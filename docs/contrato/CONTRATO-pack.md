# Contrato `expxmedia-pack` v1

Um **pack** é um conjunto instalável que dá ao ExpxMedia uma especialidade — Instagram, YouTube,
anúncios Meta, cursos. Uma **camada** é um pack que sozinho não produz nada: ela muda o
comportamento dos outros quando está presente (a galeria é a primeira).

Como no expxdev, cada pack mora no **próprio repositório**, e a central (`expxmedia`) busca os
escolhidos, trava versão e hash no lock, e monta **um plugin do Claude Code chamado `expxmedia`**
com tudo junto. Os comandos ficam com namespace: `/expxmedia:instagram-carrossel`.

Os packs não se conhecem por código. Eles se encontram nos contratos: um lê a `peca.json` que o
outro gravou, e nenhum importa módulo de outro.

---

## Os packs e camadas previstos

| Nome | Tipo | Origem na extração | Produz |
|---|---|---|---|
| `expx-instagram` | pack | `Instagram-Carrosseis` + `Instragram-Videos` | `post_unico`, `carrossel`, `reel` |
| `expx-youtube` | pack | `youtube-squad` | `apresentacao`, análise do canal |
| `expx-meta` | pack | `ExpxMeta` | campanhas; usa peças de outros packs como criativo |
| `expx-cursos` | pack | `cursos-ia` | `aula`, `apresentacao` |
| `expx-galeria` | camada | `Instagram-Carrosseis/galeria` | nada — dá templates aos outros |

## O que vai no plugin montado

```
.expxmedia/marketplace/plugins/expxmedia/
  .claude-plugin/plugin.json
  skills/<skill>/                 de cada pack instalado
  agents/<agente>.md              de cada pack instalado
  commands/<comando>.md           de cada pack instalado + os do núcleo
  hooks/                          os do núcleo + os de cada pack
  nucleo/                         vem sempre, de qualquer seleção:
    commands/alma.md              /expxmedia:alma
    commands/ambiente.md          /expxmedia:ambiente
    commands/onboarding.md        /expxmedia:onboarding
    hooks/expxmedia-portao.sh     o portão de primeiro uso (CONTRATO-alma.md)
    hooks/expxmedia-segredo.sh    bloqueia leitura e escrita de .env e tokens
    hooks/expxmedia-rastro.sh     implementação única do rastro (fonte, não executável)
```

## `pack.json`

Na raiz do repositório do pack.

```json
{
  "expxmedia_pack": 1,
  "nome": "expx-instagram",
  "versao": "1.0.0",
  "tipo": "pack",
  "descricao": "Posts, carrosséis e reels para Instagram",
  "contratos": { "alma": 1, "peca": 1, "template": 1, "estado": 1, "capacidades": 1 },
  "motor_min": "1.0.0",

  "produz": ["post_unico", "carrossel", "reel"],
  "canais": ["instagram", "facebook"],

  "capacidades": {
    "obrigatorias": ["renderizar_html"],
    "opcionais": ["renderizar_motion", "narrar", "legendar", "avatar", "rosto_ia", "video_ia",
                  "banco_imagens", "imagem_ia", "publicar", "agendar", "automacao_dm",
                  "metricas_instagram"]
  },

  "skills": ["instagram-carrossel", "instagram-post", "instagram-reel", "instagram-analisar"],
  "agentes": ["copywriter", "revisor-editorial", "geradores", "publicacao", "analista"],
  "comandos": ["instagram-carrossel", "instagram-reel", "instagram-planejar-dia"],
  "hooks": [
    { "nome": "escopo-geradores", "evento": "PreToolUse", "tipo": "metodo", "modo_inicial": "aviso" }
  ],

  "painel": {
    "abas": [
      { "id": "instagram", "titulo": "Instagram", "entrada": "painel/index.html", "api": "painel/api.py" }
    ]
  },

  "editorial": ["editorial/cadencia.json", "editorial/ganchos.md", "editorial/aprendizados.md"],

  "rotinas": [
    { "id": "planejar-dia", "comando": "/expxmedia:instagram-planejar-dia", "cron": "0 4 * * *" }
  ],

  "requisitos_sistema": {
    "binarios": ["ffmpeg"],
    "python": "requirements.txt",
    "node": null
  }
}
```

### Campos

| Campo | O que é |
|---|---|
| `tipo` | `pack` · `camada` |
| `contratos` | a versão de cada contrato que o pack **escreve e lê**. A central recusa instalar pack que exija versão maior que a do motor instalado |
| `capacidades.obrigatorias` | sem elas o pack não instala — o `doctor` explica o que falta. Deve ser o mínimo: só capacidades sem chave |
| `capacidades.opcionais` | o pack funciona sem elas, com menos recursos. **São as variáveis destas que entram no `.env.example`** |
| `painel.abas` | ver abaixo |
| `editorial` | arquivos que a pessoa ajusta para o pack (cadência, ganchos, aprendizados). São **copiados para a instalação** na primeira vez e nunca sobrescritos por atualização |
| `rotinas` | trabalho agendado. A central não instala cron sozinha: `/expxmedia:onboarding` mostra as rotinas e pede confirmação |

