---
name: criar-carrossel
description: >
  Cria um carrossel (inclusive o carrossel misto, com slides de vídeo) do pedido à peça registrada:
  confere o portão, lê a Alma, escolhe o template na galeria, confere os requisitos, escreve a copy e
  a legenda com o agente copywriter, revisa em duas passadas com o revisor-editorial e o
  `revisar copy` do motor, valida as imagens com o validador-imagem e produz a peça. Use quando o
  pedido for "faz um carrossel sobre X", "monta um carrossel de N slides", "o próximo da série Y",
  "carrossel com um slide em vídeo". Não use para post de uma imagem só (skill criar-post) nem para
  publicar (skill publicar).
---

# Criar um carrossel

O carrossel é o formato em que a copy mais pesa: capa que para o dedo, slide 2 que funciona como
segunda capa, uma tese só, um CTA só. Esta skill orquestra; quem escreve é o agente `copywriter`,
quem revisa é o `revisor-editorial` (só leitura), quem julga imagem é o `validador-imagem` (só
leitura) e quem renderiza e registra é o motor (`expxmedia-motor`). Siga as seções na ordem. Cada
uma termina num resultado que a próxima usa.

**Quem manda em quê.** A Alma decide o conteúdo (voz, público, ofertas, CTA, o que não entra). O
template decide a forma (kinds, slots, limite de caracteres de cada slot). Esta skill guarda o
método. Conflito de forma: vence o template naquele item e quem escreveu avisa; ninguém muda o
template para caber a copy.

## 1. Portão

Antes de qualquer outra coisa, na raiz da instalação:

```bash
expxmedia-motor alma validar --raiz .
```

- `portao.aberto: false` ou "não tem alma/alma.json": pare. Diga à pessoa que a Alma ainda não
  está confirmada e encaminhe para `/expxmedia:alma`. Nenhuma peça sai sem Alma.
- Sem `.env` na raiz: encaminhe para `/expxmedia:ambiente`. Ele pode estar vazio: carrossel de
  imagem sai sem chave nenhuma.
- Portão aberto: siga.

## 2. Ler a Alma

Leia `alma/alma.json` inteiro e, quando existirem, `alma/voz.md` e `alma/publico.md`. É daqui, e
só daqui, que saem:

| O quê | Campo da Alma | Como pesa na peça |
|---|---|---|
| Para quem | `publico.principal`, `publico.dores`, `publico.desejos` | a peça escolhe **um** leitor principal para a capa |
| Como fala | `voz.tom`, `voz.tratamento`, `voz.formalidade`, `voz.regras`, `voz.palavras_preferidas`, `voz.exemplos_bons`, `voz.exemplos_ruins` | tratamento e regras são obrigação, não sugestão |
| O que nunca entra | `voz.palavras_proibidas`, `restricoes.temas_proibidos`, `restricoes.promessas_proibidas`, `restricoes.observacoes_legais` | é bloqueante na revisão |
| O que se oferece | `ofertas[]` (a `principal` primeiro) | oferta que não está aqui não existe na peça |
| Para onde leva | `cta.padrao`, `cta.destino`, `cta.variacoes` | um CTA por peça, e só um destes |
| Quem aparece | `porta_vozes[]` e os `retratos` de cada um | slot de pessoa só aceita retrato do porta-voz |

Nada disso vem de memória, de outra peça nem de exemplo desta skill. Campo `null` na Alma é
ausência: não preencha com palpite; se a peça precisa dele (uma oferta, um destino de CTA), pergunte
à pessoa numa frase só ou faça a peça sem aquilo.

Leia também, em `pecas/`, a copy das duas ou três peças mais recentes do mesmo assunto ou série:
a abertura não se repete.

## 3. Buscar na galeria

Escolha o template antes de escrever. A forma define quantos slides, o papel de cada kind e o limite
de cada slot, e a copy é escrita para ela.

```bash
expxmedia-motor galeria buscar --tipo carrossel --formato 4:5 --serve-para <uso> --raiz .
```

- `--serve-para` diz o que a peça precisa fazer (lista, passo a passo, comparação...); `--estilo`
  estreita pela cara; `--kind` restringe aos kinds que você pretende usar.
