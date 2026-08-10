# CLAUDE.md — Documentação de Estrutura Base do Projeto

Este arquivo descreve as convenções e regras de organização que devem ser seguidas em todos os projetos.

---

## Estrutura de Diretórios

```
Raiz/
├── index.html
├── .gitignore
├── CLAUDE.md
├── static/
│   ├── arquivo.js
│   └── arquivo.css
├── data/
│   └── <subpasta>/
└── backend/
```

---

## Regras por Tipo de Arquivo

### HTML — `index.html`
- O arquivo `.html` principal deve **sempre** ficar na pasta raiz.
- O nome do arquivo deve ser **obrigatoriamente** `index.html`.

### JavaScript e CSS — `static/`
- Todo arquivo `.js` e `.css` deve ficar dentro da pasta `static/`.
- **Nunca** embutir JavaScript ou CSS diretamente no HTML — mantenha os arquivos sempre separados.
```
static/
├── app.js
└── styles.css
```

### Banco de Dados / Arquivos de Dados — `data/`
- Todos os arquivos usados como base de dados devem ficar dentro da pasta `data/`.
- **Nunca** salve arquivos diretamente na raiz de `data/` — utilize sempre subpastas.
```
data/
├── usuarios/
├── produtos/
└── logs/
```

### Backend — `backend/`
- Arquivos de servidor e lógica de backend (Python, Node.js, etc.) devem ficar dentro da pasta `backend/`.
```
backend/
├── server.py
└── routes.js
```

### Arquivos Ignorados — `.gitignore`
- Arquivos que **não fazem parte da interface** (variáveis de ambiente, dependências, configurações locais) devem ser excluídos do repositório via `.gitignore`.
- Exemplos comuns:
```
# .gitignore
.env
__pycache__/
node_modules/
*.log
*.sqlite
.DS_Store
```
#### O projeto será postado no GitHub, então siga a estrutura pensando nisso.

#### Atualizado em 2026-08-10: diferente da regra genérica acima, ESTE projeto usa backend sim (`backend/server.py`, Flask). A identidade dos grupos vem da planilha `data/base/base implantação.xlsx` (só leitura, nunca escrita pelo portal) e os checklists/observações ficam no Postgres (leitura e escrita). O front consome tudo via API (`/api/grupos`, `/api/grupos/<id>`), não tem dado setado direto no `.js`.
---

## Resumo das Regras

##Você já tem todas as permissões do GIT, (pull, push, add, commit)

**Sempre** fale em português

| Tipo de arquivo         | Onde colocar              | Observação                              |
|-------------------------|---------------------------|-----------------------------------------|
| HTML principal          | `index.html` (raiz)       | Sempre nomeado `index.html`             |
| JavaScript              | `static/`                 | Separado do HTML                        |
| CSS                     | `static/`                 | Separado do HTML                        |
| Dados / Banco de dados  | `data/<subpasta>/`        | Nunca diretamente em `data/`            |
| Backend (Python, Node…) | `backend/`                | Toda lógica de servidor aqui            |
| Configs locais / .env   | Fora do repositório       | Listado no `.gitignore`                 |

## Edição de arquivos
    Você tem todas as permissões para ir editando os arquivos sem que eu tenha que ficar sempre confirmando.