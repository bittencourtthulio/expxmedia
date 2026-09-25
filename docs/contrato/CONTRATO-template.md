# Contrato `expxmedia-template` v1 — template e galeria

Um **template** é a estrutura reutilizável de uma peça: layout, slots de texto com limite,
tipos de slide ou cena, requisitos de capacidade e assets. Ele **não tem marca**: cores,
fontes, logotipo e rosto vêm da Alma de quem usa, na hora de renderizar.

A **galeria** é onde os templates moram. Existem duas:

| | Galeria local | Galeria compartilhada |
|---|---|---|
| Onde | `galeria/` na instalação | repositório público `expxmedia-gallery` no GitHub |
| Quem vê | só esta instalação | todo mundo |
| O que tem | templates criados aqui + os baixados da compartilhada | os templates de todas as instalações que usam a galeria |
| Como entra | criado pelo pack ou pela camada galeria | **envio automático** de toda instalação com a galeria ativa |

A camada galeria é opcional (ver [`CONTRATO-pack.md`](./CONTRATO-pack.md)). Sem ela, cada pack
usa os próprios templates e nada sai da máquina.

---

## Tipos e motores

Os tipos são os mesmos da peça ([`CONTRATO-peca.md`](./CONTRATO-peca.md)).

| `tipo` | `motor` | O que o template traz |
|---|---|---|
| `post_unico`, `carrossel` | `html` | um HTML por `kind` de slide + um CSS |
| `carrossel` misto | `html` + `remotion` | slides HTML e slides de vídeo com o código Remotion deles |
| `reel`, `apresentacao`, `aula` | `remotion` | o código Remotion (TSX) da composição, parametrizado por slots |
| `apresentacao` | `html` também | slides HTML navegáveis, sem vídeo |

### Template de vídeo leva código: a garantia de fidelidade

**Quem usa um template de vídeo recebe um vídeo igual ao original** — mesmo layout, mesma
animação, mesmo ritmo, mesmas transições. Só muda o que é da empresa: cores, fontes, logotipo,
textos, voz e rosto.

A única forma de garantir isso é o template levar **o próprio código** da composição. Uma
descrição declarativa sobre uma biblioteca de cenas do motor só reproduz o que essa biblioteca
já sabe desenhar; qualquer visual novo sairia parecido, não igual. Por isso o motor de vídeo de
template é `remotion`, com o TSX dentro do template, e o envio para a galeria compartilhada
**inclui o código** — coberto pelo aceite da galeria (ver "O aceite").

A fidelidade depende de três coisas travadas no `template.json`:

| Trava | Por quê |
|---|---|
| `versoes.remotion` | a mesma composição renderiza diferente entre versões do Remotion |
| `versoes.motor` | as funções de injeção de Alma (cores, fontes, logo) e de alinhamento de legenda são do motor |
| `dependencias` | toda biblioteca que o código importa, com versão exata |

O motor instala a versão pedida do Remotion por template (cache compartilhado entre templates
que pedem a mesma), em vez de renderizar tudo numa versão só.

### O que o código de template pode e não pode fazer

Código de terceiro vai rodar na máquina de quem baixa. As regras abaixo são verificadas na
validação local e de novo na CI do repositório, e código que viola qualquer uma não entra:

1. **Imports só da lista permitida:** `react`, `remotion`, `@remotion/*` e o módulo de apoio do
   motor (`@expxmedia/template`, que entrega Alma, slots e alinhamento de legenda). Qualquer outro
   pacote precisa estar em `dependencias` **e** na lista permitida da galeria.
2. **Proibido:** `fs`, `child_process`, `net`, `http`, `https`, `fetch`, `XMLHttpRequest`,
   `WebSocket`, `eval`, `new Function`, `process`, `require` dinâmico, `import()` dinâmico.
3. **Sem rede:** asset só do próprio template ou entregue pelo motor; fonte só pelo motor.
4. **Tudo que é da empresa entra por props:** cor, fonte e logo vêm de `useAlma()`, texto vem dos
   slots. Cor literal fora do tema, texto fixo e caminho de asset fixo são violação (M13).
5. **O render roda isolado:** processo separado, sem rede, com leitura só da pasta do template e
   escrita só da pasta de saída da peça.

