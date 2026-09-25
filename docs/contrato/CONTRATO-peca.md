# Contrato `expxmedia-peca` v1

Uma **peça** é qualquer coisa produzida para ser publicada ou apresentada: um post, um
carrossel, um reel, uma apresentação, uma aula. Todo pack registra toda peça do mesmo jeito,
num `peca.json` — é isso que deixa o painel mostrar tudo numa linha do tempo só, a análise
comparar um reel com um carrossel, e a galeria saber que template dá resultado.

Hoje cada projeto de origem registra à sua maneira (`repo.json`/`corte.json` nos vídeos,
`uploads.json` nos carrosséis, `deck.json` + `estado.json` no YouTube, nada nos cursos). Na
extração, todos passam a gravar `peca.json`; o marcador antigo pode continuar existindo
**dentro** da pasta como detalhe do pack, mas nenhum leitor de outro pack depende dele.

---

## Os tipos

| `tipo` | Formatos aceitos | Saída principal | Notas |
|---|---|---|---|
| `post_unico` | `4:5` · `1:1` · `9:16` | 1 PNG | |
| `carrossel` | `4:5` · `1:1` | N slides, cada um PNG **ou MP4** | carrossel misto: cada slide declara a própria `midia` |
| `reel` | `9:16` | MP4 | |
| `apresentacao` | `16:9` | HTML navegável (simula PPT) | opcionalmente PNG por slide e MP4 |
| `aula` | `16:9` e/ou `9:16` | MP4 + SRT por formato | é uma composição: pode conter uma apresentação |

`formatos` é sempre uma lista, porque uma aula sai em 16:9 e 9:16 da mesma fonte. Para os
demais tipos, a lista tem um item.

Os limites de cada plataforma — quantos slides cabem, duração máxima de vídeo, proporção
obrigatória — **não** estão aqui: são regras do pack do canal. Este contrato descreve a peça; o
pack decide se ela cabe onde vai ser publicada.

## Onde fica

```
pecas/
  2026-09/
    P-20260924-A3F9-imposto-mal-enquadrado/
      peca.json
      texto/        legenda.txt, roteiro.md, notas.md
      slides/       slide_01.png, slide_02.mp4 ...
      midia/        narracao.mp3, alinhamento.json, avatar.mp4 ...
      saida/        o que vai ao ar: final.mp4, apresentacao.html, aula-16x9.srt ...
      previa/       prancha.png, capa.png
```

A pasta é `<AAAA-MM>/<peca_id>-<slug>/`, com o mês de **criação**. As subpastas são
recomendadas, não obrigatórias: o que vale é a lista `arquivos` do `peca.json`, com caminhos
relativos (M9).

## O ciclo de vida

```
ideia → roteiro → produzida → aprovada → agendada → publicada → medida
                                   ╲
                                    descartada   (de qualquer estado antes de publicada)
```

| `status` | Significa |
|---|---|
| `ideia` | pauta registrada, nada produzido |
| `roteiro` | texto pronto (roteiro, copy, slots preenchidos) |
| `produzida` | arquivos de saída gerados e verificados |
| `aprovada` | aprovada para ir ao ar (por pessoa, ou pela regra de publicação automática do plano) |
| `agendada` | tem pelo menos uma publicação com `estado: agendada` |
| `publicada` | tem pelo menos uma publicação com `estado: publicada` |
| `medida` | tem métricas coletadas |
| `descartada` | não vai ao ar; `motivo_descarte` preenchido |

Falha de produção **não é status**: é evento no rastro (`geracao_falhou`), e a peça continua no
estado anterior. Uma peça que tentou renderizar três vezes e não conseguiu ainda é `roteiro`, com
três falhas registradas.

## `peca.json`

