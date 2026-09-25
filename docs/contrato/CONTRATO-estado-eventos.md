# Contrato `expxmedia-estado` v1 — estado, eventos, plano e relatórios

Os projetos de origem já convergiram para a mesma forma — daily em JSONL, decisões em JSONL,
plano do dia em JSON, relatório com colunas e KPIs — porque foram copiados uns dos outros. Este
contrato escreve essa forma **uma vez**, sem o que era de uma pessoa ("o que o Thulio escreve
vence" vira "o que a pessoa escreve vence"), para que todos os packs falem a mesma língua e o
painel leia tudo sem saber quem escreveu.

**O estado responde "onde está"** (`peca.json`, plano do dia). **O rastro responde "o que
aconteceu e quando"** (eventos). **A daily e as decisões respondem "o que foi combinado".**

---

## Onde fica

```
estado/
  daily.jsonl          conversa de trabalho entre a pessoa e os agentes
  decisoes.jsonl       mudanças de regra, de processo, de estratégia
  chat.jsonl           a reunião do painel
eventos/
  2026-09.jsonl        o rastro, um arquivo por mês
planejamento/
  2026-09-24.json      plano do dia (máquina)
  2026-09-24.md        o mesmo plano, legível (pessoa)
relatorios/
  2026-09-24/
    expx-instagram-desempenho.json
```

Todos versionáveis, exceto `chat.jsonl` (conversa pode ter dado sensível; a instalação o coloca no
ignorado). Todo JSONL é só-acréscimo com trava (M15).

## O rastro de eventos — `eventos/AAAA-MM.jsonl`

Uma linha por evento. Escrito por skills, agentes, hooks, rotina e painel. Ninguém edita à mão.

```json
{"ts":"2026-09-24T09:12:00-03:00","expxmedia_eventos":1,"pack":"expx-instagram","origem":"skill","evento":"geracao_concluida","peca_id":"P-20260924-A3F9","agente":"geradores","capacidade":"renderizar_html","provedor":"playwright","resultado":"ok","detalhe":"3 slides em 57,5 s","arquivos":["pecas/2026-09/P-20260924-A3F9-imposto-mal-enquadrado/slides/slide_02.png"]}
```

### As doze chaves obrigatórias, nesta ordem

`ts` · `expxmedia_eventos` · `pack` · `origem` · `evento` · `peca_id` · `agente` · `capacidade` ·
`provedor` · `resultado` · `detalhe` · `arquivos`

Nenhuma é omitida (M7). Chaves extras são permitidas **depois** das doze, se declaradas na tabela
de extras abaixo. Validador verifica que as doze estão **contidas** na linha, nunca igualdade
exata de conjunto — a lição do expxdev, onde o validador estrito passou a reprovar skills que
usavam extras legítimas.

### Enums

| Campo | Valores |
|---|---|
| `pack` | nome de um pack ou camada instalada, ou `nucleo` |
| `origem` | `skill` · `agente` · `hook` · `rotina` · `painel` · `humano` |
| `resultado` | `ok` · `falha` · `aviso` · `bloqueado` |

### Vocabulário de `evento`

| Evento | Quando |
|---|---|
| `alma_criada` · `alma_atualizada` | portão da Alma concluído; edição da Alma detectada |
| `ambiente_configurado` | `/expxmedia:ambiente` concluído |
| `capacidade_ausente` | uma ação foi pedida e o requisito não estava habilitado |
| `peca_criada` | `peca.json` gravado pela primeira vez |
| `peca_status` | mudou o `status` da peça; `detalhe` = `"roteiro -> produzida"` |
| `geracao_concluida` · `geracao_falhou` | uma chamada de capacidade terminou |
| `publicacao_agendada` · `publicacao_concluida` · `publicacao_falhou` | idem, por canal |
| `metricas_coletadas` | uma coleta de métricas de uma peça; a extra `valores` leva os números |
| `template_criado` · `template_validado` · `template_enviado` · `template_recusado` · `template_baixado` | ciclo da galeria |
| `plano_gerado` · `vaga_status` | plano do dia |
| `hook_decidiu` | um hook permitiu, avisou ou bloqueou; a extra `hook` diz qual |

### Chaves extras declaradas

| Chave | Quem grava | O que é |
|---|---|---|
| `hook` | hooks | nome do hook, quando `origem: hook` |
| `segundos` | `geracao_*` | duração da chamada |
| `valores` | `metricas_coletadas` | o mesmo objeto de `peca.metricas.valores` |
| `template_id` | eventos de galeria | o template envolvido |
| `vaga` | `vaga_status` | `{ "data": "2026-09-24", "id": "v3" }` |

`geracoes.jsonl` dos carrosséis deixa de existir como arquivo separado: cada geração é um evento
`geracao_concluida`, e o que ele guardava de editorial (`gancho_tipo`, `cta_forma`, `leitor`) passa
a viver no `peca.json`.

O rastro dá, sem ninguém anotar, **o custo real de cada peça** — tempo por capacidade, falhas por
provedor, quanto uma aula demora do roteiro à publicação — e é isso que calibra o plano do dia.

## Daily — `estado/daily.jsonl`

A conversa de trabalho: a pessoa pede, orienta, pergunta; os agentes respondem e reportam.

```json
{"quando":"2026-09-24T04:09:20-03:00","id":"d016","autor":"planejador","evento":"resposta","responde_a":"d014","texto":"Progresso: 1 de 3. O item 001 foi ao ar em 23/09 às 17:30.","status":"fazendo","onde":"planejamento/2026-09-24.json#v3"}
```

| Campo | Valores / formato |
|---|---|
| `id` | `d<NNN>`, sequencial por instalação |
| `autor` | `humano` ou nome do agente |
| `evento` | `pedido` · `orientacao` · `pergunta` · `resposta` · `relato` |
| `responde_a` | id da entrada respondida, ou `null` |
| `status` | `aberto` · `fazendo` · `feito` · `descartado` |
| `onde` | caminho relativo (M9) com âncora opcional, ou `null` |

**O que a pessoa escreve vence.** Uma `orientacao` de `autor: humano` prevalece sobre qualquer regra
editorial, plano ou análise automática até ser revogada por outra entrada dela. Agente nunca
escreve `autor: humano`.

## Decisões — `estado/decisoes.jsonl`

Toda mudança de regra, processo ou estratégia — tomada por pessoa ou por agente autorizado.

```json
{"quando":"2026-09-24T11:48:30-03:00","id":"D-042","autor":"rotina","tipo":"melhoria","o_que":"Reels recriados passam a ser agendados em horário livre","por_que":"Pedido na daily d012","evidencia":"docs/reels-recriados/","como_desfazer":"remover o tipo reel do plano de recriação"}
```

| Campo | Valores |
|---|---|
| `tipo` | `regra` · `melhoria` · `correcao` · `estrategia` · `experimento` · `reversao` |

`como_desfazer` é obrigatório e nunca `null`: decisão sem caminho de volta não é registrada.

## Plano do dia — `planejamento/AAAA-MM-DD.json`

O que vai ser produzido e publicado hoje, em vagas. Um plano por dia **para a instalação toda**:
os packs contribuem vagas para o mesmo plano, e o limite do dia é um só.

```json
{
  "expxmedia_plano": 1,
  "data": "2026-09-24",
  "gerado_em": "2026-09-24T04:06:46-03:00",
  "atualizado_em": "2026-09-24T09:15:00-03:00",
  "analise_base": "relatorios/2026-09-24",
  "regras": {
    "max_feed_dia": 3,
    "max_reels_dia": 2,
    "max_por_serie_dia": 1,
    "nota_minima": 4.0,
    "publicacao_automatica": true
  },
  "vagas": [
    {
      "id": "v1",
      "hora": "07:00",
      "pack": "expx-instagram",
      "tipo": "post_unico",
      "formato": "4:5",
      "canal": "instagram",
      "serie": "frase-do-dia",
      "template": null,
      "peca_id": "P-20260924-0B1C",
      "modo": "produzir",
      "fixa": true,
      "origem": "daily d005",
      "motivo": "vaga fixa pedida na daily d005",
      "requisitos": ["renderizar_html", "agendar"],
      "status": "agendada"
    }
  ]
}
```

| Campo | Valores |
|---|---|
| `vagas[].modo` | `produzir` · `reaproveitar` · `publicar_pronta` |
| `vagas[].status` | `pendente` · `produzindo` · `produzida` · `agendada` · `publicada` · `falhou` · `cancelada` |

Regras:

1. **Vaga só existe se `requisitos` estiver habilitado** no momento em que o plano é gerado
   ([`CONTRATO-capacidades.md`](./CONTRATO-capacidades.md)). Plano não promete o que não dá para
   fazer.
2. `fixa: true` é vaga pedida pela pessoa: fica fora do limite, da nota mínima e do rodízio.
3. `regras` é a cópia das regras vigentes **no momento** do plano; a fonte é
   `editorial/cadencia.json` do pack, não este arquivo.
4. O `.md` do mesmo dia é gerado a partir do JSON, nunca o contrário (M1).

## Relatórios — `relatorios/AAAA-MM-DD/<pack>-<id>.json`

O formato que o `relatorios.py` do YouTube e dos carrosséis já usa, e que o painel desenha sem
conhecer o pack:

```json
{
  "expxmedia_relatorio": 1,
  "id": "expx-instagram-desempenho",
  "pack": "expx-instagram",
  "titulo": "Desempenho dos últimos 30 dias",
  "categoria": "desempenho",
  "gerado_em": "2026-09-24T04:05:00-03:00",
  "periodo": { "de": "2026-08-25", "ate": "2026-09-23" },
  "kpis": [
    { "id": "alcance_medio", "rotulo": "Alcance médio", "valor": 1840, "unidade": null, "variacao": 0.12 }
  ],
  "colunas": [
    { "id": "peca_id", "rotulo": "Peça", "tipo": "texto" },
    { "id": "salvos", "rotulo": "Salvos", "tipo": "numero" }
  ],
  "linhas": [
    { "peca_id": "P-20260920-77AA", "salvos": 51 }
  ],
  "fontes": ["pecas/2026-09/P-20260920-77AA-*/peca.json"]
}
```

| Campo | Valores |
|---|---|
| `categoria` | `desempenho` · `editorial` · `financeiro` · `operacao` |
| `colunas[].tipo` | `texto` · `numero` · `percentual` · `moeda` · `data` · `link` |

`variacao` é fração (`0.12` = +12%), ou `null`.

## Leitores

| Quem | Lê | Escreve |
|---|---|---|
| **Painel** | tudo deste contrato + `peca.json` + `template.json` | `daily.jsonl` e `chat.jsonl` (pela pessoa), eventos `origem: painel` |
| **Skills e agentes** | tudo | o que o escopo do agente permite ([`CONTRATO-pack.md`](./CONTRATO-pack.md)) |
| **Rotina** (cron) | plano, cadência, métricas | plano, eventos `origem: rotina` |
| **Hooks** | o payload do harness e `.expxmedia/hooks.json` | só eventos `hook_decidiu` |
