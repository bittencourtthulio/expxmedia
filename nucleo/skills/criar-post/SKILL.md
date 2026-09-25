---
name: criar-post
description: >
  Cria um post único (uma imagem) do pedido à peça registrada: confere o portão, lê a Alma, escolhe
  o template na galeria, confere os requisitos, escreve a copy com o agente copywriter, revisa com o
  revisor-editorial e o `revisar copy` do motor e produz a peça. Use quando o pedido for "faz um
  post sobre X", "uma arte só com essa frase", "post estático para amanhã". Não use para carrossel
  (skill criar-carrossel) nem para publicar (skill publicar).
---

# Criar um post único

Post único é uma mensagem completa numa imagem só: título que apresenta a ideia, apoio que explica
o mecanismo ou a aplicação (e não repete o título com outras palavras) e um CTA. Se o assunto não
cabe, reduza o recorte; carrossel só quando a pessoa aceitar mudar o formato.

O caminho é o mesmo do carrossel (skill `criar-carrossel`), com as diferenças abaixo. Siga as
seções na ordem.

## 1. Portão

```bash
expxmedia-motor alma validar --raiz .
```

Portão fechado: pare e encaminhe para `/expxmedia:alma` (sem Alma confirmada) ou
`/expxmedia:ambiente` (sem `.env`). Nenhuma peça sai sem Alma.

## 2. Ler a Alma

Leia `alma/alma.json` (e `alma/voz.md`, `alma/publico.md` quando existirem). Público
(`publico.principal`, `publico.dores`, `publico.desejos`), voz (`voz.tom`, `voz.tratamento`,
`voz.regras`, `voz.palavras_proibidas`), ofertas, `cta.padrao`, `cta.destino` e `restricoes` saem
só dali. Um leitor principal, uma tese e um CTA por peça. Campo `null` não se preenche com palpite.

## 3. Buscar na galeria

```bash
expxmedia-motor galeria buscar --tipo post_unico --formato 4:5 --serve-para <uso> --raiz .
```

Use `--formato 1:1` ou `9:16` só quando a pessoa pedir. Leia o `template.json` do escolhido: o
`max` de cada slot é o limite da copy.

## 4. Verificar os requisitos

```bash
expxmedia-motor capacidades --raiz .
```

Post de imagem precisa só de `renderizar_html`. Foto de banco (`banco_imagens`), imagem gerada
(`imagem_ia`) e rosto do porta-voz em cena nova (`rosto_ia`) são opcionais: sem eles, a arte se
resolve com texto e forma. Template com `exige_porta_voz` sem porta-voz na Alma sai com o
substituto desenhado (`expxmedia-motor imagem retrato --raiz .`).

## 5. Escrever a copy (agente `copywriter`)

O `copywriter` escreve `entrada.json` (com um slide só), `copy.txt` e, quando houver, `legenda.txt`
numa pasta de trabalho. Referência de densidade do post estático, que o `max` do template
prevalece: título de 4 a 11 palavras, apoio de 12 a 32, CTA de 5 a 16, até 60 no conjunto.

## 6. Revisar a copy

```bash
expxmedia-motor revisar copy --arquivo rascunhos/<assunto>/copy.txt --arquivo rascunhos/<assunto>/legenda.txt --palavra-publicacao <PALAVRA> --raiz .
```

Depois, o `revisor-editorial` na passada 1, com a saída do motor. Bloqueante volta para o
`copywriter` (no máximo duas voltas) e impede renderizar.

Imagem no post segue a seção 7 do `criar-carrossel`: uma foto de banco ou gerada, no máximo,
sempre aprovada pelo `validador-imagem` antes de entrar; slot de pessoa só com retrato do
porta-voz. A busca no banco (`expxmedia-motor imagem pexels --termo "<descrição em inglês>" --raiz .`)
já sai filtrada pelo motor (duplicata, tamanho, pessoa no `alt`); não filtre à mão.

## 7. Produzir e registrar a peça

```bash
expxmedia-motor produzir post --entrada rascunhos/<assunto>/entrada.json --raiz .
```

O motor valida os slots antes de renderizar, cria a peça e a deixa `produzida`. `slots_invalidos`
não cria nada; `render_reprovado` deixa a peça em `roteiro` com os `problemas` medidos.

Passada 2: o `revisor-editorial` abre `slides/slide_01.png`. Aprovada:

```bash
expxmedia-motor peca status <peca_id> --novo aprovada --raiz .
```

Entregue título, `peca_id`, pasta, CTA e veredito. Publicar é a skill `publicar`.
