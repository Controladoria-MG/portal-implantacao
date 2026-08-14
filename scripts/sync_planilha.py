"""
Sincroniza a planilha de identidade dos grupos do OneDrive pro repositório.

O usuário edita a planilha direto no OneDrive (Base_Implantação/base
implantação.xlsx); este script copia a versão atual pra
data/base/base implantação.xlsx e dá commit + push sozinho, se algo mudou.
Feito pra rodar sem supervisão (Agendador de Tarefas do Windows) -- por
isso registra tudo em scripts/sync_planilha.log em vez de só print().

Rodar manualmente:
    python scripts/sync_planilha.py
"""

import filecmp
import logging
import shutil
import subprocess
import sys
from pathlib import Path

ORIGEM = Path(r"C:\Users\warruda\OneDrive - Mgcontecnica\Base_Implantação\base implantação.xlsx")

RAIZ_REPO = Path(__file__).resolve().parent.parent
DESTINO = RAIZ_REPO / "data" / "base" / "base implantação.xlsx"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(Path(__file__).resolve().parent / "sync_planilha.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("sync_planilha")


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


def main():
    if not ORIGEM.exists():
        log.error("Planilha de origem não encontrada: %s (OneDrive sincronizado?)", ORIGEM)
        sys.exit(1)

    # Traz o repo em dia antes de mexer -- evita push rejeitado por
    # histórico divergente se alguém commitou outra coisa nesse meio tempo.
    codigo, saida = _git("pull", "--ff-only")
    if codigo != 0:
        log.error("git pull falhou, abortando sync:\n%s", saida)
        sys.exit(1)

    if DESTINO.exists() and filecmp.cmp(ORIGEM, DESTINO, shallow=False):
        log.info("Planilha já está igual, nada pra sincronizar.")
        return

    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ORIGEM, DESTINO)
    log.info("Planilha copiada do OneDrive pro repo.")

    _git("add", str(DESTINO.relative_to(RAIZ_REPO)))

    # git diff --cached --quiet devolve 0 se não há nada staged (pode
    # acontecer se o conteúdo binário mudou mas o git já tinha essa versão).
    codigo, _ = _git("diff", "--cached", "--quiet")
    if codigo == 0:
        log.info("Cópia igual à já commitada, nada pra commitar.")
        return

    codigo, saida = _git("commit", "-m", "Atualiza planilha de implantação (sync automático)")
    if codigo != 0:
        log.error("git commit falhou:\n%s", saida)
        sys.exit(1)

    codigo, saida = _git("push")
    if codigo != 0:
        log.error("git push falhou (commit ficou salvo localmente, tenta rodar de novo):\n%s", saida)
        sys.exit(1)

    log.info("Push feito com sucesso.")


if __name__ == "__main__":
    main()
