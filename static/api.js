/**
 * Camada única de acesso à API.
 *
 * Hoje o site é servido pelo próprio backend Flask (mesma origem),
 * então API_BASE fica vazio. Quando migrar para o Render, basta
 * apontar API_BASE para a URL pública do backend, ex:
 *   const API_BASE = 'https://portal-implantacao.onrender.com';
 * Nada mais no front precisa mudar.
 */
const API_BASE = '';

const API = {
  async planilhaAtualizadaEm() {
    const r = await fetch(`${API_BASE}/api/planilha-atualizada-em`);
    if (!r.ok) throw new Error('Falha ao consultar atualização da base');
    return r.json();
  },

  async listarGrupos() {
    const r = await fetch(`${API_BASE}/api/grupos`);
    if (!r.ok) throw new Error('Falha ao carregar grupos');
    return r.json();
  },

  async obterGrupo(id) {
    const r = await fetch(`${API_BASE}/api/grupos/${id}`);
    if (!r.ok) throw new Error('Falha ao carregar o grupo');
    return r.json();
  },

  async marcarEtapa(grupoId, etapaId, area, valor) {
    const r = await fetch(`${API_BASE}/api/grupos/${grupoId}/etapas`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ etapaId, area, valor }),
    });
    if (!r.ok) throw new Error('Falha ao salvar a etapa');
    return r.json();
  },

  async salvarObservacoes(grupoId, texto) {
    const r = await fetch(`${API_BASE}/api/grupos/${grupoId}/observacoes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ texto }),
    });
    if (!r.ok) throw new Error('Falha ao salvar as observações');
    return r.json();
  },
};
