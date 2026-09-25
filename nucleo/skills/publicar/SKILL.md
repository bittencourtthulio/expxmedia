---
name: publicar
description: >
  Publica agora ou agenda uma peça já aprovada, pelo provedor que a verificação da instalação
  escolhe (Expx Flow ou Graph API da Meta), sempre com dry-run antes e o sim da pessoa. Use quando o
  pedido for "publica essa peça", "agenda para amanhã às 18h", "sobe esse carrossel no Instagram",
  "por que a publicação falhou", "instala o agendador". Não use para produzir a peça (skills
  criar-post, criar-carrossel, criar-reel e as demais) nem para mexer no .env (skill ambiente).
---

# Publicar ou agendar uma peça

Publicar é ação externa e irreversível: cria um registro real na conta da empresa, e nenhum dos
dois provedores desfaz um agendamento pela API (só pela tela do provedor). Por isso esta skill
tem quatro regras que não se negociam:

1. **Só com pedido.** Produzir termina em arquivo. Publicar é decisão da pessoa, a cada peça, dita
   nesta conversa. Pedido de "produzir" não é pedido de publicar.
2. **O dry-run é obrigatório.** Todo envio começa pelo mesmo comando **sem** `--confirmar`; você
   mostra o que seria enviado e espere o sim da pessoa. Só então o mesmo comando com `--confirmar`.
3. **Nunca retente.** Publicação que falhou, ou cujo resultado é desconhecido, não se reenvia
   sem nova ordem da pessoa, depois de conferir no provedor. O motor também nunca retenta: um POST
   repetido duplica a publicação.
4. **Nunca troque de provedor.** O provedor sai da verificação da instalação. Se o provedor
   configurado não está satisfeito, você explica como habilitar; não publica pelo outro.

Delegue a execução ao agente `publicador` quando a peça for longa de conferir ou houver falha a
investigar; ele segue estas mesmas regras.

## 1. Portão

```bash
expxmedia-motor alma validar --raiz .
```

Portão fechado: pare e encaminhe para `/expxmedia:alma` ou `/expxmedia:ambiente`.

## 2. A peça está pronta?

```bash
expxmedia-motor peca status <peca_id> --raiz .
```

- Envio de verdade exige a peça `aprovada` (ou já `agendada`/`publicada`, para outro canal). O
  dry-run aceita `produzida`, para a pessoa ver antes de aprovar.
- Não aprove por conta própria para conseguir publicar: a aprovação vem da revisão da arte e da
  pessoa (`expxmedia-motor peca status <peca_id> --novo aprovada --raiz .`, quando ela disser).
- Reel e corte: a verificação de entrega (`expxmedia-motor verificar`) precisa ter passado na
  produção. Vídeo reprovado não sobe.
- Confira a legenda da peça (`texto/legenda.txt`) e, se houver CTA com palavra-chave, que a palavra
  da arte, da legenda e da automação é a mesma.

## 3. O provedor, pela verificação

```bash
expxmedia-motor capacidades --capacidade publicar --raiz .
expxmedia-motor capacidades --capacidade agendar --raiz .
```

O provedor escolhido aparece na saída. Ele vem de `PROVEDOR_PUBLICAR` e `PROVEDOR_AGENDAR` no
`.env` da instalação quando a pessoa fixou um; sem isso, do provedor que está satisfeito. Você nunca
abre nem edita o `.env`: chave e escolha de provedor são da skill `ambiente`.

- `habilitada: false` ou código 3 no envio (`capacidade_nao_habilitada`): mostre o
  `como_habilitar` e encaminhe para `/expxmedia:ambiente`. Nunca troque de provedor em silêncio,
  nem sugira "publicar pelo outro" sem a pessoa decidir mudar a configuração.
- Agendar pela Graph API exige o agendador local instalado (seção 6).

## 4. Expx Flow e Graph API não são a mesma coisa

Explique à pessoa o que vale para o provedor da instalação dela antes do primeiro envio.

| | Expx Flow (`expxflow`) | Graph API da Meta (`meta_graph`) |
|---|---|---|
| Agendamento | agenda no servidor: a máquina pode estar desligada no horário | a API não agenda: o agendador local desta máquina publica no horário, só com a máquina ligada; publica até 15 minutos depois do horário, e passou disso marca `falhou` com o motivo, sem publicar atrasado |
| Automação de DM ("comente PALAVRA") | existe: a DM só existe no Expx Flow | não existe; peça com CTA de DM não tem quem responda |
| Itens do carrossel | 2 a 20 | 2 a 10 |
| Imagem | PNG, JPEG, WebP ou GIF, até 10 MB; o provedor hospeda | só JPEG (o motor converte o PNG), proporção de 4:5 a 1.91:1: post 9:16 é recusado |
| Vídeo no carrossel (carrossel misto) | enviado assumindo aceite; se o servidor recusar, a peça registra a falha com o motivo | aceito como item; reel não entra em carrossel |
| Antecedência do horário | pelo menos 3 min no futuro | a do agendador (no minuto) |
| Limite diário | não documentado | 50 publicações em 24 h, conferidas antes de enviar |
| Legenda | a da peça, com as hashtags separadas | até 2200 caracteres e 30 hashtags |
| Mídia de vídeo | por URL pública temporária (túnel), aberta só durante o envio | por túnel aberto até o processamento terminar |

**Automação de DM.** Só existe no Expx Flow; pela Graph API ela não existe. Se a peça promete
"comente PALAVRA", a automação vai no mesmo envio com `--dm <arquivo.json>`: o bloco de automação
do Expx Flow, gravado em `rascunhos/<assunto>/dm.json`:

