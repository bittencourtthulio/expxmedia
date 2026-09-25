# Convenções do ExpxMedia — documento raiz

As regras abaixo valem para **todo** artefato do ecossistema ExpxMedia: `alma.json`,
`peca.json`, `template.json`, `pack.json`, linha de rastro, plano do dia, relatório.

Os contratos derivados **não repetem estas regras**. Eles as citam pelo número com
prefixo: "regra M3", "regra M13". Quem precisar mudar uma convenção muda aqui, uma vez.

O prefixo é `M` (de Media) para nunca colidir com as regras `R` do expxdev, que um
mesmo desenvolvedor pode ter aberto no editor ao lado.

---

## Onde cada domínio é definido

| Domínio | Documento | O que define |
|---|---|---|
| Convenções | **este arquivo** | M1–M16, válidas em todo lugar |
| Alma da empresa | [`CONTRATO-alma.md`](./CONTRATO-alma.md) | identidade, voz, visual, porta-vozes, e o portão de primeiro uso |
| Capacidades e ambiente | [`CONTRATO-capacidades.md`](./CONTRATO-capacidades.md) | o que o sistema sabe fazer, quem faz, que chave do `.env` habilita |
| Peça | [`CONTRATO-peca.md`](./CONTRATO-peca.md) | todo conteúdo produzido, dos cinco tipos, e seu ciclo de vida |
| Template e galeria | [`CONTRATO-template.md`](./CONTRATO-template.md) | o manifesto do template, a galeria local e a compartilhada |
| Estado e eventos | [`CONTRATO-estado-eventos.md`](./CONTRATO-estado-eventos.md) | daily, decisões, rastro, plano do dia, relatórios |
| Pack | [`CONTRATO-pack.md`](./CONTRATO-pack.md) | o que um pack ou camada declara ao ser instalado |

---

## As convenções

### M1 — JSON é o formato da máquina; Markdown é o formato da pessoa e do modelo

Todo arquivo que um programa lê é JSON (`.json`) ou JSON por linha (`.jsonl`). Todo
texto longo, que uma pessoa ou o modelo lê para escrever melhor, é Markdown.

Nenhum programa extrai informação de Markdown. Se o painel precisa de um dado, ele está
num JSON.

### M2 — A chave de versão vem primeiro

Todo JSON de contrato abre com a chave que diz qual contrato ele segue e em que versão:
`"expxmedia_alma": 1`, `"expxmedia_peca": 1`, `"expxmedia_template": 1`,
`"expxmedia_pack": 1`, `"expxmedia_plano": 1`, `"expxmedia_eventos": 1`.

Leitor que encontra versão maior que a que conhece **rejeita** o arquivo e diz por quê.
Não tenta ler "o que der".

### M3 — Chave em `snake_case`, minúscula, sem acento

`agendada_para`, nunca `agendadaPara` nem `agendada-para`.

Exceção única: variáveis do `.env`, que seguem a convenção universal de ambiente —
`MAIUSCULA_COM_SUBLINHADO` (M12).

### M4 — Valor de enum minúsculo, sem acento

`publicada`, nunca `Publicada`. `post_unico`, nunca `post único`.

Texto livre (`titulo`, `detalhe`, `descricao`) é prosa em português e leva acento.

### M5 — Datas e horários

- Data simples: `AAAA-MM-DD`.
- Momento: ISO 8601 **com deslocamento de fuso**: `2026-09-24T21:22:46-03:00`.

Diferente do expxdev, que usa UTC: aqui o horário importa para gente — "publicar às
07:00" é 07:00 no fuso da empresa (`empresa.fuso` da Alma), não em UTC. O deslocamento é
obrigatório justamente para o horário nunca ser ambíguo.

**Obtenha a data do sistema, nunca de memória:**

```sh
date +%Y-%m-%d
date +%Y-%m-%dT%H:%M:%S%z | sed 's/\(..\)$/:\1/'
```

### M6 — Booleanos `true` / `false`

Nunca `"true"`, `"sim"`, `1`.

### M7 — Chave nunca omitida

Lista vazia é `[]`. Ausente é `null`. **A chave está sempre lá.**