- Abra a `prancha` dos candidatos e escolha pelo que a peça precisa dizer, não pelo mais bonito.
- Leia o `template.json` do escolhido: `kinds`, `slots` (com `max` de caracteres), `requisitos` e
  `exige_porta_voz`. É o "GUIA" desta peça: estrutura e limites saem daqui.
- Nada serve? Diga isso e mostre o mais próximo. Não desenhe template novo nesta skill.

## 4. Verificar os requisitos

A busca já descarta o que esta instalação não consegue produzir (`descartados` com `falta` e
`como_habilitar`). Confira mesmo assim o que a peça inteira vai precisar:

```bash
expxmedia-motor capacidades --raiz .
```

| Precisa de | Capacidade | Sem ela |
|---|---|---|
| qualquer slide de imagem | `renderizar_html` | não há carrossel; explique o `como_habilitar` |
| slide de vídeo (carrossel misto) | `renderizar_motion` | faça o carrossel só de imagem, ou pare e explique |
| foto de banco num slide | `banco_imagens` | o slide se resolve com texto, forma ou print |
| imagem gerada | `imagem_ia` | idem |
| rosto do porta-voz em cena nova | `rosto_ia` | use um retrato que já existe |

Template com `exige_porta_voz` numa Alma sem porta-voz: o slot de pessoa sai com o substituto
desenhado (`expxmedia-motor imagem retrato --raiz .` diz qual). Diga isso à pessoa.

## 5. Escrever a copy (agente `copywriter`)

Passe ao `copywriter`: o pedido, o template escolhido (id e caminho do `template.json`), os campos
da Alma do passo 2 e a copy das peças vizinhas. Ele escreve, numa pasta de trabalho (por exemplo
`rascunhos/<assunto>/`):

- `entrada.json`, no formato da produção: `template`, `titulo`, `slides` (um objeto por slide, com
  `kind` e os slots), `legenda` e `conteudo` (`gancho`, `gancho_tipo`, `cta`, `cta_forma`);
- `copy.txt`, o texto de todos os slides na ordem, e `legenda.txt`, para a revisão mecânica.

Ele devolve leitor, tipo de gancho, forma e palavra do CTA, tese em uma frase e a tensão com o
template, se houve. Item que já tem copy revisada e só precisa renderizar: pule para a seção 7 e
diga que pulou.

## 6. Revisar a copy (passada 1, antes de renderizar)

Primeiro o que dá para mecanizar, parametrizado pela Alma:

```bash
expxmedia-motor revisar copy --arquivo rascunhos/<assunto>/copy.txt --arquivo rascunhos/<assunto>/legenda.txt --palavra-publicacao <PALAVRA> --serie <série> --raiz .
```

Ele devolve os bloqueantes com arquivo, linha e coluna: travessão (quando a voz da Alma proíbe),
tratamento diferente de `voz.tratamento`, termo de `voz.palavras_proibidas`, palavra-chave do CTA
diferente da da publicação e abertura repetida em 14 dias. O que ele não conseguiu conferir vem em
`nao_conferidos`: não trate como aprovado.

Depois, o agente `revisor-editorial`, passada 1, com a saída do motor, a copy, a legenda, o
`template.json` e a Alma. Veredito **ajustar** com achado bloqueante volta para o `copywriter`.
No máximo duas voltas; se não fechar, traga o impasse à pessoa em vez de renderizar copy
reprovada. Achado bloqueante impede a renderização.

## 7. Imagens da peça (agente `validador-imagem`)

Hierarquia: texto, forma desenhada ou print primeiro. Foto de banco só quando nada disso resolve,
e imagem gerada só quando nem o banco tem. Foto de banco ou gerada: **uma por peça**, no máximo.

