# Harness do reel (commands, skills, agents, hooks, rules)

Fonte extraída: `Instragram-Videos/.claude/` e o espelho `Instragram-Videos/.opencode/` +
`Instragram-Videos/opencode.json`. Aqui fica **como a produção é orquestrada**; os números de cada etapa
estão nos outros arquivos da base.

## Contrato de entrada

- Comandos (`Instragram-Videos/CLAUDE.md:19-30`): `/new-video [owner/repo]`, `/new-video-ia [modelo] [url]`,
  `/new-video-release [owner/repo] [--tag] [url]`, `/curar-repos`, `/revisar-video <slug>`,
  `/analise-reels <token>`, `/publicar` (fora de escopo aqui), `/new-video-youtube-cut` e
  `/new-video-recriado` (cobertos por outros agentes).
- `/new-video` roda **ponta a ponta sem parar para aprovação** (`Instragram-Videos/.claude/commands/new-video.md:7-8`).
- O pedido pode trazer "DECISÃO DO PLANO sobre a abertura gerada" e lista de assuntos a evitar, vindos da
  central (`Instragram-Videos/.claude/commands/new-video.md:37-41`; `Instragram-Videos/.claude/rules/central.md:17-26`).

## Contrato de saída

Entrega do `/new-video` (`Instragram-Videos/.claude/commands/new-video.md:47-54`): caminho e duração do `.mp4`,
saída **real** do `verify.py`, roteiro em texto, palavra do CTA e texto do cartão, se levou abertura e por
decisão de quem (prompt, segundos, se transformou), e veredito do revisor (**PUBLICAR** ou **SEGURAR** —
`Instragram-Videos/.claude/agents/revisor-video.md:135-136`).

## Limites e cotas

Fluxo (`Instragram-Videos/CLAUDE.md:76-88`; `Instragram-Videos/.claude/agents/orquestrador.md:45-62`):
curadoria → (roteiro ‖ captura no repositório; captura **antes** do roteiro em LLM/release, porque a captura
produz `site.md`) → narração → montagem (+ abertura) → revisão. Publicar é etapa separada, só a pedido.

Agentes (`Instragram-Videos/.claude/agents/orquestrador.md:16-27`):

| Agente | Escopo de escrita (hook) | Rules obrigatórias | Gate de saída |
|---|---|---|---|
| orquestrador | nenhum (delega; `tools: Read, Bash, Agent, TodoWrite, Grep, Glob`) | curadoria, segredos, publicacao | — |
| curador | NÃO LIDO em detalhe (fora do genérico) | — | `curador/stop-gate.sh` |
| roteirista | `roteiro.txt, cta.txt, impacto.txt, abertura.txt, legenda.txt, dm.json` (`Instragram-Videos/.claude/hooks/roteirista/pre-edit-scope.sh:9`) | voz-e-cta, veracidade, performance, roteirista/estrutura, curadoria-llm, curadoria-release (`Instragram-Videos/.claude/agents/roteirista.md:23-29`) | palavras, CTA, sem markdown/decimal |
| captura | `capture*.py, stitch.py, captura.json, chunks, strip.png, site.md` (`Instragram-Videos/.claude/agents/captura.md:21-22`) | captura/cdp, formato-entrega | tira 1080×≤16384; `site.md` ≥ 1200 |
| narracao | `tts.py, captions.py, narracao.mp3, alignment.json, legendas.json, caps*` (`Instragram-Videos/.claude/agents/narracao.md:20-21`) | narracao/elevenlabs, segredos, formato-entrega | arquivos + ≥ 5 PNGs |
| montagem | `compose.py, abertura.py, verify.py, lib.py, *.mp4` (`Instragram-Videos/.claude/agents/montagem.md:19-20`) | montagem/ffmpeg, formato-entrega | `verify.py` verde |
| revisor-video | read-only (hook nega Edit/Write e scripts mutáveis) | veracidade, curadoria, curadoria-llm, voz-e-cta, curadoria-corte, formato-entrega | — |

Roteiro de auditoria do revisor (`Instragram-Videos/.claude/agents/revisor-video.md:25-90`): (1) formato — rodar
`verify.py` e colar; (2) veracidade beats 2–6 com linha da fonte (item mais importante; beat 1 não se audita
por lastro); (3) curadoria; (4) voz e CTA (6 beats, sem "Fala pessoal", beat 5 fecha na conexão, sem
algarismo/markdown; dez palavras e filtros de teclado como **SUGESTÃO, nunca BLOQUEANTE**); (5) frame de
abertura: sem texto/logo/UI inventados; tipo `objeto` sem gente; tipo com pessoa: rosto reconhecível, única
pessoa, cartão não encosta no rosto (BLOQUEANTE); transição contínua; no segundo 1 cartão legível, no segundo 3
nome do repositório nítido; selo com a mesma palavra do `cta.txt`. Formato do achado:
`[BLOQUEANTE|IMPORTANTE|SUGESTÃO] título / File / Rule / Detail / Fix` (`:125-133`). Bloqueante volta ao agente
do domínio e revisa de novo (`Instragram-Videos/.claude/agents/orquestrador.md:71-72`).

Skills (procedimento para retomar do meio): `gerar-reel-repo`, `gerar-reel-llm`, `gerar-reel-release` —
tabelas "Existe / Falta / Próximo comando" (`Instragram-Videos/.claude/skills/gerar-reel-repo/SKILL.md:78-90`;
`Instragram-Videos/.claude/skills/gerar-reel-llm/SKILL.md:75-85`), red flags e checklist final
(`Instragram-Videos/.claude/skills/gerar-reel-repo/SKILL.md:60-106`). Todos os passos são reexecutáveis, exceto o
TTS (custa dinheiro) (`:43-44`); ajustar legenda roda só `captions.py` + `compose.py` (`:75-76`).

