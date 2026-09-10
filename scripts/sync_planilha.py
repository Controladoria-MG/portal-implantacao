"""
Sincroniza a planilha de identidade dos grupos do OneDrive pro repositório.

O usuário edita a planilha direto no OneDrive (Base_Implantação/base
implantação.xlsx); este script copia a versão atual pra
data/base/base implantação.xlsx e dá commit + push sozinho.
Sempre atualiza data/base/atualizado_em.txt com a hora da execução,
mesmo quando a planilha não mudou -- é essa hora que o front mostra
como "Base atualizada em ...", e ela precisa refletir quando o sync
rodou de fato, não só a última vez que algum dado mudou.
Feito pra rodar sem supervisão (Agendador de Tarefas do Windows) -- por
isso registra tudo em scripts/sync_planilha.log em vez de só print().

Rodar manualmente:
    python scripts/sync_planilha.py

Também é chamado pelo hub "Atualização de bases" (backend/relatorios/
sync_planilha_implantacao.py de lá importa executar() deste arquivo por
caminho) -- por isso a lógica de verdade fica em executar(log=None), que
aceita um callback de log opcional (mesma convenção dos outros robôs do
hub) e levanta exceção normal em erro em vez de sys.exit, pra não ser
confundido com cancelamento pela fila do hub. main() é só o wrapper de
linha de comando (sys.exit(1) em erro), usado pelo Agendador de Tarefas.
"""

import filecmp
import logging
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import openpyxl

ORIGEM = Path(r"C:\Users\warruda\OneDrive - Mgcontecnica\Base_Implantação\base implantação.xlsx")