A verificação estática reduz muito o risco, mas não o zera: um código malicioso bem escondido
pode escapar de uma análise de texto. O isolamento do passo 5 é a segunda barreira, e é por ele
existir que a primeira pode ser automática.

## Onde fica

```
galeria/
  templates/
    carrossel-editorial-azul-3fa2c1/
      template.json
      template.css            (motor html)
      slides/<kind>.html      (motor html)
      src/                    (motor remotion) Composicao.tsx, cenas/*.tsx
      package.json            (motor remotion) dependências com versão exata
      assets/                 neutros + os marcados como marca/pessoa (ver abaixo)
      previa/                 prancha.png, slide_1.png… (a prévia local, com a Alma)
      exemplo.json            conteúdo de exemplo — LOCAL, com a voz da empresa
      referencia/             imagens de inspiração — LOCAL, NUNCA sobe
  compartilhada/              cópia local da galeria pública (ignorada pelo versionador)
```

## `template.json`

Evolução direta do `layout.json` da galeria dos carrosséis: slots com limite, canvas, `kinds` e
validação continuam iguais. O que muda está marcado na lista depois do exemplo.

```json
{
  "expxmedia_template": 1,
  "template_id": "carrossel-editorial-azul-3fa2c1",
  "titulo": "Editorial com número gigante",
  "tipo": "carrossel",
  "motor": "html",
  "formato": "4:5",
  "canvas": { "w": 1080, "h": 1350 },
  "status": "validado",
  "criado_em": "2026-09-24T09:00:00-03:00",
  "atualizado_em": "2026-09-24T09:30:00-03:00",

  "estilos": ["tipografico", "dados", "claro"],
  "serve_para": ["numero-e-dado", "conceito", "citacao"],

  "versoes": { "motor": "1.0.0", "remotion": null },
  "dependencias": {},

  "requisitos": ["renderizar_html"],
  "exige_porta_voz": false,

  "tokens": ["fundo", "fundo_alt", "texto", "texto_inverso", "apoio", "destaque", "positivo"],
  "fontes": ["titulo", "texto"],

  "sequencia": ["capa", "numero", "frase", "cta"],
  "kinds": {
    "numero": {
      "midia": "imagem",
      "duracao_s": null,
      "fit": "fixo",
      "requisitos": [],
      "slots": {
        "etiqueta": { "tipo": "texto", "max": 24, "obrigatorio": false, "nota": "o assunto em uma ou duas palavras" },
        "numero":   { "tipo": "texto", "max": 4,  "obrigatorio": true,  "nota": "com sinal ou unidade curta: 12, 5M+, 8h" },
        "texto":    { "tipo": "texto", "max": 120, "obrigatorio": true, "nota": "o que o número conta, 3 linhas" },
        "logo":     { "tipo": "asset", "asset": "logo", "obrigatorio": false }
      }
    }
  },

  "assets": [
    { "id": "logo",   "arquivo": "assets/logo.svg",      "classe": "marca",  "substituir_por": "alma.visual.logo.principal" },
    { "id": "rosto",  "arquivo": "assets/retrato.jpg",   "classe": "pessoa", "substituir_por": "alma.porta_voz.retrato" },
    { "id": "malha",  "arquivo": "assets/malha.svg",     "classe": "neutro", "substituir_por": null }
  ],

  "validacao": {
    "contraste_min": 3.0,
    "fonte_min_px": 28,
    "resultado": "aprovado",
    "validado_em": "2026-09-24T09:30:00-03:00",
    "achados": []
  },

  "origem": {
    "tipo": "criado",
    "id_compartilhado": null,
    "inspiracao": null
  },

  "compartilhamento": {
    "estado": "enviado",
    "enviado_em": "2026-09-24T09:31:00-03:00",
    "pr_url": "https://github.com/<org>/expxmedia-gallery/pull/412",
    "erro": null
  }
}
```

O que muda em relação ao `layout.json` atual:

- **`tokens` em vez de `variaveis` e `temas`.** O template declara quais papéis de cor da Alma
  usa; não carrega paleta própria. `temas: ["referencia"]` deixa de existir.
- **`fontes` são papéis** (`titulo`, `texto`), não famílias. `fontes_google` sai.
- **`requisitos`** no template e em cada `kind`. O requisito efetivo é a união dos dois — um
  carrossel misto com um slide de vídeo narrado exige `narrar` só por causa daquele slide.
