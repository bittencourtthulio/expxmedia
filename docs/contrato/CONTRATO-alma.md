# Contrato `expxmedia-alma` v1

A Alma é quem a empresa é: identidade, público, ofertas, voz, visual, canais e as pessoas
que aparecem e falam por ela. **É a única fonte de marca do ecossistema** (regra M13): todo
pack lê daqui o que antes estava cravado no código.

Uma instalação, uma Alma. Quem atende vários clientes cria uma pasta por cliente e instala o
ExpxMedia em cada uma — é isso que garante que marca, chaves, peças e galeria local nunca se
misturem.

---

## O portão de primeiro uso

Nenhuma skill de nenhum pack produz nada sem Alma. A ordem é fixa:

```
qualquer skill
   │
   ├─ alma/alma.json não existe, ou "confirmada_em" é null ──► /expxmedia:alma
   │
   ├─ .env não existe ─────────────────────────────────────► /expxmedia:ambiente
   │                                                         (CONTRATO-capacidades.md)
   └─ segue
```

A verificação é feita em **duas camadas**, porque instrução em skill é esquecida:

1. **Hook do núcleo** (`UserPromptSubmit`), determinístico, que injeta no contexto a
   instrução de rodar o portão antes de qualquer ação. Falha aberta: erro no hook não
   bloqueia nada.
2. **Primeiro passo de toda skill** de pack: conferir o portão e, se faltar, parar e
   encaminhar. Está no contrato de pack ([`CONTRATO-pack.md`](./CONTRATO-pack.md)).

O portão da Alma é obrigatório. O do ambiente só exige que o `.env` **exista** — ele pode estar
vazio. Sem chave nenhuma o sistema já cria posts, carrosséis e apresentações em HTML.

## Como a Alma é criada

`/expxmedia:alma` oferece dois caminhos, que podem ser combinados:

| Caminho | Como | `metodo` |
|---|---|---|
| **Pelo site** | a pessoa informa a URL; o sistema lê a página inicial e as páginas de sobre, produtos/serviços, contato e blog, e extrai nome, descrição, público, ofertas, tom de voz, cores, fontes e logotipo | `site` |
| **Entrevista** | perguntas curtas, uma de cada vez, bloco a bloco | `entrevista` |
| Os dois | o site preenche o que dá; a entrevista pergunta só o que faltou | `misto` |

Ao terminar, o sistema mostra **a proposta inteira** num resumo legível e pede **uma
confirmação só**. Confirmada, grava `confirmada_em`. A pessoa edita os arquivos depois, quando
quiser; toda edição manual é tratada como `origem: humano`.

**O que a extração pelo site nunca faz:** inventar dado que não está lá. Campo sem evidência
fica `null` e entra na lista de pendências mostrada na confirmação. Tom de voz é sempre
`inferido` — nenhum site declara o próprio tom.

**Cores e logotipo:** a extração lê o logotipo (SVG ou imagem) e as cores dominantes da
identidade (CSS e o próprio logotipo), e as distribui nos papéis de cor abaixo. Quando o
logotipo não tem versão para fundo escuro, o campo `logo.negativo` fica `null` e vira pendência
— o sistema não fabrica uma.

## Onde fica

```
alma/
  alma.json            ← a máquina lê (M1)
  voz.md               ← guia de voz longo, para o modelo e para a pessoa
  publico.md           ← quem é o público, com as dores e desejos em prosa
  assets/
    logo.svg           ← principal
    logo-negativo.svg  ← para fundo escuro (opcional)
    simbolo.svg        ← só o ícone (opcional)
    retratos/<porta_voz>/*.jpg
```

A pasta `alma/` **é versionada**: nada nela é segredo. Um id de voz clonada não é segredo; a
chave da API que usa esse id é, e vive no `.env` (M14).

## `alma/alma.json`

