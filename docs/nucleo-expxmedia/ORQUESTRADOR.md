---
expx_schema: 1
expx_tool: sprintx
kind: orquestrador
trabalho_id: nucleo-expxmedia
titulo: Nucleo do ExpxMedia - motor de capacidades e producao generica dos cinco tipos de peca
tipo_trabalho: feature
tipo_ocorrencia: null
estagio: f6
status: em_andamento
criado_em: 2026-09-24
atualizado_em: 2026-09-24
concluido_em: null
sprints: [sprint-01, sprint-02, sprint-03, sprint-04, sprint-05, sprint-06, sprint-07, sprint-08, sprint-09, sprint-10]
caminho_critico: [T-01.01, T-01.02, T-01.03, T-02.04, T-02.05, T-02.06, T-02.07, T-04.03, T-04.04, T-04.05, T-05.06, T-06.03, T-06.09, T-09.06, T-10.03, T-10.04, T-10.05]
---

# Orquestrador — nucleo-expxmedia

> Porta de entrada da execução. Escrito para quem abriu o repositório agora e não sabe nada. Só caminhos relativos; nunca o valor de um segredo.

## 1. Objetivo

Construir o núcleo genérico do ExpxMedia: um motor Python (`motor/`) com todas as capacidades do catálogo do núcleo (render HTML, motion Remotion, vídeo, narração, transcrição, legenda, avatar, imagem, vídeo por IA, banco de imagens, captura, publicação e agendador local) e a produção dos cinco tipos de peça (post único, carrossel inclusive misto, reel, apresentação, aula), mais o plugin `nucleo/` do Claude Code com portão, Alma, ambiente, skills e agentes. Tudo extraído de Instagram-Carrosseis, Instragram-Videos, cursos-ia, youtube-squad e ExpxMeta **sem nenhuma marca** e **sem perder a inteligência e a qualidade atuais**, seguindo os contratos de `docs/contrato/`.

## 2. Mapa e ordem de leitura

1. Este arquivo (`docs/nucleo-expxmedia/ORQUESTRADOR.md`)
2. `docs/contrato/CONVENCOES.md` e os seis contratos em `docs/contrato/` — o que todo artefato precisa respeitar
3. `docs/nucleo-expxmedia/00-DECISOES.md` — 49 decisões e 2 pendências não bloqueantes
4. `docs/nucleo-expxmedia/base/00-INDICE.md` — e os 37 arquivos da base; antes de cada task, leia os arquivos da base citados no objetivo e o código de origem que eles apontam
5. `docs/nucleo-expxmedia/base/00-LACUNAS.md`
6. `docs/nucleo-expxmedia/sprint-01/sprint.md` → `fases.md` → `tasks.md`
7. `sprint-02/` até `sprint-10/`, na ordem, cada um `sprint.md` → `fases.md` → `tasks.md`
8. `docs/nucleo-expxmedia/00-BLOQUEIOS.md` — bloqueios registrados durante a execução
9. `docs/nucleo-expxmedia/00-AUDITORIA.md` — achados MÉDIA/BAIXA que permanecem válidos

## 3. Rota de execução

As sprints são sequenciais por padrão: uma sprint só começa com o critério de saída da anterior atendido. As exceções declaradas abaixo valem porque os critérios de saída das sprints 04 a 08 cobrem só as pastas de teste de cada uma; a suíte inteira é cobrada no portão da sprint 09 e na sprint 10. Dentro de cada sprint, fases marcadas ∥ rodam em paralelo; dentro de cada fase, só rodam em paralelo as tasks com `paralelizavel: true` cujas dependências já estão `concluida`.