```json
{
  "expxmedia_peca": 1,
  "peca_id": "P-20260924-A3F9",
  "slug": "imposto-mal-enquadrado",
  "titulo": "Seu imposto não é caro, está mal enquadrado",
  "tipo": "carrossel",
  "formatos": ["4:5"],
  "status": "agendada",
  "pack": "expx-instagram",
  "serie": "mitos-do-imposto",
  "template": "carrossel-editorial-azul-3fa2c1",
  "porta_voz": null,
  "oferta": "consultoria-inicial",
  "vaga": { "data": "2026-09-25", "id": "v3" },

  "criada_em": "2026-09-24T09:10:00-03:00",
  "atualizado_em": "2026-09-24T11:40:00-03:00",
  "motivo_descarte": null,

  "conteudo": {
    "gancho": "Seu imposto não é caro.",
    "gancho_tipo": "contraste",
    "cta": "Comente CONTA que eu te mando o checklist",
    "cta_forma": "comentario",
    "legenda": "texto/legenda.txt",
    "roteiro": null
  },

  "slides": [
    { "n": 1, "kind": "capa",    "midia": "video",  "arquivo": "slides/slide_01.mp4", "duracao_s": 6 },
    { "n": 2, "kind": "numero",  "midia": "imagem", "arquivo": "slides/slide_02.png", "duracao_s": null },
    { "n": 3, "kind": "frase",   "midia": "imagem", "arquivo": "slides/slide_03.png", "duracao_s": null }
  ],

  "compoe": [],

  "arquivos": [
    { "caminho": "slides/slide_01.mp4", "papel": "slide",   "formato": "4:5" },
    { "caminho": "slides/slide_02.png", "papel": "slide",   "formato": "4:5" },
    { "caminho": "slides/slide_03.png", "papel": "slide",   "formato": "4:5" },
    { "caminho": "texto/legenda.txt",   "papel": "legenda", "formato": null },
    { "caminho": "previa/prancha.png",  "papel": "previa",  "formato": null }
  ],

  "producao": {
    "capacidades": ["renderizar_html", "renderizar_motion"],
    "provedores": { "renderizar_html": "playwright", "renderizar_motion": "remotion" },
    "segundos": 57.5,
    "produzida_em": "2026-09-24T09:12:00-03:00"
  },

  "publicacoes": [
    {
      "canal": "instagram",
      "provedor": "expxflow",
      "estado": "agendada",
      "agendada_para": "2026-09-25T12:00:00-03:00",
      "publicada_em": null,
      "id_externo": "sched_8f2a",
      "url": null,
      "automacao_dm": { "palavra": "CONTA", "id_externo": "trg_19c" },
      "erro": null
    }
  ],

  "metricas": null
}
```

### Campos

| Campo | Obrigatório | O que é |
|---|---|---|
| `pack` | sim | o pack que criou a peça |
| `serie` | não (`null`) | agrupamento editorial do pack (as "séries" dos carrosséis, as "linhas" dos cursos) |
| `template` | não (`null`) | o template da galeria usado; `null` quando a peça foi feita sem template |
| `porta_voz` | não (`null`) | id do porta-voz da Alma que aparece ou fala na peça |
| `oferta` | não (`null`) | id da oferta da Alma que a peça promove |
| `vaga` | não (`null`) | a vaga do plano do dia que originou a peça |
| `conteudo` | sim | o essencial do texto, para análise sem abrir arquivo. Texto longo fica em arquivo, e aqui vai o caminho |
| `slides` | `carrossel`, `post_unico`, `apresentacao`: sim; demais: `[]` | um por slide, na ordem |
| `compoe` | sim (`[]` se nada) | ids das peças que esta usa — a aula aponta para a apresentação que roda dentro dela |
| `arquivos` | sim | tudo o que a peça gerou e importa; o que não está aqui é rascunho |
| `producao` | sim depois de `produzida` | capacidades e provedores **efetivamente** usados, e o tempo gasto |
| `publicacoes` | sim (`[]` se nenhuma) | uma entrada por canal |
| `metricas` | `null` até a primeira coleta | ver abaixo |

### Enums

