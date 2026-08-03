"""
Portal de Implantação — backend.

- Serve o site estático (index.html, static/, data/imagens).
- Identidade dos grupos (nome, contatos, equipe, dados contratuais,
  empresas, datas de implantação) vem de data/db.json — hoje é a base de
  teste; depois vira uma planilha Excel, sempre só leitura pelo portal.
- Checklists (catálogo de itens + marcações) e observações — tudo que o
  portal de fato escreve — ficam no Postgres (variável DATABASE_URL).
  Schema em backend/schema_postgres.sql.

Rodar localmente:
    pip install -r backend/requirements.txt
    export DATABASE_URL=postgresql://usuario:senha@host/banco
    python backend/server.py
    abrir http://localhost:5000
"""

import json
import os
from contextlib import contextmanager
from pathlib import Path

import psycopg2
import psycopg2.pool
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request, send_from_directory

# ── Caminhos e config ────────────────────────────────────────
RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO_DB = RAIZ / "data" / "db.json"

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

AREAS = ("dp", "ef", "ctb", "paralegal", "gerencia")

app = Flask(__name__, static_folder=None)

# Pool de conexões: abrir uma conexão nova (handshake TLS com o Postgres do
# Render) a cada requisição era o principal motivo dos cards demorando pra
# abrir. Com o pool, a conexão é reaproveitada entre requisições.
_pool = None


def _obter_pool():
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            1, 10, DATABASE_URL, cursor_factory=RealDictCursor
        )
    return _pool


@contextmanager
def get_conn():
    conn = _obter_pool().getconn()
    # autocommit evita que a conexão volte "suja" (transação aberta) pro
    # pool — sem isso, o putconn() faz um reset() com ida e volta extra ao
    # Postgres a cada requisição, quase dobrando o tempo de resposta.
    conn.autocommit = True
    try:
        yield conn
    finally:
        _obter_pool().putconn(conn)


# ── Identidade dos grupos (JSON hoje, planilha Excel depois) ──
def carregar_identidade():
    with open(ARQUIVO_DB, "r", encoding="utf-8") as f:
        return json.load(f)


def encontrar_identidade(dados, grupo_id):
    return next((g for g in dados["grupos"] if g["id"] == grupo_id), None)