- **Sprint 01 — Capacidade de testar:** F-01.1 → F-01.2
- **Sprint 02 — Fundação dos contratos:** F-02.1 → (F-02.2 ∥ F-02.3) → F-02.4
- **Sprint 03 — Imagem estática:** (F-03.1 ∥ F-03.2) → F-03.3
- **Sprint 04 — Áudio, texto e vídeo básico:** F-04.1 → (F-04.2 ∥ F-04.3) → F-04.4
- **Sprint 05 — Motion:** F-05.1 → (F-05.2 ∥ F-05.3 ∥ F-05.4) → F-05.5
- **Sprint 06 — Referência e corte:** (F-06.1 ∥ F-06.2 ∥ F-06.3) → F-06.4. F-06.2 e F-06.3 dependem só das sprints 03 e 04 e podem começar junto com a sprint 05.
- **Sprint 07 — Aula e avatar:** F-07.1 → F-07.2. Depende só das sprints 04 e 05 e pode rodar junto com a sprint 06.
- **Sprint 08 — Publicação e agendador:** F-08.1 → F-08.2 → F-08.3. Exceção ao portão entre sprints: a sprint 08 depende só das sprints 02 e 04 e pode rodar em paralelo com as sprints 05 a 07.
- **Sprint 09 — Plugin do núcleo:** F-09.1 → F-09.2. F-09.1 depende só das sprints 01 a 03 e pode rodar junto com as sprints 04 a 08; F-09.2 começa com as sprints 05 a 08 concluídas.
- **Sprint 10 — Validação ponta a ponta:** F-10.1 → F-10.2

**Caminho crítico** (cadeia mais longa de `depende_de`, 17 tasks): T-01.01 → T-01.02 → T-01.03 → T-02.04 → T-02.05 → T-02.06 → T-02.07 → T-04.03 → T-04.04 → T-04.05 → T-05.06 → T-06.03 → T-06.09 → T-09.06 → T-10.03 → T-10.04 → T-10.05.

## 4. Ferramentas

- **Rede (uma vez, na T-01.08):** `uv sync`, `npm ci` do kit, `npx remotion browser ensure` (chrome-headless-shell), `uv run playwright install chromium` e o Google Fonts do golden (T-01.07). Depois disso a suíte roda offline. Sem rede, T-01.08 vira bloqueio.
- **MCPs / SDKs:** nenhum MCP obrigatório. Python 3.11+ com `uv`; Node 20 com npm para o kit Remotion; binários locais `ffmpeg` (8.x, sem libass), `say` (macOS, fala sintética dos testes de corte), `claude` (para `claude plugin validate nucleo`), `whisper`/`faster-whisper`, Chromium do Playwright (`uv run playwright install chromium`), `cloudflared` e `higgsfield` (os dois últimos substituídos por executáveis falsos nos testes).
- **Testes:** `cd motor && uv run pytest` (suíte inteira); por task, o comando está no `criterio_aceite`. Testes que exigem binário local usam o marcador `integracao_local` e devem rodar, não pular, nesta máquina.
- **Modelos em cache:** faster-whisper `small` em `~/.cache/huggingface/hub` (a suíte roda com `HF_HUB_OFFLINE=1`) e `u2net.onnx` do rembg em `~/.u2net`.
- **Typecheck do kit:** `cd motor/kit-remotion && npx tsc --noEmit`
- **Lint:** NÃO EXISTE NO PROJETO.
- **Typecheck Python:** NÃO EXISTE NO PROJETO.
- **Segredos:** nenhum é necessário para executar este plano (D-15). Os nomes canônicos (`ELEVENLABS_API_KEY`, `HEYGEN_API_KEY`, `OPENROUTER_API_KEY`, `PEXELS_API_KEY`, `EXPXFLOW_API_KEY`, `EXPXFLOW_CLIENT_ID`, `META_GRAPH_TOKEN`, `META_IG_USER_ID`, `META_PAGE_ID`, `PROVEDOR_*`) ficam no `.env` da raiz de cada instalação e, nos testes, em `.env` gerados pela fixture com valores falsos. **Nunca leia os `.env` dos projetos de origem.**
- **Projetos de origem:** `../Instagram-Carrosseis`, `../Instragram-Videos`, `../cursos-ia`, `../youtube-squad`, `../ExpxMeta` (relativos à pasta `ExpxMedia`). Somente leitura; código antigo só roda em cópia temporária (D-37).

