---
name: criar-aula
description: >
  Produz uma aula narrada em 16:9 e 9:16 com SRT: gravação de tela (quando há) feita antes, roteiro
  escrito depois com marcações de cue, narração na voz do porta-voz da Alma, tela editada no tempo da
  fala, avatar do porta-voz gerado a partir do áudio da narração, legenda com o texto do roteiro,
  render nos dois formatos e compilação de várias aulas num vídeo só. Use quando pedirem aula,
  videoaula, episódio de curso, tutorial narrado ou demonstração de tela com voz. Não publica.
---

# Aula narrada

Numa aula tudo depende do mesmo relógio: os segundos de cada marcação do roteiro, medidos na
narração. As cenas, a tela editada, o avatar, a legenda e a compilação leem esses mesmos tempos. Por
isso a ordem não se negocia, e **mexer no roteiro ou na narração invalida tudo o que veio depois**.

## Regras que não se negociam

- **O avatar sai sempre do áudio da narração, nunca do texto.** Veja o passo 8.
- **Com tela, a gravação vem antes do roteiro final.** Veja os passos 5 e 6.
- A voz é a do porta-voz da Alma, com os parâmetros de aula dele (mais lenta e mais estável que a do
  reel); cores, fontes e nome vêm da Alma. Nada de nome de série, pessoa ou marca escrito no código ou
  no texto que não venha da Alma ou do pedido.
- Narração e avatar custam crédito e rodam uma vez por produção. Nada roda "para testar".
- Chave de API nunca aparece na tela: grave com dado pessoal e chave ocultos ou mascarados.
- Nada é publicado aqui.

## 1. Portão

```bash
expxmedia-motor alma validar --raiz .
```

Com `portao.aberto: false`, pare e encaminhe para o que `portao.encaminhar` disser.

## 2. Ler a Alma

Leia `alma/alma.json`, `alma/voz.md` e `alma/publico.md`: idioma, tom, tratamento, para quem é a aula,
e o porta-voz (a voz dele com o bloco de parâmetros de aula, o avatar cadastrado). Sem porta-voz com
voz na Alma não há aula narrada; sem avatar cadastrado, a aula sai sem o quadro do porta-voz.

## 3. Buscar na galeria

```bash
expxmedia-motor galeria buscar --tipo aula --formato 16:9 --porta-voz <id> --raiz .
```

Leia o `exemplo.json` do template escolhido: é uma entrada completa de aula e o molde da sua. Sem
template na galeria da instalação, vale a composição de aula do kit.

## 4. Conferir os requisitos

```bash
expxmedia-motor capacidades --capacidade narrar --porta-voz <id> --raiz .
expxmedia-motor capacidades --capacidade renderizar_motion --raiz .
expxmedia-motor capacidades --capacidade avatar --porta-voz <id> --raiz .
expxmedia-motor capacidades --capacidade editar_video --raiz .
```

`narrar` e `renderizar_motion` são obrigatórios. `avatar` é opcional (desligado, a aula sai sem o
porta-voz no canto). `editar_video` é preciso quando a aula tem tela.

## 5. Gravar a tela, quando a aula tem tela

**Grave a tela primeiro**, sem narrar. O núcleo não automatiza a gravação: a pessoa grava a janela do
programa (sem áudio, em mp4 ou mov, com zoom que deixe o texto legível e notificações e dados pessoais
ocultos) e coloca o arquivo na instalação, por exemplo em `gravacoes/<slug>/tela.mp4`. Não precisa
acertar o tempo de cada passo: faça com calma e **pare 2 segundos parado entre um passo e outro**,
que isso vira ponto de corte. Se a gravação tiver marcas de tempo (`marks-rel.json`, com `t0` e as
marcas por rótulo), elas servem para achar cada passo.

## 6. Escrever o roteiro

**Escreva o roteiro depois** da gravação, em cima do que aconteceu de verdade na tela: os resultados,
os números e os tempos reais. Roteiro escrito antes promete o que a tela pode não mostrar.

- É um **roteiro com marcações de cue**: `[[s1]]`, `[[s2]]`... antes de cada trecho, uma cena por
  marcação, na ordem da fala. Subeventos dentro de uma cena ganham nome próprio (`[[s2_prova]]`).
- Números e extensões por extenso ("noventa por cento", "ponto json"): a voz lê algarismo de forma
  imprevisível, e a legenda usa esse mesmo texto.
- Até uns cinco minutos de fala por aula: a narração vai numa chamada só, e o maior áudio testado na
  origem teve 296 s. Aula maior vira várias aulas, compiladas no passo 11.
- Uma estrutura que funciona: abertura com o que a pessoa vai aprender, passos numerados, um resumo e
  o gancho da próxima aula. Fato citado na aula é conferido na fonte, com a data da consulta.

Grave `rascunhos/<slug>/entrada.json` no formato do `exemplo.json`: `titulo`, `roteiro` (com as
marcações), `cenas` (uma por cue, na ordem: `cue`, `modo` `cena`, `tela` ou `slide`, e os campos da
cena: `rotulo`, `titulo`, `texto`, `itens`, `passo`, `fato`), `formatos` (padrão, os dois), `avatar`
(`true`, `false` ou `null` para usar se estiver habilitado), `porta_voz`, `serie`, e:

- `tela`, quando há gravação: `{"janelas": [...], "marcas": "gravacoes/<slug>/marks-rel.json" | null,
  "cue_final": null}`, uma janela por cue de tela, na ordem da fala:
  `{"cue": "s2", "arquivo": "gravacoes/<slug>/tela.mp4", "inicio": 12.3, "fim": {"marca": "passo3"},
  "rotulo": "editor", "camera": [{"t": 0, "cx": 700}], "crop": null, "crop9": null}`;