Hooks: `PreToolUse` (escopo de edição + guarda de bash) e `Stop` (gate) por agente, declarados no frontmatter
do agente (`Instragram-Videos/.claude/agents/roteirista.md:8-15`). No OpenCode não há `Stop`: o plugin roda o
mesmo `stop-gate.sh` depois de cada comando `pipeline/*.py` ou `browser-harness` do agente
(`Instragram-Videos/.opencode/plugin/gates.ts:3-27`); `command/` é symlink para `.claude/commands`.

Regras transversais: nunca publicar sem pedido; commit/push só sob pedido (bloqueado por hook); chave nunca
em log/argv; não regenerar TTS "para testar" (`Instragram-Videos/.claude/rules/segredos.md:1-16`); "Nunca peça
ao usuário para rodar comando" (`Instragram-Videos/.claude/agents/orquestrador.md:69`); contratar agente novo
só com OK do usuário, no mesmo padrão agente + hooks + rule (`:74-78`).

## Erros conhecidos e tratamento

| Situação | Tratamento | Referência |
|---|---|---|
| Assunto recusado pela curadoria | parar e explicar o eixo/barreira; não contornar | `Instragram-Videos/.claude/commands/new-video.md:26-27` |
| Nenhuma página oficial responde | curador busca na web e passa `--site`; nunca inventar URL | `Instragram-Videos/.claude/commands/new-video-ia.md:48-50` |
| Revisor acha BLOQUEANTE | devolve ao agente culpado e revisa de novo | `Instragram-Videos/.claude/commands/new-video.md:45-46` |
| Pedido fora dos domínios | avisar e pedir OK antes de criar agente | `Instragram-Videos/.claude/agents/orquestrador.md:74-78` |
| Aba errada fechada / `activate_tab` | hook bloqueia `activate_tab` na captura | `Instragram-Videos/.claude/hooks/captura/pre-bash-guard.sh:6` |

## Riscos para a nossa implementação

- **Marca no harness**: "narrado na voz do Thulio" (`Instragram-Videos/.claude/commands/new-video.md:7`),
  "Thulio" em `CLAUDE.md`, agentes e regras; central em `../Instagram-Carrosseis` com `cerebro.py`,
  `biblioteca.py`, `galeria/retratos` (`Instragram-Videos/.claude/rules/central.md:3-57`). M13 exige que prompts de
  agente não citem pessoa — tudo vira referência à Alma.
- **Contrato de arquivo com a central**: nomes `repo.json, modelo.json, release.json, corte.json, recriado.json,
  publicacao.json, abertura.json.montado_em` são contrato da ponte `reels.py`
  (`Instragram-Videos/.claude/rules/central.md:11-16,31-32`). No ExpxMedia isso é substituído por `peca.json`;
  os marcadores podem ficar como detalhe do pack.
- Stop-gate por "pasta mais recente" (`ls -td`) falha com produção concorrente (ver `verificar-reel-gates.md`).
- Guardas de bash por padrão de string (`*deploy*`, `*"rm -rf"*`) são contornáveis e bloqueiam falso-positivo;
  servem de barreira, não de segurança.
- O que derruba a qualidade se extraído de forma ingênua:
  1. Colapsar os agentes num só: perde-se o gate por domínio e o revisor independente read-only.
  2. Paralelizar roteiro e captura quando a fonte é produzida pela captura → roteiro sem lastro.
  3. Permitir "verde" sem saída real colada → entregas não verificadas.
  4. Deixar o revisor corrigir → perde a independência da auditoria.
  5. Rodar TTS/abertura em retries automáticos → gasto de crédito.
- Documentação desatualizada dentro do harness (decidir a versão certa antes de extrair): `hold inicial 2,0s`
  na skill (`Instragram-Videos/.claude/skills/gerar-reel-repo/SKILL.md:53`) vs 3,5s no código; `header.AppHeader`
  em `cdp.md:35`; `cartao_y` inexistente em `performance.md:414`; `new-video-release.md` sem frontmatter de
  `description` (`Instragram-Videos/.claude/commands/new-video-release.md:1`).
- Testes: `python3 -m pytest` (pytest 9.0.3) em `Instragram-Videos/tests/` (41 definições `def test`, nenhuma sobre
  o pipeline narrado de repositório/LLM/release); `conftest.py` bloqueia rede e gera vídeo sintético. Não há
  `requirements.txt`/`pyproject.toml` no projeto.

## Fonte

- `Instragram-Videos/CLAUDE.md` (1–167)
- `Instragram-Videos/.claude/commands/new-video.md`, `new-video-ia.md`, `new-video-release.md`, `revisar-video.md`
- `Instragram-Videos/.claude/skills/gerar-reel-repo/SKILL.md`, `gerar-reel-llm/SKILL.md`, `gerar-reel-release/SKILL.md`
- `Instragram-Videos/.claude/agents/orquestrador.md`, `roteirista.md`, `narracao.md`, `montagem.md`, `captura.md`, `revisor-video.md`
- `Instragram-Videos/.claude/hooks/*/` (stop-gate, pre-bash-guard, pre-edit-scope, revisor pre-tool-use)
- `Instragram-Videos/.claude/rules/segredos.md`, `central.md`
- `Instragram-Videos/.opencode/plugin/gates.ts`, `Instragram-Videos/opencode.json`
- `Instragram-Videos/tests/` (conftest.py, test_harness.py, test_verify_recriado.py)
- Git: um único commit (`cc1e39d`, 2026-09-17); `.claude/`, `pipeline/`, `tests/` estão não rastreados.