```json
{"keywords": ["palavra", "palavras"], "mensagem": "texto da DM", "link": "https://...",
 "link_label": "até 20 caracteres", "match_mode": "any"}
```

- `keywords`: a mesma palavra da arte e da legenda, mais o plural e as grafias que o teclado
  costuma estragar. `mensagem` e `link` saem da peça e da Alma, nunca inventados.
- Provedor `meta_graph` (ou Expx Flow não configurado) com `--dm`: código 3 com o `como_habilitar`.
  Nunca tire o `--dm` em silêncio para conseguir publicar: diga à pessoa que, sem a automação, o
  CTA de DM cai no vazio, e ela decide.
- Bloco inválido (sem `keywords`, `link_label` longo demais): código 2 com os `achados`.

## 5. Dry-run, sempre primeiro

Agendar (o padrão; a data é obrigatória):

```bash
expxmedia-motor agendar --peca <peca_id> --para 2026-10-02T18:00:00-03:00 --raiz .
```

Com CTA de DM, o mesmo comando com `--dm`:

```bash
expxmedia-motor agendar --peca <peca_id> --para 2026-10-02T18:00:00-03:00 --dm rascunhos/<assunto>/dm.json --raiz .
```

Publicar agora, só quando a pessoa pedir "agora" com todas as letras:

```bash
expxmedia-motor publicar --peca <peca_id> --raiz .
```

- Sem data e hora no pedido de agendar: pare e pergunte. Nunca escolha horário por conta própria.
  Sem fuso dito, use o `empresa.fuso` da Alma e escreva o horário com o deslocamento (ISO 8601).
- Mais de um canal: repita `--canal` (padrão: `instagram`).
- O `--dm` usado no dry-run vai também no envio com `--confirmar`; confira o bloco `automation`
  no `payload` do resumo.
- Mostre à pessoa o resumo do `payload`: provedor, canal, horário, quantos itens, legenda (começo),
  e se a peça tem CTA de DM. Olhe as outras peças já agendadas: horário a menos de 30 min de outra
  publicação no mesmo canal vira aviso no resumo (duas peças no mesmo horário competem entre si).
- Código 2 é recusa antes de qualquer envio: `peca_nao_aprovada`, `horario_invalido`,
  `canal_invalido`, `validacao` (a peça não cabe no provedor: os `achados` dizem o quê),
  `ja_enviada`, `canal_ocupado`. Explique e resolva na peça, não no provedor.

Depois do resumo, espere o sim. Silêncio, "parece bom" sobre outra coisa ou pedido antigo não são
sim.

## 6. Enviar de verdade

Com o sim, o mesmo comando, acrescido de `--confirmar`:

```bash
expxmedia-motor agendar --peca <peca_id> --para 2026-10-02T18:00:00-03:00 --raiz . --confirmar
```

ou

```bash
expxmedia-motor publicar --peca <peca_id> --raiz . --confirmar
```

(com `--dm rascunhos/<assunto>/dm.json` quando o dry-run o teve)

O motor grava a intenção na peça antes de enviar, envia uma vez só e grava o resultado de cada
canal na peça e no rastro. A peça passa a `agendada` ou `publicada`.

**Agendador local (Graph API).** Na primeira vez que a instalação agenda pela Graph API:

```bash
expxmedia-motor agendador instalar --raiz .
```

sem `--aplicar` só mostra o que instalaria no sistema (LaunchAgent no macOS, tarefa no Windows,
systemd ou cron no Linux). Mostre à pessoa, lembre que a máquina precisa estar ligada no horário e,
com o sim dela, rode de novo com `--aplicar`. O sistema chama `expxmedia-motor agendador rodar` a
cada minuto; não rode esse comando à mão sem pedido, porque ele publica de verdade o que chegou no
horário.

## 7. Ler o resultado

- `estado: agendada` ou `publicada` em cada canal: entregue `id_externo`, horário confirmado,
  `url` quando houver e a palavra da DM, se houver.
- Canal publicado com `erro` preenchido (por exemplo, criado no Expx Flow com HTTP 207, ou a
  automação de DM falhou): **não é sucesso**. Diga com todas as letras o que funcionou e o que não:
  o post foi criado, mas o agendamento ou o CTA não.
- Código 1 com `incerto: true` ("resultado desconhecido"): o provedor pode ter criado a publicação.
  Nunca retente. Confira no provedor com a pessoa (a tela dele mostra o que foi criado). Só com nova ordem dela, e depois de ela
  confirmar que não há nada lá, o reenvio usa `--forcar` (que solta a trava de envio duplicado),
  começando de novo pelo dry-run.
- Código 1 sem `incerto`: o provedor recusou (chave, permissão, mídia). Explique o motivo; corrigir
  chave é na skill `ambiente`. Reenviar é nova ordem, com novo dry-run.
- Pela Graph API, `falhou` com erro começando por `atraso`: a máquina estava desligada ou dormindo
  no horário. A peça volta para a pessoa decidir um novo horário.

## Red flags

- Rodar com `--confirmar` sem o dry-run e o sim nesta conversa.
- Retentar, reenviar ou usar `--forcar` porque "deve ter falhado" sem a pessoa conferir no provedor.
- Publicar pelo outro provedor porque o configurado não está habilitado.
- Tratar 207 ou automação falhada como sucesso.
- Escolher horário, aprovar a peça ou abrir o `.env` por conta própria.
