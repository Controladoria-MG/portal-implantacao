-- ============================================================
-- Portal de Implantação — schema Postgres
-- ============================================================
-- A identidade do grupo (nome, empresas, contatos, equipe, dados
-- contratuais — a "Tela 1") vem de uma planilha Excel, só leitura.
-- O Postgres guarda apenas o que o portal de fato escreve: o
-- estado dos checklists de implantação por departamento e as
-- observações. `grupo_id` é a chave que liga as duas bases —
-- precisa bater com o identificador usado na planilha (ex: a
-- coluna "id"/código do grupo).
--
-- Departamentos usam os mesmos códigos já usados no app:
--   ctb        = Contábil
--   ef         = Escrita Fiscal
--   dp         = Departamento Pessoal
--   paralegal  = Paralegal
--   gerencia   = Gerência de Contas
-- ============================================================

-- ── Catálogo dos itens de checklist (fixo, por departamento) ──
-- Um item pode ser específico de um regime (hoje só a Escrita Fiscal
-- varia): 'lucro_real_presumido' e 'simples_nacional' são as duas
-- variantes de Fiscal Varejo (conforme o regime tributário do
-- cliente); 'industria' é o checklist único de Fiscal Indústria
-- (não se subdivide por regime tributário).
-- `regime = NULL` = item vale pra qualquer regime (caso de todos os
-- itens do Contábil, e futuramente de DP/Paralegal).
CREATE TABLE IF NOT EXISTS checklist_itens (
    id            SERIAL PRIMARY KEY,
    departamento  TEXT NOT NULL CHECK (departamento IN ('ctb', 'ef', 'dp', 'paralegal', 'gerencia')),
    regime        TEXT CHECK (regime IN ('lucro_real_presumido', 'simples_nacional', 'industria')),
    texto         TEXT NOT NULL,
    ordem         INTEGER NOT NULL,
    ativo         BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_checklist_itens_depto ON checklist_itens (departamento, regime, ordem);

-- ── Estado de implantação por grupo ────────────────────────────
-- `regime_ef` decide qual variante do checklist de Escrita Fiscal
-- esse grupo usa: 'lucro_real_presumido'/'simples_nacional' para
-- grupos Fiscal Varejo (conforme regime tributário), ou 'industria'
-- para grupos Fiscal Indústria (segmento da empresa = Indústria,
-- checklist único, não depende do regime tributário). Se o grupo
-- tiver mais de uma empresa com regimes diferentes, hoje tratamos
-- um regime só por grupo — revisar se isso mudar.
CREATE TABLE IF NOT EXISTS grupos_implantacao (
    grupo_id      TEXT PRIMARY KEY,   -- mesma chave usada na planilha Excel
    regime_ef     TEXT CHECK (regime_ef IN ('lucro_real_presumido', 'simples_nacional', 'industria')),
    observacoes   TEXT NOT NULL DEFAULT '',
    criado_em     TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── Marcação de cada item, por grupo ────────────────────────────
CREATE TABLE IF NOT EXISTS checklist_marcacoes (
    id                 SERIAL PRIMARY KEY,
    grupo_id           TEXT NOT NULL REFERENCES grupos_implantacao(grupo_id) ON DELETE CASCADE,
    checklist_item_id  INTEGER NOT NULL REFERENCES checklist_itens(id) ON DELETE CASCADE,
    concluido          BOOLEAN NOT NULL DEFAULT FALSE,
    concluido_em       TIMESTAMPTZ,
    concluido_por      TEXT,
    UNIQUE (grupo_id, checklist_item_id)
);

CREATE INDEX IF NOT EXISTS idx_checklist_marcacoes_grupo ON checklist_marcacoes (grupo_id);

-- ============================================================
-- Seed: catálogo de itens — todos os 4 departamentos já são os
-- itens reais (Contábil, Escrita Fiscal, Paralegal e DP).
-- ============================================================

-- Contábil (regime NULL = aplica a qualquer cliente)
INSERT INTO checklist_itens (departamento, regime, texto, ordem) VALUES
('ctb', NULL, 'Reunião de implantação', 1),
('ctb', NULL, 'Alinhar data de envio dos extratos e relatórios', 2),
('ctb', NULL, 'Senha e acesso do FTP do cliente', 3),
('ctb', NULL, 'Senha e acesso no SCI Web', 4),
('ctb', NULL, 'Balanço de implantação', 5),
('ctb', NULL, 'Implantar saldos no sistema Único', 6),
('ctb', NULL, 'Certificado', 7),
('ctb', NULL, 'Aplicar o modelo de tributação no MG Controle', 8),
('ctb', NULL, 'Cadastrar o email no Check List', 9),
('ctb', NULL, 'Revisar o plano de contas', 10),
('ctb', NULL, 'Atribuir o responsável direto do cliente', 11);

-- Escrita Fiscal — Lucro Real ou Presumido
INSERT INTO checklist_itens (departamento, regime, texto, ordem) VALUES
('ef', 'lucro_real_presumido', 'Confirmar se o certificado já está na árvore da coordenação', 1),
('ef', 'lucro_real_presumido', 'Confirmar se o certificado já está cadastrado no GAX para efetuar a captura das compras', 2),
('ef', 'lucro_real_presumido', 'Verificar se o cliente colocou a TAG nas notas emitidas', 3),
('ef', 'lucro_real_presumido', 'Consulta Conta Fiscal', 4),
('ef', 'lucro_real_presumido', 'Consulta SPED FISCAL ENTREGUE', 5),
('ef', 'lucro_real_presumido', 'Consulta SPED CONTRIBUIÇÕES ENTREGUE', 6),
('ef', 'lucro_real_presumido', 'Parametrização de empresa no SCI', 7),
('ef', 'lucro_real_presumido', 'Aplicação de modelo no MG Controle', 8),
('ef', 'lucro_real_presumido', 'Verificar obrigatoriedade do SPED', 9),
('ef', 'lucro_real_presumido', 'Confirmar se tem algum regime especial (Carnes ou Restaurante)', 10),
('ef', 'lucro_real_presumido', 'Verificar acessos à prefeitura (IM, LOGIN e SENHA)', 11),
('ef', 'lucro_real_presumido', 'Acesso remoto (verificar se há possibilidade de acessar o sistema do cliente)', 12),
('ef', 'lucro_real_presumido', 'Verificar cadastro SCI WEB e se os relatórios estão devidamente habilitados', 13),
('ef', 'lucro_real_presumido', 'Confirmar se terá portaria CAT e se será feita na MG', 14),
('ef', 'lucro_real_presumido', 'Confirmar se tem algum tipo de compensação efetuada por advogados', 15),
('ef', 'lucro_real_presumido', 'Verificar cadastro no portal nacional', 16),
('ef', 'lucro_real_presumido', 'Para empresas de outros estados, ter um estudo técnico sobre as particularidades do estado', 17);

-- Escrita Fiscal — Simples Nacional
INSERT INTO checklist_itens (departamento, regime, texto, ordem) VALUES
('ef', 'simples_nacional', 'Usuário e senha de acesso ao portal Simples Nacional', 1),
('ef', 'simples_nacional', 'Senha de acesso à prefeitura', 2),
('ef', 'simples_nacional', 'Verificar se o cliente colocou a TAG nas notas emitidas', 3),
('ef', 'simples_nacional', 'Verificar cadastro SCI WEB e se os relatórios estão devidamente habilitados', 4),
('ef', 'simples_nacional', 'Parametrização de empresa no SCI', 5),
('ef', 'simples_nacional', 'Aplicação de modelo no MG Controle', 6),
('ef', 'simples_nacional', 'Verificar acessos à prefeitura (IM, LOGIN e SENHA)', 7);

-- Escrita Fiscal — Fiscal Indústria (checklist único, não varia por regime)
INSERT INTO checklist_itens (departamento, regime, texto, ordem) VALUES
('ef', 'industria', 'Cadastro SCI WEB', 1),
('ef', 'industria', 'Validação TAG', 2),
('ef', 'industria', 'Validação de senhas MG Controle', 3),
('ef', 'industria', 'Validação Extrato Simples Nacional', 4),
('ef', 'industria', 'Validação Sped Fiscal', 5),
('ef', 'industria', 'Validação Sped Contribuição', 6),
('ef', 'industria', 'Papel de Trabalho', 7),
('ef', 'industria', 'Cadastro de produto', 8),
('ef', 'industria', 'Aplicação de modelo', 9),
('ef', 'industria', 'Validação do 1º mês', 10),
('ef', 'industria', 'Validação do 2º mês', 11),
('ef', 'industria', 'Validação do 3º mês', 12),
('ef', 'industria', 'Validação de obrigações acessórias atípicas', 13),
('ef', 'industria', 'Parametrização SCI', 14);

-- Paralegal (regime NULL = aplica a qualquer cliente)
INSERT INTO checklist_itens (departamento, regime, texto, ordem) VALUES
('paralegal', NULL, 'Aguardar o SAC informar os dados de contato do antigo contador', 1),
('paralegal', NULL, 'Entrar em contato com o antigo contador', 2),
('paralegal', NULL, 'Solicitar o certificado digital ao cliente', 3),
('paralegal', NULL, 'Cobrar a documentação do Departamento Pessoal', 4),
('paralegal', NULL, 'Cobrar a documentação do Departamento Fiscal', 5),
('paralegal', NULL, 'Cobrar a documentação do Departamento Contábil', 6),
('paralegal', NULL, 'Verificar se a empresa possui parcelamentos ativos', 7),
('paralegal', NULL, 'Realizar a vinculação no Posto Fiscal', 8),
('paralegal', NULL, 'Realizar o levantamento de débitos', 9),
('paralegal', NULL, 'Realizar o levantamento de SPED', 10),
('paralegal', NULL, 'Comunicar o antigo contador caso haja pendências na documentação', 11),
('paralegal', NULL, 'Atualizar o cadastro do CNPJ com o e-mail e o telefone da MG', 12),
('paralegal', NULL, 'Cancelar as procurações do antigo contador', 13),
('paralegal', NULL, 'Retirar a documentação com o antigo contador', 14);

-- DP (Departamento Pessoal) — regime NULL = aplica a qualquer cliente.
INSERT INTO checklist_itens (departamento, regime, texto, ordem) VALUES
('dp', NULL, 'Procurações', 1),
('dp', NULL, 'Recebimento de Documentos', 2),
('dp', NULL, 'Download eSocial', 3),
('dp', NULL, 'Importação eSocial', 4),
('dp', NULL, 'Validação Cadastral', 5),
('dp', NULL, 'Validação Contratual', 6),
('dp', NULL, 'Validação Histórico de Férias', 7),
('dp', NULL, 'Validação Ficha IRRF', 8),
('dp', NULL, 'Cadastramento Ficha HE''s', 9),
('dp', NULL, 'Cadastramento Ficha RV''s', 10),
('dp', NULL, 'Reunião de Implantação', 11);

-- Gerência de Contas (regime NULL = aplica a qualquer cliente)
INSERT INTO checklist_itens (departamento, regime, texto, ordem) VALUES
('gerencia', NULL, 'Certificados', 1),
('gerencia', NULL, 'Procurações', 2),
('gerencia', NULL, 'Gerar senha Drive MG', 3);

-- ============================================================
-- Consultas de referência (não são views, só documentação de como
-- calcular o progresso quando for implementar o backend):
--
-- Progresso de um departamento para um grupo:
--   SELECT count(*) FILTER (WHERE m.concluido) * 100.0 / count(*)
--   FROM checklist_itens i
--   JOIN checklist_marcacoes m ON m.checklist_item_id = i.id AND m.grupo_id = :grupo_id
--   WHERE i.departamento = :departamento
--     AND (i.regime IS NULL OR i.regime = :regime_do_grupo);
--
-- Ao criar um grupo novo em grupos_implantacao, inserir em
-- checklist_marcacoes uma linha (concluido=false) para cada item
-- de checklist_itens que se aplica a esse grupo (ctb inteiro +
-- só a variante de ef do regime_ef escolhido).
-- ============================================================
