"""
Portal de Implantação — backend leve.

- Serve o site estático (index.html, static/, data/imagens).
- Expõe a API que lê/grava o estado em data/db.json.

Persistência TEMPORÁRIA em JSON (fase de teste). Ao migrar para o Render,
basta trocar a implementação de carregar_db()/salvar_db() por um banco real
(ex: Postgres) — o restante (rotas e front-end) não muda.

Rodar localmente:
    pip install flask
    python backend/server.py
    abrir http://localhost:5000
"""

import json
import threading
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

# ── Caminhos ─────────────────────────────────────────────────
RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO_DB = RAIZ / "data" / "db.json"

# Lock para evitar corrida na leitura/gravação do JSON
_lock = threading.Lock()

app = Flask(__name__, static_folder=None)


# ── Acesso ao "banco" (JSON) ─────────────────────────────────
def carregar_db():
    with _lock:
        with open(ARQUIVO_DB, "r", encoding="utf-8") as f:
            return json.load(f)


def salvar_db(dados):
    with _lock:
        with open(ARQUIVO_DB, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)


def encontrar_grupo(dados, grupo_id):
    return next((g for g in dados["grupos"] if g["id"] == grupo_id), None)


def calcular_progresso(grupo):
    """Retorna % de conclusão geral e por área, com base nos checkboxes."""
    areas = ("dp", "ef", "ctb", "paralegal")
    etapas = grupo.get("etapas", [])
    total_por_area = len(etapas)

    resultado = {"geral": 0, "dp": 0, "ef": 0, "ctb": 0, "paralegal": 0}
    if total_por_area == 0:
        return resultado

    for area in areas:
        feitos = sum(1 for e in etapas if e.get(area))
        resultado[area] = round(feitos / total_por_area * 100)

    total_geral = total_por_area * len(areas)
    feitos_geral = sum(1 for e in etapas for a in areas if e.get(a))
    resultado["geral"] = round(feitos_geral / total_geral * 100)
    return resultado


# ── API ──────────────────────────────────────────────────────
@app.get("/api/grupos")
def listar_grupos():
    """Lista enxuta para a Tela 1 (nome, datas por área e progresso)."""
    dados = carregar_db()
    lista = [
        {
            "id": g["id"],
            "grupo": g["grupo"],
            "implantacao": g.get("implantacao", {}),
            "vigencia": g.get("contratuais", {}).get("vigenciaContrato"),
            "progresso": calcular_progresso(g)["geral"],
        }
        for g in dados["grupos"]
    ]
    lista.sort(key=lambda x: (x["vigencia"] or "9999-99", x["grupo"].lower()))
    return jsonify(lista)


@app.get("/api/grupos/<grupo_id>")
def obter_grupo(grupo_id):
    """Detalhe completo para a Tela 2, já com o progresso calculado."""
    dados = carregar_db()
    grupo = encontrar_grupo(dados, grupo_id)
    if not grupo:
        return jsonify({"erro": "Grupo não encontrado"}), 404
    resposta = dict(grupo)
    resposta["progresso"] = calcular_progresso(grupo)
    return jsonify(resposta)


@app.post("/api/grupos/<grupo_id>/etapas")
def marcar_etapa(grupo_id):
    """
    Marca/desmarca um checkbox de etapa.
    Body JSON: { "etapaId": "et1", "area": "dp", "valor": true }
    """
    body = request.get_json(silent=True) or {}
    etapa_id = body.get("etapaId")
    area = body.get("area")
    valor = bool(body.get("valor"))

    if area not in ("dp", "ef", "ctb", "paralegal"):
        return jsonify({"erro": "Área inválida (use dp, ef, ctb ou paralegal)"}), 400

    dados = carregar_db()
    grupo = encontrar_grupo(dados, grupo_id)
    if not grupo:
        return jsonify({"erro": "Grupo não encontrado"}), 404

    etapa = next((e for e in grupo.get("etapas", []) if e["id"] == etapa_id), None)
    if not etapa:
        return jsonify({"erro": "Etapa não encontrada"}), 404

    etapa[area] = valor
    salvar_db(dados)

    return jsonify({"ok": True, "progresso": calcular_progresso(grupo)})


@app.post("/api/grupos/<grupo_id>/observacoes")
def salvar_observacoes(grupo_id):
    """Salva o texto de observações do grupo. Body JSON: { "texto": "..." }"""
    body = request.get_json(silent=True) or {}
    texto = str(body.get("texto", ""))

    dados = carregar_db()
    grupo = encontrar_grupo(dados, grupo_id)
    if not grupo:
        return jsonify({"erro": "Grupo não encontrado"}), 404

    grupo["observacoes"] = texto
    salvar_db(dados)

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
    app.run(host="0.0.0.0", port=5000, debug=True)