```json
{
  "expxmedia_alma": 1,
  "metodo": "misto",
  "fontes": ["https://www.exemplo.com.br", "https://www.exemplo.com.br/sobre"],
  "criada_em": "2026-09-24T10:00:00-03:00",
  "confirmada_em": "2026-09-24T10:12:00-03:00",
  "atualizado_em": "2026-09-24T10:12:00-03:00",

  "empresa": {
    "nome": "Exemplo Contabilidade",
    "nome_curto": "Exemplo",
    "descricao_curta": "Contabilidade digital para pequenas empresas de serviço.",
    "segmento": "contabilidade",
    "site": "https://www.exemplo.com.br",
    "pais": "BR",
    "idioma": "pt-BR",
    "fuso": "America/Sao_Paulo"
  },

  "publico": {
    "principal": "donos de pequenas empresas de serviço, de 1 a 20 funcionários",
    "dores": ["não entende o próprio imposto", "medo de multa"],
    "desejos": ["pagar menos imposto dentro da lei", "tempo livre"]
  },

  "ofertas": [
    {
      "id": "consultoria-inicial",
      "nome": "Consultoria inicial",
      "tipo": "servico",
      "descricao": "Diagnóstico tributário em uma reunião.",
      "url": "https://www.exemplo.com.br/consultoria",
      "principal": true
    }
  ],

  "voz": {
    "tom": ["direto", "didático", "próximo"],
    "tratamento": "voce",
    "formalidade": "media",
    "palavras_preferidas": ["simples", "na prática"],
    "palavras_proibidas": ["garantido", "milagre"],
    "regras": ["frases curtas", "um número concreto por peça sempre que houver"],
    "exemplos_bons": ["Seu imposto não é caro. Ele está mal enquadrado."],
    "exemplos_ruins": ["Somos líderes em soluções contábeis inovadoras."]
  },

  "visual": {
    "cores": {
      "fundo": "#FFFFFF",
      "fundo_alt": "#F3F5F9",
      "texto": "#101828",
      "texto_inverso": "#FFFFFF",
      "apoio": "#667085",
      "destaque": "#1E5EFF",
      "destaque_2": "#00B386",
      "positivo": "#12B76A",
      "negativo": "#F04438"
    },
    "fontes": {
      "titulo": { "familia": "Inter Tight", "origem": "google" },
      "texto": { "familia": "Inter", "origem": "google" }
    },
    "logo": {
      "principal": "alma/assets/logo.svg",
      "negativo": null,
      "simbolo": null
    },
    "estilo": ["limpo", "tipografico", "claro"]
  },

  "cta": {
    "padrao": "Agende sua consultoria inicial",
    "destino": "https://www.exemplo.com.br/consultoria",
    "variacoes": ["Comente CONTA que eu te mando o checklist"]
  },

  "canais": [
    { "canal": "instagram", "identificador": "@exemplocontabil", "url": "https://instagram.com/exemplocontabil" },
    { "canal": "youtube", "identificador": "@exemplocontabil", "url": null }
  ],

  "porta_vozes": [
    {
      "id": "ana-souza",
      "nome": "Ana Souza",
      "papel": "sócia fundadora",
      "principal": true,
      "consentimento_imagem_voz": true,
      "voz": { "provedor": "elevenlabs", "voz_id": "abc123" },
      "avatar": { "provedor": "heygen", "avatar_id": null },
      "rosto_ia": { "provedor": "higgsfield", "id": null },
      "retratos": ["alma/assets/retratos/ana-souza/01.jpg"]
    }
  ],

  "restricoes": {
    "temas_proibidos": ["política partidária"],
    "promessas_proibidas": ["resultado financeiro garantido"],
    "observacoes_legais": ["peça sobre imposto cita o ano-base"]
  },

  "origens": {
    "empresa.nome": "site",
    "empresa.descricao_curta": "site",
    "publico.principal": "inferido",
    "voz.tom": "inferido",
    "visual.cores": "site",
    "cta.padrao": "entrevista",
    "porta_vozes": "entrevista"
  },

  "pendencias": ["visual.logo.negativo", "canais.youtube.url"]
}
```

### Enums

| Campo | Valores |
|---|---|
| `metodo` | `site` · `entrevista` · `misto` |
| `origens.*` | `site` · `entrevista` · `inferido` · `humano` |
| `ofertas[].tipo` | `produto` · `servico` · `curso` · `evento` · `assinatura` · `outro` |
| `voz.tratamento` | `voce` · `tu` · `nos` · `impessoal` |
| `voz.formalidade` | `baixa` · `media` · `alta` |
| `visual.fontes.*.origem` | `google` · `local` |
| `canais[].canal` | `instagram` · `facebook` · `youtube` · `tiktok` · `linkedin` · `x` · `site` · `outro` |

### Os papéis de cor

Os nove papéis de `visual.cores` são **o vocabulário que todo template usa** (ver
[`CONTRATO-template.md`](./CONTRATO-template.md)). Um template nunca pede "o azul"; ele pede
`destaque`. É isso que permite a mesma peça servir a qualquer empresa.

| Papel | Uso |
|---|---|
| `fundo` / `fundo_alt` | superfície principal e a alternada |
| `texto` / `texto_inverso` | texto sobre `fundo` e sobre cor escura ou `destaque` |
| `apoio` | texto secundário, rótulos, miúdo |
| `destaque` / `destaque_2` | a cor da marca e a segunda cor |
| `positivo` / `negativo` | dado bom e dado ruim (gráfico, antes/depois) |

### `origens`

Mapa de **caminho do campo → de onde veio**. Não precisa listar todo campo: o que não está no
mapa é `humano`. Serve para a pessoa saber o que vale revisar — `inferido` é palpite.

### `porta_vozes`

As pessoas que aparecem e falam pela empresa. Uma empresa sem ninguém que apareça tem a
lista vazia, e todo template que exige rosto ou voz fica fora do alcance (é um requisito de
capacidade, ver [`CONTRATO-capacidades.md`](./CONTRATO-capacidades.md)).

`consentimento_imagem_voz` é obrigatório e começa `false`. Nenhuma capacidade que usa voz
clonada, avatar ou rosto gerado roda para um porta-voz com `false`. Os ids de voz, avatar e
rosto são referências ao provedor, não segredo.

## Regras

1. **A Alma é a única fonte de marca** (M13). Pack que precisa de um dado de marca que não
   está aqui propõe um campo novo para este contrato; não cria arquivo próprio.
2. **Nunca sai da instalação.** Nada da Alma sobe para a galeria compartilhada
   ([`CONTRATO-template.md`](./CONTRATO-template.md)).
3. **Campo sem evidência é `null`**, e o caminho dele vai para `pendencias`.
4. **Editar a Alma não invalida peça já produzida.** Peça registra o que usou no momento em que
   foi feita.