- **`assets` classificados** (ver abaixo).
- **`origem`** não guarda mais autor, URL nem métricas de terceiros. `inspiracao` é texto livre
  local e nunca sobe.
- **`compartilhamento`**, novo.

### O CSS usa só tokens

```css
:root {
  --cor-fundo: var(--alma-fundo);
  --cor-destaque: var(--alma-destaque);
  --fonte-titulo: var(--alma-fonte-titulo);
  /* derivadas são permitidas: */
  --cor-destaque-suave: color-mix(in srgb, var(--alma-destaque) 20%, var(--alma-fundo));
}
```

O motor injeta `--alma-<papel>` para cada papel de cor e `--alma-fonte-titulo`/`--alma-fonte-texto`
a partir da Alma. **Cor literal fora de `:root` é violação** de validação — é assim que a cor de
quem criou o template vazaria para todo mundo. Preto, branco e `transparent` são permitidos,
porque não identificam marca.

### Regras de renderização (motor `html`)

Herdadas da galeria dos carrosséis, e agora obrigatórias porque o template pode vir de terceiros:

1. A página renderiza **com JavaScript desligado**.
2. **Sem rede**, exceto Google Fonts. URL externa em `src`, `url()` ou `@import` é violação.
3. O texto é encaixado pelo motor dentro do `max` do slot; texto que não cabe é achado de
   validação, não corte silencioso.

### Enums

| Campo | Valores |
|---|---|
| `tipo` | os de peça: `post_unico` · `carrossel` · `reel` · `apresentacao` · `aula` |
| `motor` | `html` · `remotion` · `html_remotion` (carrossel misto) |
| `status` | `rascunho` · `validado` · `reprovado` · `fora` |
| `kinds.*.midia` | `imagem` · `video` |
| `slots.*.tipo` | `texto` · `lista` · `asset` · `numero` |
| `assets[].classe` | `marca` · `pessoa` · `neutro` |
| `origem.tipo` | `criado` · `derivado` · `baixado` · `externo` |
| `compartilhamento.estado` | `nao_enviado` · `enviado` · `aceito` · `recusado` · `erro` |

## Assets: o que é identidade

Todo asset do template é classificado **no momento em que o template é criado**:

| `classe` | Exemplo | Ao subir | Ao baixar |
|---|---|---|---|
| `marca` | logotipo, selo, mascote, ícone próprio | trocado pelo genérico da galeria (`genericos/logo.svg`) | trocado pelo da Alma (`substituir_por`) |
| `pessoa` | foto do porta-voz | trocado pelo retrato genérico (`genericos/retrato.png`) | trocado pelo retrato do porta-voz da peça |
| `neutro` | malha de pontos, textura, ícone de biblioteca livre | sobe como está | usado como está |

**Asset sem classificação é tratado como `marca`** e substituído. Na dúvida, não vaza.

Asset `neutro` precisa ser de uso livre. Foto de banco com licença que não permite redistribuição
(inclusive do Pexels) **não** é `neutro`: vira slot `asset` preenchido na hora pela capacidade
`banco_imagens`.

## A galeria compartilhada

### O repositório

```
expxmedia-gallery/                 (GitHub, público)
  LICENSE                          CC0-1.0
  genericos/
    logo.svg  logo-negativo.svg  simbolo.svg  retrato.png
  templates/
    <tipo>/<template_id>/
      template.json  template.css  slides/  src/  package.json  assets/  previa/  exemplo.json
  indice.json                      gerado pela CI a cada merge; é o que a busca lê
  .github/workflows/validar.yml
```

### O aceite

Usar a galeria compartilhada **é** concordar em contribuir. Ao instalar a camada galeria, a
pessoa vê o termo uma vez e aceita:

- todo template **novo** criado nesta instalação sobe automaticamente, sem pergunta;
- sobe sob **CC0-1.0**: qualquer pessoa pode usar para qualquer fim;
- **inclui o código** do template (HTML, CSS e o TSX dos templates de vídeo), também sob CC0-1.0;
- o que sobe é estrutura e código (lista abaixo); nada da Alma, nenhum conteúdo, nenhuma imagem
  de referência.

