---
name: cortar-video
description: >
  Transforma um trecho de vídeo longo já gravado (aula, palestra, live, entrevista do porta-voz) num
  reel vertical 9:16 com a fala original: transcrição da fonte, escolha do trecho lendo o texto pelas
  quatro perguntas do corte, plano de um ou vários pedaços sem mudar o sentido, reenquadramento que
  segue o rosto, gancho fixo no topo, b-roll opcional com licença, legenda, verificação e revisão. Use
  quando pedirem "corta esse vídeo", "tira um reel dessa aula" ou para retomar um corte que falhou.
  Reel narrado com voz clonada é a criar-reel ou a reel-de-pagina. Não publica.
---

# Cortar vídeo longo em reel

Aqui o áudio existe antes de tudo, e é a pessoa falando. Somem o roteiro, a narração e o crédito;
entram a **escolha do trecho**, o reenquadramento e o gancho fixo. O formato ganha ou perde na escolha,
e a escolha é julgamento de quem **leu** a transcrição: o motor pré-filtra o que é mecânico, e a nota
dele é desempate.

## Regras que não se negociam

- **O corte nunca distorce o que foi dito.** Veja as regras invioláveis da emenda no passo 6.
- **Este formato não tem CTA, e isso é decisão.** A fala é uma aula, não um roteiro escrito para
  converter: enxertar card pedindo comentário que a fala não pede é exatamente o que a verificação
  existe para impedir. Sem palavra de comentário não há automação de resposta.
- **B-roll só de banco com licença comercial**, nunca trecho de vídeo de terceiro.
- O vídeo é de quem a Alma cadastrou como porta-voz, ou material que a empresa tem direito de usar.
- Nada é publicado aqui.

## 1. Portão

```bash
expxmedia-motor alma validar --raiz .
```

Com `portao.aberto: false`, pare e encaminhe para o que `portao.encaminhar` disser.

## 2. Ler a Alma

Leia `alma/alma.json` e `alma/voz.md`: o idioma (é o da transcrição), as fontes e cores (legenda e
gancho fixo saem delas), `restricoes` e quem é o porta-voz que fala no vídeo. A `voz` da Alma vale para
o gancho fixo e a legenda do post; a fala em si não se reescreve.

## 3. Galeria: este formato não usa template

O corte não sai de template: o vídeo é a própria gravação, e o visual (legenda, caixa do gancho) vem
da Alma. Não rode busca na galeria para ele.

## 4. Conferir os requisitos

```bash
expxmedia-motor capacidades --capacidade transcrever --raiz .
expxmedia-motor capacidades --capacidade editar_video --raiz .
expxmedia-motor capacidades --capacidade banco_imagens --raiz .
```

`transcrever` e `editar_video` são obrigatórios; `banco_imagens` só se o corte levar b-roll. O vídeo
fonte tem de estar na instalação (por exemplo em `fontes/`), com pelo menos 180 s: abaixo disso já é
um vídeo curto, e cortar não acrescenta nada.

## 5. Transcrever a fonte

```bash
expxmedia-motor transcrever --audio fontes/<video>.mp4 --saida fontes/<video>/transcricao.json --modo varredura --raiz .
```

A varredura usa o modelo rápido na gravação inteira: serve só para escolher o trecho, e erro de grafia
aqui não vai para a tela. A transcrição fica em `fontes/`, fora das peças, porque é cache: o segundo
corte da mesma gravação não transcreve de novo. O texto que vai queimado na tela é transcrito de novo
na produção, só no corte, com o modelo maior.

## 6. Escolher o trecho

Leia a transcrição com os instantes. Cada candidato passa pelas quatro perguntas:

- **O trecho se sustenta sem o que veio antes?** "Então isso aí é o que eu falei" é o defeito clássico:
  quem chega pelo feed não viu nada antes.