## As abas do painel

O painel é um só, da central: servidor local em `127.0.0.1`, com a casca comum (Início, Daily,
Reunião, Decisões, Peças, Agenda, Galeria, Ambiente). **Cada pack instalado acrescenta abas.**

| | O que o pack entrega | Regras |
|---|---|---|
| `entrada` | HTML/JS/CSS estático, sem build | carregado dentro da casca; usa o CSS de tokens da casca, para todas as abas terem a mesma cara |
| `api` | módulo Python opcional que registra rotas em `/api/<pack>/…` | **só lê** arquivos dos contratos; qualquer escrita passa pela API da casca (daily, chat) ou dispara um comando do pack. Nunca chama provedor externo |

As abas comuns da casca já leem `peca.json`, plano e relatórios de **todos** os packs. A aba do
pack existe para o que é só dele (o mock do feed do Instagram, o escritório do YouTube, o placar de
campanhas da Meta), não para repetir o que a casca mostra.

## Regras para skills de pack

Toda skill de pack que produz, publica ou planeja segue esta abertura, nesta ordem:

1. **Portão.** Conferir Alma confirmada e `.env` existente ([`CONTRATO-alma.md`](./CONTRATO-alma.md)).
   Faltando, parar e encaminhar para `/expxmedia:alma` ou `/expxmedia:ambiente`.
2. **Ler a Alma** — nunca usar dado de marca de outro lugar (M13).
3. **Consultar a galeria**, se a camada `expx-galeria` estiver instalada
   ([`CONTRATO-template.md`](./CONTRATO-template.md)).
4. **Conferir requisitos** da peça. Faltando, parar e mostrar `como_habilitar`
   ([`CONTRATO-capacidades.md`](./CONTRATO-capacidades.md)).
5. **Registrar a peça** (`peca.json`) antes de gerar qualquer arquivo, e cada transição depois
   ([`CONTRATO-peca.md`](./CONTRATO-peca.md)).

E durante o trabalho:

- **Pedir capacidade ao motor, nunca chamar provedor direto.** Pack que importa o SDK da
  ElevenLabs viola o contrato: a troca de provedor deixaria de ser configuração.
- **Escrever eventos** pelo `expxmedia-rastro` do núcleo, nunca por implementação própria — no
  expxdev, quatro implementações do rastro divergiram em produção.
- **A ausência nunca quebra.** Sem galeria, sem uma capacidade opcional, sem outro pack: aviso do
  que falta, nunca erro que trava o trabalho.

## Regras para agentes e hooks

Herdadas do padrão que os projetos de origem já usam, e do contrato de eventos do expxdev:

1. **Todo agente declara `tools`.** Agente sem declaração herda todas as ferramentas.
2. **Agente de revisão tem só leitura.** "Aponta, não corrige" vira impossibilidade técnica.
3. **Hook de escopo por agente**: cada agente escreve só nas pastas do seu papel (o gerador escreve
   em `pecas/`, o analista em `relatorios/`, ninguém escreve em `alma/` exceto `/expxmedia:alma`).
4. **Hook de método nasce em `aviso`**; só a pessoa promove para `bloqueio`, em
   `.expxmedia/hooks.json`. **Hook de segurança nasce em `bloqueio`** e falha fechado.
5. **Os hooks são registrados de verdade.** Hook declarado no frontmatter e ausente do
   `settings.json` não roda — é o que acontece hoje no `ExpxMeta`. A central garante o registro ao
   montar o plugin, e o `doctor` confere.

## Regras para a camada

Uma camada:

- não tem `produz` (lista vazia);
- é detectada pelos packs **pela presença do artefato dela** (para a galeria:
  `galeria/templates/` existir), nunca por import;
- quando ausente, os packs se comportam exatamente como sem ela.

## Na instalação (visão da central)

A central, ao instalar ou atualizar um pack:

1. confere `contratos` e `motor_min` contra o motor instalado; incompatível não entra;
2. confere `requisitos_sistema` e `capacidades.obrigatorias`; faltando, instala mesmo assim e o
   `doctor` explica — como no expxdev, um pack que falha não derruba os outros;
3. copia `editorial` para a instalação **só se ainda não existir**;
4. regenera o `.env.example` com as variáveis das capacidades opcionais de todos os packs
   instalados — **sem tocar no `.env`**;
5. monta o plugin, registra os hooks no `settings.json` (com backup) e grava o lock com o hash de
   cada arquivo.