## 5. Agentes

- **Implementador** — lê a base e o código de origem citados, escreve primeiro os dois testes da task, vê ambos falharem, implementa até passarem.
- **Revisor de testes** — antes de aceitar o verde, responde: este teste falharia com uma implementação errada (ou com o número calibrado trocado)? Se não, o teste volta.
- **Auditor de aceite** — roda o comando do `criterio_aceite`, confere 0 failed (e 0 skipped quando exigido), roda `tests/test_marca.py` quando a task criou arquivos em `motor/src`, `motor/kit-remotion`, `nucleo/` ou `templates/`, e só então permite `status: concluida`.

**Agente único:** assume os três papéis em sequência dentro de cada task, nesta ordem, tratando cada papel como um portão — não avança ao papel seguinte sem fechar o anterior. Com subagentes disponíveis, tasks paralelizáveis de uma mesma janela podem ir para subagentes distintos, cada um fazendo os três papéis na sua task; o orquestrador consolida `tasks.md`.

## 6. Regras de autonomia

1. Não pergunte nada; não peça autorização para nada.
2. O teste vem antes do código, sempre.
3. Task só é `concluida` com teste de integração E funcional passando e `criterio_aceite` verificado. Não existe "concluído com ressalva".
4. Dúvida nova ou pré-requisito faltando: registrar em `00-BLOQUEIOS.md` (`B-NN | task | bloqueio | o que destravaria`), marcar a task `bloqueada`, pular para a próxima paralelizável. Nunca parar e esperar.
5. Só rode em paralelo o que o plano declarou paralelizável; a execução nunca decide paralelismo.
6. Atualize `status` em `tasks.md` (prosa e YAML) a cada transição; ao concluir, preencha `concluida_em` e `suite`.
7. Critério de saída de fase/sprint não atendido = não avança.
8. Nenhuma chamada paga a provedor e nenhuma publicação real (D-15). Nenhuma escrita nos projetos de origem (D-37).
9. Números calibrados (limiares, pesos, tempos) são portados com o mesmo valor e a referência `arquivo:linha` de origem num comentário; mudar um número exige decisão D-NN nova, registrada como bloqueio se surgir na execução.

## 7. Definição de pronto global

- [ ] `cd motor && uv run pytest` termina com 0 failed e 0 skipped nesta máquina (critério de saída da sprint-10).
- [ ] `tests/test_marca.py` passa sobre `motor/src`, `motor/kit-remotion`, `nucleo/` e `templates/` (D-02, M13).
- [ ] Com a Alma fictícia e sem nenhuma chave, o núcleo produz post único, carrossel, carrossel misto, apresentação, reel narrado, reel de página e aula com `peca.json` válido (D-35, T-10.01).
- [ ] Publicação em dry-run funciona pelos dois provedores contra stubs, sem troca silenciosa (D-07, T-10.02).
- [ ] Um reel por referência foi produzido seguindo a skill, com verificação `sob_medida` aprovada e checklist de parecença gravado (D-04, D-18, T-10.03).
- [ ] Os testes de paridade com o sistema atual (render HTML, montagem e trilha, legendas) passam (D-16).
- [ ] `claude plugin validate nucleo` termina com código 0 e toda skill cita só subcomandos existentes do CLI e contém as âncoras de inteligência (D-33, D-45).
- [ ] `docs/contrato/CONTRATO-alma.md` traz os parâmetros e o léxico de voz do porta-voz (D-22).

## 8. Como retomar uma sessão interrompida

1. Leia este arquivo inteiro.
2. Leia o `status` de cada task em cada `docs/nucleo-expxmedia/sprint-NN/tasks.md`.
3. Leia `docs/nucleo-expxmedia/00-BLOQUEIOS.md`.
4. Continue da primeira task `pendente` ou `em_andamento` cujas dependências (`depende_de`) estão todas `concluida`. Ignore as `bloqueada` até que o bloqueio registrado seja resolvido.