Chave obrigatória ausente é **violação** (o arquivo é lido e aparece no painel com o
defeito à vista), não **rejeição** (o arquivo some do painel). Rejeição é só para o que
não dá para ler: JSON inválido, chave de versão ausente ou maior que a suportada (M2).

Leitor não preenche valor padrão em silêncio.

### M8 — Ausente é `null`, e só

Nunca `"n/a"`, `"-"`, `""` ou `"nenhum"` em JSON.

### M9 — Nenhum caminho absoluto

Caminho é sempre relativo à raiz da instalação: `pecas/2026-09/P-20260924-A3F9-gancho/final.mp4`.
Caminho absoluto vaza o usuário da máquina e quebra ao trocar de máquina.

### M10 — `atualizado_em` a cada gravação

Todo JSON com estado carrega `atualizado_em` e o reescreve sempre que é gravado.

### M11 — Ids

| Artefato | Formato | Exemplo |
|---|---|---|
| Peça | `P-AAAAMMDD-XXXX` (XXXX = 4 hex maiúsculos aleatórios) | `P-20260924-A3F9` |
| Template | `<tipo>-<slug>-<hash6>` | `carrossel-editorial-azul-3fa2c1` |
| Vaga do plano | `v<N>` dentro do dia | `v3` |
| Item da daily | `d<NNN>` | `d016` |
| Decisão | `D-<NNN>` | `D-042` |
| Porta-voz | slug | `ana-souza` |
| Oferta | slug | `consultoria-inicial` |

O id da peça é aleatório, não sequencial, de propósito: vários packs criam peças ao mesmo
tempo, e contador sequencial exige trava entre processos que ninguém quer manter.

### M12 — Variáveis de ambiente

Todo segredo e toda escolha de provedor vivem no `.env` da raiz da instalação, em
`MAIUSCULA_COM_SUBLINHADO`. O catálogo de nomes está em
[`CONTRATO-capacidades.md`](./CONTRATO-capacidades.md). Nenhum pack inventa nome de
variável fora do catálogo.

### M13 — Nada de marca no código

**A regra que torna o produto vendável.** Nenhum pack, skill, agente, hook, template ou
linha de código carrega nome, cor, voz, rosto, conta, domínio, CTA ou público de uma
empresa específica. Tudo isso vem da Alma (`alma/alma.json`) ou do `.env`.

Teste prático: instalar o pack numa pasta com outra Alma tem de produzir peças da outra
empresa sem mudar um byte do pack.

Exemplo de violação: `"cta": "expxplay.com.br"` num script; `VOICE_ID = "a1b2c3..."` num
módulo; `"Thulio"` num prompt de agente; `#22C55E` num tema de Remotion.

### M14 — Segredo só no `.env`

Nenhum valor de chave aparece em JSON de contrato, em Markdown, em linha de rastro, em
`detalhe` de evento, em log ou em mensagem de erro. Mensagem de erro cita o **nome** da
variável (`ELEVENLABS_API_KEY`), nunca o valor.

O `.env` é ignorado pelo versionador desde a instalação. O `.env.example` (sem valores) é
versionado.

### M15 — Escrita atômica e rastro com trava

- JSON: grava em arquivo temporário **na mesma pasta** e troca por `rename`. O painel pode
  estar lendo no mesmo instante, e JSON pela metade quebra a leitura.
- JSONL: acrescenta uma linha inteira por vez, com trava de arquivo. Ninguém reescreve
  linha antiga.

### M16 — Idioma e encoding

Prosa em português do Brasil, com acento. Identificador (chave, enum, nome de arquivo,
nome de agente, nome de skill) em português sem acento. UTF-8 sem BOM; leitores toleram BOM
na entrada.

---

## Como citar

```python
# Chave nunca omitida (M7): None vira null.
```

Não reescreva o texto da regra no ponto de uso. Resumo em prosa vira segunda fonte, e
segunda fonte envelhece.

## Histórico

| Data | Mudança |
|---|---|
| 2026-09-24 | Documento criado, adaptando as convenções R1–R14 do expxdev ao domínio de mídia: JSON em vez de frontmatter (M1), horário com fuso em vez de UTC (M5), e duas regras novas — nada de marca no código (M13) e segredo só no `.env` (M14). |