- `apresentacao`, quando os slides vêm de uma apresentação produzida com `--mp4` (o `peca_id` dela).

## 7. Registrar a peça e produzir

```bash
expxmedia-motor produzir aula --entrada rascunhos/<slug>/entrada.json --raiz .
```

É este comando que registra a peça (o `peca.json` nasce em `roteiro`) e roda o pipeline na ordem de
dependências:

1. a entrada é conferida antes de criar a peça: cada cena aponta para uma marcação do roteiro, na
   ordem; cena de tela exige a gravação; cena de slide exige a apresentação com os PNG;
2. a **narração gera o áudio e os cues**: `midia/narracao.mp3`, o alinhamento por caractere e
   `midia/cues.json`, o segundo em que cada marcação começa a ser falada;
3. a **gravação de tela no tempo da fala**: cada janela é cortada para caber no tempo da fala do seu
   cue, só acelerando (com selo de acelerado) ou congelando o último quadro, nunca em câmera lenta,
   com enquadramento próprio em cada formato;
4. o **avatar depois da narração**, a partir do `narracao.mp3` (passo 8), com a mesma duração da fala;
5. a **legenda com o texto exato do roteiro**, nos tempos de cada palavra (42 caracteres por linha,
   2 linhas, corte equilibrado sem palavra órfã), e o SRT de cada formato. Os tempos vêm do
   alinhamento da narração, que faz o papel da transcrição com tempo por palavra da origem: a legenda
   nunca usa o texto transcrito, que erra nome próprio e número;
6. o **render 16:9 e 9:16** (1920×1080 e 1080×1920, 30 fps), a mistura em -14 LUFS com pico até
   -1 dBFS e a verificação no perfil `aula` de cada formato; aprovada, a peça vai para `produzida` com
   `saida/aula-16x9.mp4`, `saida/aula-9x16.mp4` e os dois SRT.

Reprovada, a peça fica em `roteiro` com `geracao_falhou` no rastro e os `achados`.

**Roteiro ou narração mudou, refaça antes do render**: a legenda, a tela editada e o avatar do jeito
antigo não casam com os cues novos. Não remende arquivo: produza a aula de novo (peça nova) e descarte a
anterior com `expxmedia-motor peca status <peca_id> --novo descartada --motivo "<por quê>" --raiz .`.

## 8. O avatar: sempre do áudio

Gere o **avatar a partir do áudio** da narração (o arquivo é enviado ao provedor e o vídeo sai
falando aquele áudio), **nunca do texto** do roteiro. Vídeo de avatar **gerado pelo texto
não sincroniza**: o provedor sintetiza outra locução, com outra duração, e o quadro do porta-voz nunca
casa com a narração. Gerado do áudio, ele sai com a mesma duração (na origem, 12 ms de diferença em
cinco minutos) e roda em 1x na composição.

A produção faz isso sozinha. Para gerar ou conferir o avatar de uma narração já feita:

```bash
expxmedia-motor avatar gerar --audio pecas/<mes>/<peca>/midia/narracao.mp3 --saida pecas/<mes>/<peca>/midia/avatar.mp4 --porta-voz <id> --raiz .
```

Duração do avatar diferente da narração é defeito: não se estica nem se corta para caber.

## 9. Ajustar a tela sem narrar de novo

Janela cortada no lugar errado se confere com a edição por cues, sobre os `cues.json` da peça:

```bash
expxmedia-motor aula editar-tela --cues pecas/<mes>/<peca>/midia/cues.json --janelas rascunhos/<slug>/janelas.json --saida rascunhos/<slug>/demo.mp4 --raiz .
```

O `demo.json` ao lado mostra, por cue, de onde a janela saiu, até onde foi e a taxa (1 é tempo real;
acima disso, acelerado). Com as janelas certas, atualize a entrada e produza a aula de novo.

## 10. Verificar

A produção já verifica; para colar a saída na entrega:

```bash
expxmedia-motor verificar --perfil aula pecas/<mes>/<peca>/saida/aula-16x9.mp4 --pasta pecas/<mes>/<peca>/midia --srt pecas/<mes>/<peca>/saida/aula-16x9.srt --raiz .
```

Repita para `aula-9x16.mp4`. Assista aos dois: o quadro do porta-voz, a tela e a legenda não se
sobrepõem no 9:16, e a tela está legível.

## 11. Compilar várias aulas

```bash
expxmedia-motor aula compilar --partes rascunhos/<slug>/partes.json --titulo "<título>" --formato 16:9 --raiz .
```

`partes.json` é a lista `[{"peca_id", "ini", "fim", "nome"}]` (`fim: null` vai até o fim). Nada é
regravado: cada parte reusa a aula produzida. Corte no meio das pausas e tire os ganchos "na próxima
aula" e "na aula anterior", que não fazem sentido no vídeo único. O SRT único sai deslocado.

## 12. Aprovar

Com a pessoa de acordo:

```bash
expxmedia-motor peca status <peca_id> --novo aprovada --raiz .
```

## Checklist final

- [ ] Portão aberto, Alma lida, template da galeria, requisitos conferidos
- [ ] Tela gravada antes, roteiro escrito depois com os números reais da tela
- [ ] Marcações de cue na ordem, uma cena por marcação
- [ ] Avatar do áudio da narração, com a mesma duração
- [ ] Legenda com o texto do roteiro, 16:9 e 9:16 verificados, SRT dos dois
- [ ] Nada foi publicado
