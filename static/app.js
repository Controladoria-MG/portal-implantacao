// ── Estado em memória ────────────────────────────────────────
let GRUPOS_LISTA = [];      // lista enxuta da Tela 1
let grupoAtual = null;      // detalhe carregado na Tela 2
const CACHE_GRUPOS = {};    // grupoId -> detalhe já carregado (evita refetch ao reabrir o mesmo grupo)

// ── Formatação ───────────────────────────────────────────────
function formatarData(iso) {
  if (!iso) return null;
  const [ano, mes, dia] = iso.split('-');
  return `${dia}/${mes}/${ano}`;
}

function formatarMesAno(iso) {
  if (!iso) return null;
  const meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
    'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
  const [ano, mes] = iso.split('-');
  return `${meses[parseInt(mes, 10) - 1]}/${ano}`;
}

function formatarVigenciaCard(anoMes) {
  if (!anoMes) return null;
  const [ano, mes] = anoMes.split('-');
  return `01/${mes}/${ano}`;
}

function escapar(txt) {
  return String(txt ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// ══════════════════════════════════════════════════════════════
//  TELA 1 — Lista
// ══════════════════════════════════════════════════════════════
function colunaDataCard(sigla, iso, realizada) {
  const pendente = !iso;
  const feito = !!(iso && realizada);
  const valorClasse = feito ? 'card-data-col-valor card-data-col-valor--feito'
    : pendente ? 'card-data-col-valor card-data-col-valor--pendente' : 'card-data-col-valor';
  const valor = iso
    ? `<span class="${valorClasse}">${formatarData(iso)}</span>`
    : `<span class="${valorClasse}">A agendar</span>`;
  const rotuloClasse = feito ? 'card-data-col-rotulo card-data-col-rotulo--feito'
    : pendente ? 'card-data-col-rotulo card-data-col-rotulo--pendente' : 'card-data-col-rotulo';
  return `<div class="card-data-col"><span class="${rotuloClasse}">${sigla}</span>${valor}</div>`;
}

function renderLista(lista) {
  const alvo = document.getElementById('lista-grupos');
  const vazia = document.getElementById('lista-vazia');

  if (!lista.length) {
    alvo.innerHTML = '';
    vazia.classList.remove('hidden');
    return;
  }
  vazia.classList.add('hidden');

  alvo.innerHTML = lista.map(g => {
    const imp = g.implantacao || {};
    const pendente = ['dp', 'ef', 'ctb'].some(a => !imp[a]);
    const alerta = pendente
      ? `<span class="alerta-pendente" title="Há datas de implantação pendentes"></span>`
      : '';
    const corProg = corDonut(g.progresso);
    return `
      <div class="card-grupo" onclick="abrirGrupo('${g.id}')">
        <div class="card-grupo-topo">
          <span class="card-grupo-nome-wrap">
            <span class="card-grupo-nome">${escapar(g.grupo)}</span>
            ${alerta}
          </span>
          <span class="mini-prog" style="background:${corProg}">${g.progresso}%</span>
        </div>
        <div class="card-grupo-barra"><div class="card-grupo-barra-fill" style="width:${g.progresso}%; background:${corProg}"></div></div>
        <div class="card-grupo-secao-header">
          <span class="card-grupo-datas-titulo">Data de Implantação</span>
          ${g.vigencia ? `<span class="card-grupo-vigencia">Vigência <span>${formatarVigenciaCard(g.vigencia)}</span></span>` : ''}
        </div>
        <div class="card-grupo-datas">
          ${colunaDataCard('DP', imp.dp, g.implantacaoRealizada)}
          ${colunaDataCard('EF', imp.ef, g.implantacaoRealizada)}
          ${colunaDataCard('CTB', imp.ctb, g.implantacaoRealizada)}
        </div>
        <div class="dica-clique">Clique para ver mais detalhes</div>
      </div>
    `;
  }).join('');
}

function filtrarLista() {
  const termo = document.getElementById('busca').value.trim().toLowerCase();
  if (!termo) return renderLista(GRUPOS_LISTA);

  const filtrada = GRUPOS_LISTA.filter(g => {
    const nome = g.grupo.toLowerCase();
    const imp = g.implantacao || {};
    const datas = ['dp', 'ef', 'ctb']
      .map(a => formatarData(imp[a]) || 'a agendar')
      .join(' ').toLowerCase();
    return nome.includes(termo) || datas.includes(termo);
  });
  renderLista(filtrada);
}

// ══════════════════════════════════════════════════════════════
//  TELA 2 — Detalhe
// ══════════════════════════════════════════════════════════════

// ── Gráfico de rosca (percentual de conclusão) ───────────────
function corDonut(pct) {
  if (pct <= 30) return '#C00000';
  if (pct <= 70) return '#e6a700';
  return '#1e7d34';
}

function donut(pct, id) {
  return `<div class="donut" id="${id}" style="--pct:${pct}; --donut-color:${corDonut(pct)}"><span class="donut-label">${pct}%</span></div>`;
}

// ── Checkbox de etapa ─────────────────────────────────────────
function chk(grupoId, etapa, area) {
  const marcado = etapa.concluido ? 'checked' : '';
  return `<input type="checkbox" ${marcado}
            onchange="onToggleEtapa('${grupoId}', '${etapa.id}', '${area}', this.checked, this)" />`;
}

// ── Checklist de etapas de uma única área (dentro do card) ───
// Cada área tem sua própria lista de itens (grupo.etapasPorArea[area]) —
// Contábil/Fiscal/Paralegal/DP têm checklists diferentes entre si.
function secaoEtapasArea(grupo, area) {
  const itens = (grupo.etapasPorArea && grupo.etapasPorArea[area]) || [];
  if (!itens.length) {
    return '<div class="etapas-area-lista"><div class="vazio">Checklist ainda não definido.</div></div>';
  }
  const linhas = itens.map(et => `
    <div class="etapa-area-linha">
      <span class="etapa-area-nome">${escapar(et.nome)}</span>
      <span class="etapa-area-chk">${chk(grupo.id, et, area)}</span>
    </div>
  `).join('');
  return `<div class="etapas-area-lista">${linhas}</div>`;
}

// ── Botões "marcar todos" / "desmarcar todos" de uma área ───
function botoesMarcarTodos(grupoId, area) {
  return `
    <div class="etapas-area-acoes">
      <button type="button" class="btn-marcar-todos" onclick="marcarTodos('${grupoId}', '${area}', true)">Marcar todos</button>
      <button type="button" class="btn-desmarcar-todos" onclick="marcarTodos('${grupoId}', '${area}', false)">Desmarcar todos</button>
    </div>
  `;
}

// Conteúdo completo do detalhe de uma área: botões + lista de checkboxes.
// Fica junto numa função só porque marcarTodos precisa re-renderizar os
// dois de uma vez (o clique é em massa, não passa pelo onchange de cada
// checkbox individual).
function conteudoDetalheDepto(grupo, area) {
  const itens = (grupo.etapasPorArea && grupo.etapasPorArea[area]) || [];
  if (!itens.length) {
    return secaoEtapasArea(grupo, area);
  }
  return botoesMarcarTodos(grupo.id, area) + secaoEtapasArea(grupo, area);
}

// ── Título do card Fiscal, conforme o segmento das empresas do grupo ──
// Os itens do checklist continuam os mesmos (variam só por regime); isso
// é só o rótulo do card, pra organizar visualmente Indústria x Varejo.
function tituloFiscal(grupo) {
  const segmento = (grupo.empresas[0] && grupo.empresas[0].segmento) || '';
  return /varejo/i.test(segmento) ? 'Fiscal Varejo' : 'Fiscal Indústria';
}

// ── Card de implantação por departamento (Contábil/Fiscal/DP/Paralegal) ──
function cardDepto(grupo, titulo, area, dataIso, pct) {
  const feito = !!(dataIso && grupo.implantacaoRealizada);
  const valorData = dataIso
    ? `<span class="depto-data-valor${feito ? ' depto-data-valor--feito' : ''}">${formatarData(dataIso)}</span>`
    : `<span class="depto-data-valor depto-data-valor--pendente">Pendente</span>`;
  return `
    <div class="card-depto">
      <div class="card-depto-clicavel" onclick="toggleDepto('${area}')">
        <div class="card-depto-titulo">${titulo}</div>
        <div class="card-depto-corpo">
          ${donut(pct, `donut-${area}`)}
          <div class="card-depto-data">
            <span class="depto-data-rotulo">Data de implantação</span>
            ${valorData}
          </div>
        </div>
        <div class="dica-clique" id="dica-${area}">Clique para ver mais detalhes</div>
      </div>
      <div class="card-depto-detalhe hidden" id="detalhe-${area}">
        ${conteudoDetalheDepto(grupo, area)}
      </div>
    </div>
  `;
}

// ── Cards informativos ────────────────────────────────────────
function caixaContatos(grupo) {
  const itens = grupo.contatos.map(c => `
    <div class="contato-item">
      <div class="contato-nome">${escapar(c.nome)} <span class="contato-cargo">${escapar(c.cargo)}</span></div>
      <div class="contato-det">${escapar(c.email) || '<span class="vazio">sem e-mail</span>'}</div>
      <div class="contato-det">${escapar(c.telefone) || '<span class="vazio">sem telefone</span>'}</div>
    </div>
  `).join('');
  return `<div class="box"><div class="box-titulo">Contatos</div>${itens || '<div class="vazio">Sem contatos</div>'}</div>`;
}

function caixaEquipe(grupo) {
  const eq = grupo.equipe || {};
  const linha = (r, v) => `<div class="box-linha"><span class="rotulo">${r}</span><span class="valor">${escapar(v) || '—'}</span></div>`;
  return `
    <div class="box">
      <div class="box-titulo">Equipe de atendimento</div>
      ${linha('Gerente', eq.gerente)}
      ${linha('Secretaria', eq.secretaria)}
      ${linha('Master', eq.master)}
    </div>
  `;
}

function caixaContratuais(grupo) {
  const c = grupo.contratuais || {};
  const linha = (r, v) => `<div class="box-linha"><span class="rotulo">${r}</span><span class="valor">${v || '—'}</span></div>`;
  return `
    <div class="box">
      <div class="box-titulo">Informações contratuais</div>
      ${linha('Vigência', formatarMesAno(c.vigenciaContrato))}
      ${linha('Regime', escapar(c.regimeContratual))}
    </div>
  `;
}

// ── Lista de clientes do grupo ────────────────────────────────
function badgeRegime(regime) {
  if (!regime) return '<span class="vazio">—</span>';
  const classe = /SN/i.test(regime) ? 'badge-regime--sn' : 'badge-regime--outro';
  return `<span class="badge-regime ${classe}">${escapar(regime)}</span>`;
}

function secaoClientes(grupo) {
  const linhas = grupo.empresas.map(e => `
    <tr>
      <td class="td-id">${escapar(e.id)}</td>
      <td class="td-nome">${escapar(e.razaoSocial)}</td>
      <td>${badgeRegime(e.regime)}</td>
    </tr>
  `).join('');
  return `
    <div class="secao">
      <div class="secao-titulo">Clientes do grupo <span class="secao-titulo-contagem">${grupo.empresas.length}</span></div>
      <div class="clientes-tabela-wrap">
        <table class="clientes-tabela">
          <thead><tr><th>ID</th><th>Nome</th><th>Tributação</th></tr></thead>
          <tbody>${linhas || '<tr><td colspan="3" class="vazio">Nenhum cliente cadastrado.</td></tr>'}</tbody>
        </table>
      </div>
    </div>
  `;
}

// ── Observações do cliente ────────────────────────────────────
function secaoObservacoes(grupo) {
  return `
    <div class="secao">
      <div class="secao-titulo">Observações</div>
      <textarea class="observacoes-campo" id="observacoes-campo"
        placeholder="Escreva observações sobre o cliente...">${escapar(grupo.observacoes)}</textarea>
      <div class="observacoes-acoes">
        <button class="btn-salvar-obs" onclick="salvarObservacoes()">Salvar observações</button>
        <span class="observacoes-status" id="observacoes-status"></span>
      </div>
    </div>
  `;
}

// ── Montagem da Tela 2 ───────────────────────────────────────
function renderDetalhe(grupo) {
  const imp = grupo.implantacao || {};
  const prog = grupo.progresso || {};
  return `
    <section class="frame">
      <div class="frame-header">
        <span class="grupo-nome">${escapar(grupo.grupo)}</span>
        <span class="grupo-sub">${grupo.empresas.length} empresa${grupo.empresas.length > 1 ? 's' : ''}</span>
      </div>

      <div class="grid-deptos">
        ${cardDepto(grupo, 'Implantação Contábil', 'ctb', imp.ctb, prog.ctb || 0)}
        ${cardDepto(grupo, tituloFiscal(grupo), 'ef', imp.ef, prog.ef || 0)}
        ${cardDepto(grupo, 'Implantação DP', 'dp', imp.dp, prog.dp || 0)}
        ${cardDepto(grupo, 'Implantação Paralegal', 'paralegal', imp.paralegal, prog.paralegal || 0)}
        ${cardDepto(grupo, 'Gerência de Contas', 'gerencia', imp.gerencia, prog.gerencia || 0)}
      </div>

      <div class="linha-boxes linha-3">
        ${caixaContatos(grupo)}
        ${caixaEquipe(grupo)}
        ${caixaContratuais(grupo)}
      </div>

      ${secaoClientes(grupo)}
      ${secaoObservacoes(grupo)}
    </section>
  `;
}

// ── Ações ────────────────────────────────────────────────────
async function abrirGrupo(id) {
  try {
    // Reabrir um grupo já visitado nessa sessão não precisa de rede: reusa
    // o mesmo objeto (por referência), então marcações/observações feitas
    // antes continuam refletidas.
    grupoAtual = CACHE_GRUPOS[id] || await API.obterGrupo(id);
    CACHE_GRUPOS[id] = grupoAtual;
    document.getElementById('grupo-detalhe').innerHTML = renderDetalhe(grupoAtual);
    document.getElementById('tela-1').classList.add('hidden');
    document.getElementById('tela-2').classList.remove('hidden');
    window.scrollTo(0, 0);
  } catch (e) {
    alert(e.message);
  }
}

function voltarParaLista() {
  document.getElementById('tela-2').classList.add('hidden');
  document.getElementById('tela-1').classList.remove('hidden');

  // Atualização otimista: o progresso do grupo editado já foi calculado
  // localmente na Tela 2 (calcularProgressoLocal), então atualiza o card
  // na hora, sem esperar a ida e volta até o Postgres no Render.
  if (grupoAtual) {
    const card = GRUPOS_LISTA.find(g => g.id === grupoAtual.id);
    if (card && grupoAtual.progresso) card.progresso = grupoAtual.progresso.geral;
  }
  filtrarLista();

  // Reconcilia com o servidor em segundo plano, sem travar a troca de tela.
  carregarLista();
}

function toggleDepto(area) {
  const det = document.getElementById(`detalhe-${area}`);
  if (!det) return;
  const aberto = det.classList.toggle('hidden') === false; // toggle retorna o novo estado da classe 'hidden'
  const dica = document.getElementById(`dica-${area}`);
  if (dica) dica.textContent = aberto ? 'Clique para ver menos detalhes' : 'Clique para ver mais detalhes';
}

// Mesmo cálculo do backend (ver calcular_progresso em server.py), só que
// no navegador — permite atualizar a rosquinha na hora do clique, sem
// esperar a ida e volta até o Postgres no Render.
function calcularProgressoLocal(porArea) {
  const resultado = { geral: 0, dp: 0, ef: 0, ctb: 0, paralegal: 0, gerencia: 0 };
  let totalGeral = 0;
  let feitosGeral = 0;
  ['dp', 'ef', 'ctb', 'paralegal', 'gerencia'].forEach(area => {
    const itens = (porArea && porArea[area]) || [];
    const total = itens.length;
    const feitos = itens.filter(i => i.concluido).length;
    resultado[area] = total ? Math.round((feitos / total) * 100) : 0;
    totalGeral += total;
    feitosGeral += feitos;
  });
  resultado.geral = totalGeral ? Math.round((feitosGeral / totalGeral) * 100) : 0;
  return resultado;
}

async function onToggleEtapa(grupoId, etapaId, area, valor, checkboxEl) {
  // etapaId chega como string (veio de um atributo HTML) — os itens em
  // etapasPorArea têm id numérico (vem do Postgres), então o find abaixo
  // precisa comparar como número, senão nunca acha o item.
  const etapaIdNum = Number(etapaId);
  const itens = (grupoAtual.etapasPorArea && grupoAtual.etapasPorArea[area]) || [];
  const etapa = itens.find(e => e.id === etapaIdNum);
  const valorAnterior = etapa ? etapa.concluido : null;

  // Atualização otimista: muda a rosquinha na hora, antes da resposta do servidor.
  if (etapa) etapa.concluido = valor;
  atualizarProgresso(calcularProgressoLocal(grupoAtual.etapasPorArea));

  try {
    await API.marcarEtapa(grupoId, etapaIdNum, area, valor);
    // Não usa o "progresso" que volta na resposta pra atualizar a tela: se o
    // usuário clicou em mais de um item rápido, essa resposta pode ser de um
    // clique anterior e chegar depois de outra mais recente, sobrescrevendo
    // o valor já certo com um desatualizado (o "pisca" reportado). O estado
    // local já soma todos os cliques feitos até agora, então ele já é a
    // fonte da verdade — só precisamos saber aqui se deu erro ou não.
  } catch (e) {
    // desfaz o clique (estado local + o próprio checkbox) em caso de erro
    if (etapa) etapa.concluido = valorAnterior;
    if (checkboxEl) checkboxEl.checked = valorAnterior;
    atualizarProgresso(calcularProgressoLocal(grupoAtual.etapasPorArea));
    alert(e.message);
  }
}

// Marca/desmarca todos os itens de uma área de uma vez. Reaproveita
// onToggleEtapa pra cada item (mesma persistência/otimismo já testados);
// o estado local já fica certo de forma síncrona, então já dá pra
// re-renderizar a lista de checkboxes na sequência sem esperar a rede.
function marcarTodos(grupoId, area, valor) {
  const itens = (grupoAtual.etapasPorArea && grupoAtual.etapasPorArea[area]) || [];
  itens.forEach(etapa => {
    if (etapa.concluido !== valor) {
      onToggleEtapa(grupoId, String(etapa.id), area, valor, null);
    }
  });
  const det = document.getElementById(`detalhe-${area}`);
  if (det) det.innerHTML = conteudoDetalheDepto(grupoAtual, area);
}

function atualizarProgresso(prog) {
  grupoAtual.progresso = prog;
  ['dp', 'ef', 'ctb', 'paralegal', 'gerencia'].forEach(area => {
    const el = document.getElementById(`donut-${area}`);
    if (!el) return;
    el.style.setProperty('--pct', prog[area]);
    el.style.setProperty('--donut-color', corDonut(prog[area]));
    const label = el.querySelector('.donut-label');
    if (label) label.textContent = `${prog[area]}%`;
  });
}

async function carregarDetalheAtual() {
  if (grupoAtual) await abrirGrupo(grupoAtual.id);
}

async function salvarObservacoes() {
  const campo = document.getElementById('observacoes-campo');
  const status = document.getElementById('observacoes-status');
  const texto = campo.value;
  try {
    await API.salvarObservacoes(grupoAtual.id, texto);
    grupoAtual.observacoes = texto;
    status.textContent = 'Salvo.';
    setTimeout(() => { status.textContent = ''; }, 2000);
  } catch (e) {
    status.textContent = 'Erro ao salvar.';
  }
}

// ── Tema ─────────────────────────────────────────────────────
function alternarTema() {
  const escuro = document.body.classList.toggle('tema-escuro');
  document.querySelector('.btn-tema').textContent = escuro ? 'Tema claro' : 'Tema escuro';
}

// ── Init ─────────────────────────────────────────────────────
async function carregarLista() {
  try {
    GRUPOS_LISTA = await API.listarGrupos();
    filtrarLista();
  } catch (e) {
    document.getElementById('lista-grupos').innerHTML =
      `<div class="lista-vazia">Erro ao carregar: ${e.message}.<br>O backend está rodando?</div>`;
  }
}

carregarLista();