# ── Checklist (Postgres) ──────────────────────────────────────
def carregar_checklist(grupo_id):
    """Retorna {etapasPorArea, regimeEf, observacoes} para um grupo, ou
    None se o grupo ainda não existir em grupos_implantacao."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT regime_ef, observacoes FROM grupos_implantacao WHERE grupo_id = %s",
                (grupo_id,),
            )
            grupo_pg = cur.fetchone()
            if not grupo_pg:
                return None

            cur.execute("""
                SELECT i.id, i.departamento, i.texto, i.ordem, m.concluido
                FROM checklist_itens i
                JOIN checklist_marcacoes m ON m.checklist_item_id = i.id
                WHERE m.grupo_id = %s AND i.ativo
                ORDER BY i.departamento, i.ordem
            """, (grupo_id,))
            linhas = cur.fetchall()

    por_area = {a: [] for a in AREAS}
    for r in linhas:
        por_area[r["departamento"]].append({
            "id": r["id"],
            "nome": r["texto"],
            "concluido": r["concluido"],
        })

    return {
        "etapasPorArea": por_area,
        "regimeEf": grupo_pg["regime_ef"],
        "observacoes": grupo_pg["observacoes"],
    }


def carregar_progresso_geral_todos():
    """Progresso 'geral' de todos os grupos numa única query — evita abrir
    uma conexão nova por grupo (a Tela 1 lista todos de uma vez)."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT m.grupo_id,
                       count(*) AS total,
                       count(*) FILTER (WHERE m.concluido) AS feitos
                FROM checklist_marcacoes m
                JOIN checklist_itens i ON i.id = m.checklist_item_id AND i.ativo
                GROUP BY m.grupo_id
            """)
            linhas = cur.fetchall()
    return {
        r["grupo_id"]: round(r["feitos"] / r["total"] * 100) if r["total"] else 0
        for r in linhas
    }


def calcular_progresso(por_area):
    """% de conclusão geral e por área, a partir de etapasPorArea."""
    resultado = {"geral": 0, "dp": 0, "ef": 0, "ctb": 0, "paralegal": 0, "gerencia": 0}

    total_geral = 0
    feitos_geral = 0
    for area in AREAS:
        itens = por_area.get(area, [])
        total = len(itens)
        feitos = sum(1 for i in itens if i["concluido"])
        resultado[area] = round(feitos / total * 100) if total else 0
        total_geral += total
        feitos_geral += feitos

    resultado["geral"] = round(feitos_geral / total_geral * 100) if total_geral else 0
    return resultado


# ── API ──────────────────────────────────────────────────────
@app.get("/api/grupos")
def listar_grupos():
    """Lista enxuta para a Tela 1 (nome, datas por área e progresso)."""
    dados = carregar_identidade()
    progresso_por_grupo = carregar_progresso_geral_todos()
    lista = [
        {
            "id": g["id"],
            "grupo": g["grupo"],
            "implantacao": g.get("implantacao", {}),
            "vigencia": g.get("contratuais", {}).get("vigenciaContrato"),
            "progresso": progresso_por_grupo.get(g["id"], 0),
        }
        for g in dados["grupos"]
    ]
    lista.sort(key=lambda x: (x["vigencia"] or "9999-99", x["grupo"].lower()))
    return jsonify(lista)


@app.get("/api/grupos/<grupo_id>")
def obter_grupo(grupo_id):
    """Detalhe completo para a Tela 2: identidade (JSON) + checklist (Postgres)."""
    dados = carregar_identidade()
    grupo = encontrar_identidade(dados, grupo_id)
    if not grupo:
        return jsonify({"erro": "Grupo não encontrado"}), 404

    checklist = carregar_checklist(grupo_id)
    if not checklist:
        return jsonify({"erro": "Grupo sem checklist cadastrado no Postgres"}), 404

    resposta = dict(grupo)
    resposta["etapasPorArea"] = checklist["etapasPorArea"]
    resposta["regimeEf"] = checklist["regimeEf"]
    resposta["observacoes"] = checklist["observacoes"]
    resposta["progresso"] = calcular_progresso(checklist["etapasPorArea"])
    return jsonify(resposta)


@app.post("/api/grupos/<grupo_id>/etapas")
def marcar_etapa(grupo_id):
    """
    Marca/desmarca um item do checklist.
    Body JSON: { "etapaId": 5, "area": "ctb", "valor": true }
    """
    body = request.get_json(silent=True) or {}
    area = body.get("area")
    valor = bool(body.get("valor"))

    if area not in AREAS:
        return jsonify({"erro": "Área inválida (use dp, ef, ctb, paralegal ou gerencia)"}), 400

    try:
        etapa_id = int(body.get("etapaId"))
    except (TypeError, ValueError):
        return jsonify({"erro": "etapaId inválido"}), 400

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE checklist_marcacoes SET concluido = %s
                WHERE grupo_id = %s AND checklist_item_id = %s
                RETURNING id
            """, (valor, grupo_id, etapa_id))
            atualizado = cur.fetchone()
            conn.commit()

    if not atualizado:
        return jsonify({"erro": "Etapa não encontrada para esse grupo"}), 404

    checklist = carregar_checklist(grupo_id)
    return jsonify({"ok": True, "progresso": calcular_progresso(checklist["etapasPorArea"])})


@app.post("/api/grupos/<grupo_id>/observacoes")
def salvar_observacoes(grupo_id):
    """Salva o texto de observações do grupo. Body JSON: { "texto": "..." }"""
    body = request.get_json(silent=True) or {}
    texto = str(body.get("texto", ""))

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE grupos_implantacao SET observacoes = %s, atualizado_em = now()
                WHERE grupo_id = %s
                RETURNING grupo_id
            """, (texto, grupo_id))
            atualizado = cur.fetchone()
            conn.commit()

    if not atualizado:
        return jsonify({"erro": "Grupo não encontrado"}), 404
    return jsonify({"ok": True})


# ── Servir o site estático ───────────────────────────────────
@app.get("/")
def index():
    return send_from_directory(RAIZ, "index.html")


@app.get("/<path:caminho>")
def estaticos(caminho):
    # Serve static/, data/imagens, etc. Bloqueia acesso ao db.json.
    if caminho.replace("\\", "/").endswith("data/db.json"):
        return jsonify({"erro": "Acesso negado"}), 403
    return send_from_directory(RAIZ, caminho)


if __name__ == "__main__":
    # use_reloader=False: o reloader do Flask atrapalha o pool de conexões
    # (cada request ficava lento como se abrisse conexão nova de novo).
    # Em produção (gunicorn) isso nem entra em jogo.
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