- **Os três primeiros segundos prometem alguma coisa?** O gancho aqui não se escreve, se escolhe: se o
  trecho abre morno, comece alguns segundos depois, num ponto que abre melhor.
- **Fecha?** Trecho que termina no meio de um raciocínio frustra e não gera comentário.
- **Rende sem imagem de apoio?** Se a pessoa está apontando para um slide ou tela que o corte não
  mostra, o b-roll não salva.

Entre dois pontos de entrada aceitáveis, ganha o que tem **número de dinheiro ou de quantidade nas
primeiras palavras** (o sinal mais forte medido no corte), desde que seja benefício ou dor e não
inventário. A primeira palavra do reel diz alguma coisa: muleta ("Bom,", "Tá,", "Olha só,"), falsa
largada, anáfora ("então isso aí") e referência para fora ("no vídeo anterior") entram na palavra
**seguinte**. Categoria abstrata e metáfora na largada perdem.

Se você rodar a produção sem trecho nem plano, o motor escolhe pelos momentos e guarda os candidatos
em `candidatos.json`; mas **a nota é desempate, não veredito**: ela conhece palavras, não sentido.
Leia os candidatos e passe o trecho escolhido.

Nada obriga a usar um pedaço só: numa gravação longa a ideia inteira quase nunca está num intervalo
só, e o plano pode juntar vários. As regras da emenda são invioláveis:

- **Nenhuma emenda cria frase que não foi dita.** Emendar "isso funciona" de um lugar com "sempre" de
  outro é inventar fala na voz da pessoa, e ninguém duvida do que ouve na própria voz.
- **A ressalva viaja com a afirmação.** "Isso funciona, mas só quando..." não pode acabar antes do
  "mas", nem no fim de um pedaço nem na emenda.
- Cada pedaço tem **no mínimo 4 segundos**; abaixo disso é estilhaço.
- Os pedaços não se sobrepõem e vão em **ordem cronológica**: inverter o que foi dito muda o sentido.

Duração: alvo de 60 s, piso de 52 s de material, teto de 180 s. Acima de 75 s escreva o `por_que` de
cada pedaço a mais: não porque o relógio puna (a duração não explicou o desempenho na origem), mas
porque cauda sem ideia nova é cauda. Faixa que já virou corte não repete: sobreposição acima de 20%
com um corte anterior é recusada.

## 7. Gancho fixo no topo

Escreva até **3 linhas curtas em CAIXA ALTA**: o texto fica fixo no topo o vídeo inteiro, acima da
legenda. Ele **não herda a isenção do gancho** do reel narrado: fica escrito do primeiro ao último
quadro, então **só promete o que a fala daquele corte entrega**. Concretude vale igual: coisa que dá
para ver, não categoria. Não é CTA: nada de "comente", "siga", "link". Sem gancho só com motivo, pela
válvula `sem_gancho`.

## 8. B-roll, se o corte pedir

Quem escolhe os termos é quem leu o trecho, **em inglês e descrevendo a imagem**, não o conceito
("developer typing code at night", não "produtividade"). As regras de colocação são cobradas antes de
buscar: os 3 s de abertura e os 2 s de fecho ficam livres (o rosto segura o começo, e o último quadro
congela no loop), cada inserção tem de 2 a 4 s, 4 s de respiro entre duas, e o total não passa de 40%
do corte. Termo sem resultado faz a produção parar: troque o termo, nunca deixe buraco. Corte sem
b-roll é legítimo.

## 9. Registrar a peça e produzir

Grave `rascunhos/<slug>/corte.json`:

```json
{
  "video": "fontes/<video>.mp4",
  "titulo": "<título da peça>",
  "gancho": ["<LINHA 1>", "<LINHA 2>"],
  "plano": [{"inicio": 512.4, "fim": 548.9, "por_que": "a dor e a saída"},
            {"inicio": 601.2, "fim": 626.0, "por_que": "a prova, com a ressalva inteira"}],
  "enquadramento": "auto",
  "broll": null,
  "legenda": null,
  "porta_voz": "<id>"
}
```