1. **Primeiro validador, o mecânico: o motor.** Busque com
   `expxmedia-motor imagem pexels --termo "<descrição em inglês>" --orientacao portrait --conhecido <id> --raiz .`
   (um `--conhecido` para cada id de banco que já saiu numa peça recente). O motor já devolve só o
   que passou nos filtros de banco: duplicata, lado curto abaixo de 1200 px e `alt` que diz ter
   pessoa; `descartados` mostra o que caiu e por quê. Não refaça esse filtro à mão nem use
   `--sem-filtro` para "ter mais opção": o que caiu não entra na peça. Imagem gerada sai de
   `expxmedia-motor imagem openrouter --prompt "..." --saida <arquivo> --proporcao 4:5 --raiz .`
   (entra na cota diária da instalação); com gente, só a partir de um retrato do porta-voz em
   `--base`.
2. **Segundo validador, o olho.** Passe ao `validador-imagem` cada candidata com o texto do slide
   onde ela entra. Ele abre a imagem e devolve aprovar ou recusar, com o porquê. Sem aprovação, a
   imagem não entra no `entrada.json`. Nada aprovado é resposta legítima: o slide se resolve sem foto.
3. **Pessoa.** Slot de pessoa só aceita retrato do porta-voz (`porta_vozes[].retratos`); foto de
   banco e pessoa inventada nunca. Variação gerada do rosto do porta-voz também passa pelo
   `validador-imagem` ("é a mesma pessoa?") antes de entrar.

Foto de banco guarda o crédito (autor e página) na peça; ela nunca vai para dentro de template.

## 8. Produzir e registrar a peça

Com a passada 1 aprovada e as imagens aprovadas:

```bash
expxmedia-motor produzir carrossel --entrada rascunhos/<assunto>/entrada.json --raiz .
```

O motor confere os slots contra o template (kind inexistente, slot desconhecido, obrigatório vazio,
texto acima do `max`) **antes** de renderizar; cria a peça (`peca.json`, `peca_criada`), renderiza
com a Alma, grava `slides/slide_NN.png`, `previa/prancha.png` e `texto/legenda.txt` e passa a peça
para `produzida`. Guarde o `peca_id` da saída.

- `slots_invalidos` (código 2): nada foi criado. Volte para o `copywriter` com os `erros`.
- `render_reprovado` (código 1): contraste, encaixe ou fonte reprovados na medição; a peça fica em
  `roteiro`. Leia os `problemas`: texto que só caberia encolhendo é copy longa demais, não motivo
  para mexer no template.

### Carrossel misto

Um slide é de vídeo quando traz `"midia": "video"` no `entrada.json` (ou quando o kind do template
é de vídeo). Ele é renderizado em Remotion, no mesmo 4:5 dos outros, com a Alma, e sai como
`slides/slide_NN.mp4`. Slots do slide de vídeo sem kind próprio no template: `etiqueta`, `titulo`
(entra palavra a palavra), `texto` e `duracao_s` (padrão 6 s, de 3 a 60 s). Exige
`renderizar_motion` (seção 4). Na publicação, o provedor recebe cada filho com a sua mídia; se um
provedor recusar vídeo como filho, a peça registra a falha com o motivo e a peça não muda.

## 9. Conferir a arte (passada 2)

O `revisor-editorial` abre `previa/prancha.png` e os slides (capa, um do meio e o último; no
misto, também um quadro de cada vídeo). Texto cortado, fonte encolhida demais, acento faltando,
palavra órfã no fim de bloco, capa em que a afirmação não é o maior elemento: volta para a seção 5
ou 8. Aprovada, e só então:

```bash
expxmedia-motor peca status <peca_id> --novo aprovada --raiz .
```

## 10. Entregar

Diga: título, `peca_id`, pasta da peça, tipo de gancho, leitor, CTA e palavra, veredito das duas
passadas e o que ficou pendente (imagem que faltou, capacidade desligada). Publicar é outro pedido
e outra skill (`publicar`).

## Red flags

- Renderizar copy com achado bloqueante aberto, ou declarar aprovado sem ter aberto a prancha.
- Escrever a copy antes de escolher o template: o limite de caracteres vem dele.
- Tirar voz, público, oferta ou CTA de outro lugar que não a Alma.
- Usar imagem que o `validador-imagem` não aprovou, foto de banco com pessoa, ou mais de uma foto
  de banco ou gerada por peça.
- Mudar template ou fonte para acomodar copy longa.
- Pular `revisar copy` porque "o revisor vai ver": o mecânico pega o que já foi ao ar errado.