Sem aceite, não há galeria compartilhada — nem para baixar. O aceite fica em
`.expxmedia/galeria.json`:

```json
{
  "expxmedia_galeria": 1,
  "aceite": true,
  "aceito_em": "2026-09-24T10:20:00-03:00",
  "licenca": "CC0-1.0",
  "repositorio": "https://github.com/<org>/expxmedia-gallery"
}
```

A capacidade `galeria_compartilhada` exige aceite **e** login do `gh`. Sem eles, a galeria local
continua funcionando normalmente.

### O que sobe, e o que nunca sobe

| Sobe | Nunca sobe |
|---|---|
| `template.json` (sem `origem.inspiracao`, sem `compartilhamento`) | qualquer coisa de `alma/` |
| `template.css`, `slides/*.html`, `src/`, `package.json` | `exemplo.json` local (tem a voz e o conteúdo da empresa) |
| assets `neutro` | assets `marca` e `pessoa` originais |
| **prévia genérica**, gerada no envio | a prévia local (tem cor, logo e texto da empresa) |
| **exemplo genérico**, gerado no envio | `referencia/` — imagens de inspiração, quase sempre de terceiros |

### O envio automático, passo a passo

Dispara quando um template passa para `status: validado` pela primeira vez.

1. **Sanitiza** numa pasta temporária: remove o que nunca sobe; troca assets `marca` e `pessoa`
   pelos genéricos.
2. **Gera o exemplo genérico**: todo slot de texto recebe texto de preenchimento (lorem ipsum)
   com o **mesmo comprimento** do `max` do slot, para a prévia mostrar a ocupação real.
3. **Renderiza a prévia genérica** com a paleta neutra da galeria (tons de cinza com um azul de
   destaque neutro) e as fontes padrão do motor.
4. **Valida de novo** sobre o resultado sanitizado: contraste, fonte mínima, cor literal fora de
   `:root`, URL externa, as regras de código de template de vídeo, e ausência de qualquer string
   da Alma (nome, site, arroba, CTA) em qualquer arquivo, inclusive no código. Qualquer achado interrompe o envio, registra `compartilhamento.estado:
   erro` e o motivo — o template continua válido localmente.
5. **Abre o pull request** pelo `gh`, a partir de um fork da conta da pessoa, com
   `template_id` no título.
6. **A CI do repositório** repete a validação do passo 4 e verifica que o `template_id` é
   inédito. Passou: faz merge automático e atualiza `indice.json`. Não passou: fecha o PR com o
   motivo, e a próxima sincronização grava `recusado` no template local.

Nenhum passo pergunta nada à pessoa. Falha de envio nunca bloqueia a produção da peça.

**Template baixado (`origem.tipo: baixado`) não sobe de novo.** Template derivado de um baixado
(`derivado`) sobe como template novo, com `origem.id_compartilhado` apontando o original.
Template `externo` (decomposto de uma referência) sobe como qualquer outro — só a pasta
`referencia/`, que nunca sobe, fica para trás.

### A busca

Quando a camada galeria está instalada, **toda skill que vai criar uma peça consulta a galeria
antes**, nesta ordem:

1. filtra por `tipo` e `formato`;
2. **descarta todo template com requisito não habilitado** (união de `requisitos` do template e
   dos `kinds` que serão usados) — ele nem é cogitado;
3. descarta `exige_porta_voz: true` se a Alma não tem porta-voz;
4. ordena por aderência a `serve_para` e `estilos` ao pedido, depois pelo desempenho local
   (métricas das peças desta instalação que usaram o template);
5. usa a galeria local primeiro; a compartilhada completa o que faltar.

Um template da compartilhada escolhido é **baixado** para `galeria/templates/` e passa a ser local.

Se a pessoa pedir **explicitamente** um template cujo requisito falta, a skill não o descarta em
silêncio: responde com `como_habilitar` da capacidade
([`CONTRATO-capacidades.md`](./CONTRATO-capacidades.md)).

## Migração da galeria atual

Os layouts em `Instagram-Carrosseis/galeria/layouts/` foram decompostos de referências (Behance,
com autor e URL em `origem`). Eles migram como templates `externo`: `origem` perde autor, URL e
métricas da fonte, `referencia/` fica só na máquina, e o resto sobe para a galeria compartilhada
normalmente, pelo mesmo envio automático.
