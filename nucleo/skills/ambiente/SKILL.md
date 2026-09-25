---
name: ambiente
description: >
  Configura o ambiente da instalação do ExpxMedia: cria o .env, mostra o que já funciona sem chave
  nenhuma e, para cada capacidade que a pessoa quiser ligar (narração, avatar, imagem por IA, banco de
  imagens, publicação e agendamento), explica o que ela libera e onde conseguir a chave. Use quando o
  portão encaminhar para /expxmedia:ambiente, quando não houver .env, ou quando a pessoa pedir para
  habilitar um recurso. A chave é colada no arquivo, nunca na conversa.
---

# Ambiente da instalação

Uma capacidade é algo que o sistema sabe fazer (narrar, gerar avatar, publicar). Ela está habilitada
quando o provedor dela está satisfeito: a chave está no `.env`, o login do programa está feito ou o
programa está instalado. **Recurso sem chave não existe**: não aparece, não é sugerido e não quebra.

## Regras que não se negociam

- **Cole a chave no arquivo, nunca na conversa.** Chave colada na conversa fica no histórico do
  assistente. Você nunca pede a chave, nunca abre, lê, edita nem imprime o `.env` (o hook de segredo do
  núcleo bloqueia de qualquer jeito) e nunca repete um valor de chave em resposta.
- **Nada de uma vez.** Mostre o que cada bloco libera, pergunte o que a pessoa quer usar agora e trate
  uma capacidade por vez.
- **O `.env` pode ficar vazio.** O portão só exige que o arquivo exista. Sem chave nenhuma já saem
  post único, carrossel, apresentação e reel sem narração.
- **Sem troca silenciosa de provedor.** Se a pessoa escolheu publicar por um provedor, o sistema nunca
  publica pelo outro sem ela pedir.
- Pack ou programa não instalado não entra na conversa: fale só do que o motor listar.

## 1. Criar o arquivo de ambiente

Na raiz da instalação:

```bash
expxmedia-motor ambiente exemplo --raiz .
expxmedia-motor ambiente criar-env --raiz .
```

O primeiro gera o `.env.example` (sem valor nenhum, versionável): um bloco por grupo de chaves, com o
que cada bloco libera e a linha "Onde conseguir". O segundo cria o `.env` a partir dele, **só se ainda
não existir** (um `.env` que já existe nunca é tocado), e põe o `.env` no `.gitignore`.

## 2. Mostrar o que já funciona e o que está desligado

```bash
expxmedia-motor capacidades --raiz .
```

Apresente em duas listas curtas, em linguagem de gente (não em ids):

- **Já funciona, sem chave nenhuma**: as capacidades com `habilitada: true` (render de imagem e de
  vídeo, edição de vídeo, transcrição, legenda, captura de página, conforme o motor listar), e o que
  elas permitem produzir.
- **Pode ser ligado**: as desligadas, cada uma com o que libera:

| Bloco | O que libera |
|---|---|
| narrar | a voz clonada do porta-voz em reels, aulas e apresentações narradas |
| avatar | o porta-voz falando em vídeo, gerado a partir do áudio da narração |
| imagem_ia | imagem gerada por IA para slides e capas |
| banco_imagens | fotos e vídeos de banco (b-roll) com licença |
| rosto_ia e video_ia | o porta-voz em cena nova e vídeos curtos por IA (login do programa do provedor) |
| publicar e agendar | publicar agora ou num horário futuro, pelo provedor escolhido |
| automacao_dm | comentário com palavra-chave vira mensagem direta automática |

Pergunte, numa frase, o que a pessoa quer ligar agora. "Nada por enquanto" é uma resposta válida: o
portão já está aberto.

## 3. Ligar uma capacidade

Para cada escolha:

1. Consulte o que falta:

   ```bash
   expxmedia-motor capacidades --capacidade <capacidade> --raiz .
   ```

2. Explique o `como_habilitar` da saída: o nome exato da variável e o trecho **Onde conseguir**, com o
   caminho no painel do provedor.
3. Peça: *"Abra o arquivo `.env` na raiz, cole a chave na linha da variável, depois do `=`, e salve.
   Me avise quando terminar. Não cole a chave aqui."*
4. Quando a pessoa avisar, rode a mesma consulta e confirme `habilitada: true`. Se continuar
   desligada, mostre de novo o que falta (o nome da variável, nunca um valor).

Capacidades que dependem de porta-voz (`narrar`, `avatar`, `rosto_ia`) só ficam habilitadas para um
porta-voz com o id correspondente na Alma. Consulte com `--porta-voz <id>`; se faltar o id, a pessoa o
cadastra pela skill `alma`.

Com mais de um provedor de publicação satisfeito, o padrão sai da variável `PROVEDOR_PUBLICAR` (e
`PROVEDOR_AGENDAR`). Explique a diferença na hora da escolha: um provedor agenda no próprio servidor e
hospeda a mídia; a API direta da rede social não agenda sozinha, e quem agenda é o agendador local, que
exige a máquina ligada no horário da publicação.

Sobre o motor de vídeo (Remotion): ele é gratuito para empresas pequenas e pago acima de um certo porte.
Avise a pessoa para conferir os termos da licença do Remotion antes de produzir vídeo em escala.

## Se a pessoa colar a chave na conversa mesmo assim

Não repita o valor. Grave pelo motor, com o valor pelo stdin, e avise:

```bash
printf '%s' '<valor colado>' | expxmedia-motor ambiente gravar-chave --nome <NOME_DA_VARIAVEL> --raiz .
```

Depois diga: *"Gravei no `.env`, mas o valor passou pela conversa e ficou no histórico. É bom girar a
chave no painel do provedor e colar a nova direto no arquivo."* O motor só aceita nomes do catálogo
(os que aparecem no `.env.example`).

## Ao terminar

Rode `expxmedia-motor capacidades --raiz .` uma última vez e mostre o que ficou ligado. O portão está
aberto: a pessoa já pode pedir a primeira peça.