| Campo | Valores |
|---|---|
| `tipo` | `post_unico` · `carrossel` · `reel` · `apresentacao` · `aula` |
| `formatos[]`, `arquivos[].formato` | `4:5` · `1:1` · `9:16` · `16:9` · `null` |
| `status` | `ideia` · `roteiro` · `produzida` · `aprovada` · `agendada` · `publicada` · `medida` · `descartada` |
| `slides[].midia` | `imagem` · `video` |
| `arquivos[].papel` | `final` · `slide` · `legenda` · `roteiro` · `audio` · `alinhamento` · `srt` · `avatar` · `tela` · `previa` · `fonte` |
| `conteudo.gancho_tipo` | `pergunta` · `contraste` · `numero` · `lista` · `historia` · `processo` · `polemica` · `outro` |
| `conteudo.cta_forma` | `comentario` · `salvar` · `compartilhar` · `link` · `seguir` · `dm` · `nenhum` |
| `publicacoes[].canal` | `instagram` · `facebook` · `youtube` · `tiktok` · `linkedin` · `meta_ads` |
| `publicacoes[].provedor` | `expxflow` · `meta_graph` · `youtube_api` · `manual` |
| `publicacoes[].estado` | `agendada` · `publicada` · `falhou` · `cancelada` |

`gancho_tipo` e `cta_forma` já existem no `geracoes.jsonl` dos carrosséis e são o que permite a
análise responder "que tipo de gancho funciona". Por isso entram no contrato.

### Carrossel misto

O carrossel de hoje é o caso em que todo slide é `imagem`. Um slide `video` tem `duracao_s`
preenchida e arquivo MP4 no mesmo formato dos outros slides. Nenhum outro campo muda.

O contrato assume que os provedores de publicação aceitam vídeo nos filhos do carrossel. Se um
deles não aceitar, é limitação do adaptador daquele provedor, a resolver lá — a peça não muda.

### Apresentação e aula

- **Apresentação** tem `slides` com `kind` do template (título, comparação, estatísticas,
  etapas…) e um arquivo `papel: final` que é o **HTML navegável**. PNG por slide e MP4 são
  arquivos extras, `papel: slide` e `papel: final`.
- **Aula** tem `slides: []` e usa `compoe` para apontar a apresentação que roda dentro dela,
  quando houver. Os arquivos típicos: `audio` (narração), `alinhamento`, `avatar`, `tela`
  (gravação de tela), `srt`, e um `final` por formato.

A mesma apresentação pode compor várias aulas e virar um vídeo do YouTube sem ser refeita.

### `metricas`

```json
"metricas": {
  "coletadas_em": "2026-09-26T05:00:00-03:00",
  "canal": "instagram",
  "horas_no_ar": 41,
  "valores": {
    "alcance": 1840,
    "impressoes": 2210,
    "curtidas": 96,
    "comentarios": 14,
    "compartilhamentos": 9,
    "salvos": 51,
    "visualizacoes": null,
    "retencao_3s": null
  }
}
```

Guarda **só a coleta mais recente**. O histórico de coletas vai para o rastro
(`metricas_coletadas`), onde a análise encontra a curva. As chaves de `valores` acima são
canônicas: todo pack de canal usa esses nomes para o que existir no canal, e `null` para o que
não existir. Métrica exclusiva de um canal (por exemplo `ctr_miniatura` no YouTube) entra como
chave extra **depois** das canônicas.

## Regras

1. **Um `peca.json` por peça**, gravado com escrita atômica (M15), reescrevendo `atualizado_em`
   (M10).
2. **Toda transição de `status` gera um evento** no rastro
   ([`CONTRATO-estado-eventos.md`](./CONTRATO-estado-eventos.md)).
3. **Nada de marca fixa na peça além do que veio da Alma** naquele momento (M13). A peça
   registra o que foi usado; não é fonte de marca para a próxima.
4. **A peça não guarda segredo** (M14): `id_externo` é o id do agendamento, nunca o token.
5. **Pack lê peça de outro pack** — só pelos campos deste contrato. Um pack de análise pode
   comparar reels e carrosséis sem conhecer os packs que os fizeram.