Um pedaço só vai em `"trecho": {"inicio": s, "fim": s}` no lugar de `plano`. `enquadramento`: `auto`
(segue o rosto e compõe a tela em cima e o rosto embaixo quando a gravação é de tela com câmera),
`rosto`, `central` ou `fundo_desfocado` (o quadro inteiro centrado sobre o próprio quadro borrado:
válvula para plano fechado ou tela, não o padrão, porque deixa o rosto menor). `sem_split` desliga a
composição tela e rosto quando ela atrapalhar.

```bash
expxmedia-motor produzir reel-corte --entrada rascunhos/<slug>/corte.json --raiz .
```

É este comando que registra a peça: cria o `peca.json` em `roteiro`, corta com o reenquadramento,
grava a procedência em `corte.json` da peça (vídeo, trechos, enquadramento, `cta: null`), transcreve o
corte com o modelo maior (é o texto queimado na tela), busca o b-roll, legenda **sem CTA** e sem atraso
(a fala começa no primeiro quadro), compõe o gancho fixo, normaliza em -14 LUFS com pico até -1 dBFS,
verifica no perfil `corte` e passa a peça para `produzida`. Leia os avisos do enquadramento: rosto em
menos de 15% dos quadros cai para o crop central fixo, e aí o enquadramento se confere no olho.

## 10. Verificar e revisar

```bash
expxmedia-motor verificar --perfil corte pecas/<mes>/<peca>/saida/final.mp4 --pasta pecas/<mes>/<peca>/midia --roteiro pecas/<mes>/<peca>/texto/roteiro.txt --raiz .
```

O perfil `corte` aceita de 50 a 185 s (aviso acima de 75 s, que você endereça com o `por_que`), cobra a
cauda muda de no máximo 0,8 s depois da última legenda e não procura card de CTA. Cole a saída.

Depois revise, você ou o `revisor-reel` com este roteiro, sem editar nada:

1. **Fidelidade**: para cada emenda, leia o texto antes e depois da borda, nos dois lados. Frase que
   não foi dita, ressalva cortada ou ordem invertida é BLOQUEANTE.
2. **Abertura**: o trecho começa em frase que se sustenta sozinha?
3. **Legenda contra fala**: nome próprio e jargão errados vão queimados na tela. A correção vai no
   campo `correcao` da entrada (o texto corrigido, recasado sobre os mesmos tempos) numa produção nova;
   editar o texto sem recasar é ignorado em silêncio.
4. **B-roll**: autor e licença registrados, nada nos 3 s iniciais nem nos 2 s finais, total até 40%.
5. **Enquadramento**: extraia um quadro de dentro de cada passagem; rosto inteiro, tela legível.
6. **Gancho fixo**: cada promessa tem fala que a entrega (promessa sem fala é BLOQUEANTE); pedir
   comentário ali é BLOQUEANTE; a caixa não tampa o rosto nem a tela.
7. **Sem CTA é o esperado**: cobrar CTA neste formato não é achado.

Veredito **PUBLICAR** ou **SEGURAR**; com PUBLICAR e o de acordo da pessoa:

```bash
expxmedia-motor peca status <peca_id> --novo aprovada --raiz .
```

## A legenda do post, se for publicar

Sai da fala do trecho, não herda isenção de gancho e não promete o que a fala não entrega. Sem palavra
de comentário, o post vai sem automação de resposta.

## Nunca

- Emendar pedaços de modo a formar uma frase que não foi dita.
- Inverter a ordem cronológica do que foi falado.
- Cortar antes da ressalva para deixar a afirmação mais forte.
- Cortar de novo uma faixa que já virou vídeo.
- Usar b-roll sem licença, "porque ninguém vai ver".
- Enxertar CTA que a fala não diz, ou escrever no gancho fixo promessa que a fala não entrega.