RAIZ_REPO = Path(__file__).resolve().parent.parent
DESTINO = RAIZ_REPO / "data" / "base" / "base implantação.xlsx"
# Sidecar com a hora da última sincronização -- o backend expõe isso na API
# pro front mostrar "Base atualizada em ..." na barra superior. Guardado à
# parte (em vez de usar a data de modificação do arquivo) porque no deploy
# do Render o checkout do git muda a mtime do .xlsx pra hora do deploy, não
# pra hora real da última edição.
ARQUIVO_TIMESTAMP = DESTINO.parent / "atualizado_em.txt"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(Path(__file__).resolve().parent / "sync_planilha.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("sync_planilha")


class _CallbackHandler(logging.Handler):
    """Espelha cada log emitido pro callback do chamador (ex.: o hub
    'Atualização de bases', que mostra essas mensagens no painel do card
    em vez de só no arquivo .log/stdout)."""

    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.setFormatter(logging.Formatter("%(message)s"))

    def emit(self, record):
        self.callback(self.format(record))


def _ler_linhas(caminho):
    """Lê a aba 'Clientes' e devolve {ID: {coluna: valor}} -- ID é a
    chave de cada linha (empresa) na planilha, então serve pra comparar
    duas versões e achar o que mudou linha a linha."""
    wb = openpyxl.load_workbook(caminho, data_only=True)
    ws = wb["Clientes"]
    cabecalho = [c.value for c in ws[1]]
    linhas = {}
    for linha in ws.iter_rows(min_row=2, values_only=True):
        d = dict(zip(cabecalho, linha))
        id_empresa = d.get("ID")
        if id_empresa is None:
            continue
        linhas[id_empresa] = d
    return linhas


def _norm(valor):
    """None e string vazia contam como 'sem valor' -- evita ruído no diff
    (célula vazia vs. célula nunca preenchida não é uma mudança real)."""
    if valor is None:
        return ""
    return str(valor).strip()


def _nome_linha(d):
    return d.get("RazaoSocial") or d.get("Grupo") or "?"


def _log_diferencas(antigas, novas):
    """Compara as linhas antigas x novas por ID e loga o que mudou:
    empresas novas, removidas e, pras que continuam, quais campos
    mudaram de valor."""
    ids_antigos = set(antigas)
    ids_novos = set(novas)

    adicionadas = ids_novos - ids_antigos
    removidas = ids_antigos - ids_novos
    em_comum = ids_antigos & ids_novos

    alteracoes = {}
    for id_empresa in em_comum:
        antiga, nova = antigas[id_empresa], novas[id_empresa]
        campos = set(antiga) | set(nova)
        mudou = [
            (campo, antiga.get(campo), nova.get(campo))
            for campo in campos
            if campo != "ID" and _norm(antiga.get(campo)) != _norm(nova.get(campo))
        ]
        if mudou:
            alteracoes[id_empresa] = mudou

    if not (adicionadas or removidas or alteracoes):
        logger.info("Planilha mudou (ex: formatação), mas nenhuma linha de dado foi alterada.")
        return

    logger.info(
        "Alterações: %d empresa(s) nova(s), %d removida(s), %d alterada(s).",
        len(adicionadas), len(removidas), len(alteracoes),
    )
    for id_empresa in sorted(adicionadas, key=str):
        logger.info("  + %s (ID %s)", _nome_linha(novas[id_empresa]), id_empresa)
    for id_empresa in sorted(removidas, key=str):
        logger.info("  - %s (ID %s)", _nome_linha(antigas[id_empresa]), id_empresa)
    for id_empresa in sorted(alteracoes, key=str):
        nome = _nome_linha(novas[id_empresa])
        detalhes = "; ".join(
            f"{campo}: {_norm(antigo) or '(vazio)'} -> {_norm(novo) or '(vazio)'}"
            for campo, antigo, novo in alteracoes[id_empresa]
        )
        logger.info("  * %s (ID %s): %s", nome, id_empresa, detalhes)


def _git(*args):
    """Roda um comando git na raiz do repo e devolve (codigo, stdout+stderr)."""
    resultado = subprocess.run(
        ["git", *args],
        cwd=RAIZ_REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    saida = (resultado.stdout + resultado.stderr).strip()
    return resultado.returncode, saida


def executar(log=None) -> dict:
    """Lógica de verdade do sync -- chamada tanto pelo main() (CLI/Agendador
    de Tarefas) quanto pelo wrapper do hub "Atualização de bases"
    (backend/relatorios/sync_planilha_implantacao.py, que importa esta
    função por caminho). `log`, se passado, recebe cada linha de log
    também (além do arquivo/stdout de sempre) -- é o que o hub usa pra
    mostrar o progresso no painel do card. Levanta RuntimeError em erro,
    em vez de sys.exit, pra não ser confundido com um cancelamento pela
    fila do hub (que trata SystemExit como "cancelado pelo usuário")."""
    handler = _CallbackHandler(log) if log else None
    if handler:
        logger.addHandler(handler)
    try:
        if not ORIGEM.exists():
            msg = f"Planilha de origem não encontrada: {ORIGEM} (OneDrive sincronizado?)"
            logger.error(msg)
            raise RuntimeError(msg)

        # Traz o repo em dia antes de mexer -- evita push rejeitado por
        # histórico divergente se alguém commitou outra coisa nesse meio tempo.
        codigo, saida = _git("pull", "--ff-only")
        if codigo != 0:
            msg = f"git pull falhou, abortando sync:\n{saida}"
            logger.error(msg)
            raise RuntimeError(msg)

        houve_mudanca = not (DESTINO.exists() and filecmp.cmp(ORIGEM, DESTINO, shallow=False))

        if not houve_mudanca:
            logger.info("Planilha já está igual, nada pra sincronizar.")
        else:
            if DESTINO.exists():
                try:
                    _log_diferencas(_ler_linhas(DESTINO), _ler_linhas(ORIGEM))
                except Exception:
                    logger.exception("Não deu pra calcular o diff da planilha (sync segue normalmente).")
            else:
                logger.info("Primeira sincronização, sem versão anterior pra comparar.")

            DESTINO.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ORIGEM, DESTINO)
            logger.info("Planilha copiada do OneDrive pro repo.")

        # Sempre atualiza o timestamp, mesmo sem mudança de dado -- senão a
        # barra do portal mostra uma data velha mesmo quando o sync rodou e
        # confirmou que a base já estava em dia (o que confundia quem via a
        # data parada e achava que o robô não tinha rodado).
        timestamp = datetime.now().astimezone().isoformat()
        ARQUIVO_TIMESTAMP.write_text(timestamp, encoding="utf-8")

        _git("add", str(DESTINO.relative_to(RAIZ_REPO)), str(ARQUIVO_TIMESTAMP.relative_to(RAIZ_REPO)))

        # git diff --cached --quiet devolve 0 se não há nada staged (pode
        # acontecer se o conteúdo binário mudou mas o git já tinha essa versão).
        codigo, _ = _git("diff", "--cached", "--quiet")
        if codigo == 0:
            logger.info("Cópia igual à já commitada, nada pra commitar.")
            return {"houve_mudanca": houve_mudanca, "atualizado_em": timestamp, "publicado": False}

        mensagem = (
            "Atualiza planilha de implantação (sync automático)"
            if houve_mudanca
            else "Atualiza data do último sync (planilha sem mudanças)"
        )
        codigo, saida = _git("commit", "-m", mensagem)
        if codigo != 0:
            msg = f"git commit falhou:\n{saida}"
            logger.error(msg)
            raise RuntimeError(msg)

        codigo, saida = _git("push")
        if codigo != 0:
            msg = f"git push falhou (commit ficou salvo localmente, tenta rodar de novo):\n{saida}"
            logger.error(msg)
            raise RuntimeError(msg)

        logger.info("Push feito com sucesso.")
        return {"houve_mudanca": houve_mudanca, "atualizado_em": timestamp, "publicado": True}
    finally:
        if handler:
            logger.removeHandler(handler)


def main():
    try:
        executar()
    except RuntimeError:
        sys.exit(1)


if __name__ == "__main__":
    main()
