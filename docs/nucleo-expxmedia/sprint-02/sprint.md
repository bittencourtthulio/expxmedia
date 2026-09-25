---
expx_schema: 1
expx_tool: sprintx
kind: sprint
trabalho_id: nucleo-expxmedia
sprint_id: sprint-02
titulo: "Fundacao dos contratos"
status: concluido
criterio_saida: "cd motor && uv run pytest termina com 0 failed e uv run expxmedia-motor capacidades roda na fixture"
fases: [F-02.1, F-02.2, F-02.3, F-02.4]
riscos: ["fcntl nao existe no Windows; usar filelock (base/infra-estado-e-plano.md)", "Google Fonts exige rede; testes usam stub (D-21)"]
atualizado_em: 2026-09-25
---

# Sprint 02 — Fundacao dos contratos

## Objetivo

Implementa as convenções, o rastro, o ambiente e as capacidades, a Alma, a peça, o template, a galeria local e o CLI base.

## Fases

| Fase | Título | Roda em paralelo com |
|---|---|---|
| F-02.1 | Arquivos, ids e rastro | nenhuma |
| F-02.2 | Ambiente e capacidades | F-02.3 |
| F-02.3 | Alma, peca e template | F-02.2 |
| F-02.4 | Galeria local e CLI base | nenhuma |

Detalhe de cada fase em `fases.md`; tasks em `tasks.md`.

## Critério de saída

`cd motor && uv run pytest` termina com 0 failed e `uv run expxmedia-motor capacidades` roda na fixture

## Riscos conhecidos

- fcntl nao existe no Windows; usar filelock (base/infra-estado-e-plano.md)
- Google Fonts exige rede; testes usam stub (D-21)
