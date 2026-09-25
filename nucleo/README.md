# Plugin `expxmedia` (o núcleo)

Esta pasta é o plugin do Claude Code que entrega o núcleo do ExpxMedia: as skills que produzem
peças (post único, carrossel, reel, apresentação, aula, corte), publicam e agendam, os agentes
que escrevem e revisam, os comandos de configuração e os hooks de portão e de segredo. Todo o
trabalho pesado é do motor em Python ([`motor/`](../motor/README.md)); as skills conversam com a
pessoa e chamam o `expxmedia-motor`.

Nada aqui pertence a uma marca. A identidade da empresa vem da Alma (`alma/alma.json`) da
instalação e as chaves de provedor vêm do `.env`.

## Uso em desenvolvimento

Prepare o motor uma vez (`cd motor && uv run python scripts/preparar_ambiente.py`) e abra o
Claude Code na raiz do repositório carregando o plugin desta pasta:

```bash
claude --plugin-dir nucleo
```

As skills e comandos aparecem com o prefixo `expxmedia:` (por exemplo `/expxmedia:alma`). Para
conferir o manifesto e a estrutura: `claude plugin validate nucleo`.

## O portão

Nenhuma produção começa sem a instalação estar pronta, e a ordem é fixa:

1. **Alma.** Sem `alma/alma.json` confirmada, o caminho é `/expxmedia:alma`: a Alma é montada a
   partir do site da empresa ou por entrevista e só é gravada depois do "confirmo tudo".
2. **Ambiente.** Sem `.env` na raiz da instalação, o caminho é `/expxmedia:ambiente`: o `.env` é
   criado, a pessoa vê o que já funciona sem chave e cola no arquivo as chaves que quiser ligar.
3. Com as duas coisas no lugar, o portão está aberto.

O portão é conferido em duas camadas: pelo hook `expxmedia-portao.sh`, antes de cada pedido, e
pelo primeiro passo de toda skill de produção.

## Skills

| Skill | O que faz |
|---|---|
| `alma` | cria, completa ou revisa a Alma da empresa, pelo site ou por entrevista |
| `ambiente` | cria o `.env`, mostra o que já funciona e orienta onde conseguir cada chave |
| `criar-post` | post único do pedido à peça registrada, com copy e revisão |
| `criar-carrossel` | carrossel (inclusive o misto, com slides de vídeo), com copy, revisão e validação das imagens |
| `criar-apresentacao` | apresentação de 6 a 10 slides em HTML navegável e, se pedido, MP4 e PNG por slide |
| `criar-reel` | reel narrado 9:16 em Remotion a partir de um template de reel da galeria |
| `reel-de-pagina` | reel narrado a partir de uma página web capturada antes do roteiro |
| `reel-por-referencia` | recria um reel de referência o mais parecido possível, com composição sob medida |
| `cortar-video` | reel 9:16 com a fala original a partir de um trecho de vídeo longo |
| `criar-aula` | aula narrada em 16:9 e 9:16 com SRT, tela editada no tempo da fala e avatar opcional |
| `publicar` | publica agora ou agenda uma peça aprovada, sempre com dry-run antes e o sim da pessoa |

## Comandos

| Comando | O que faz |
|---|---|
| `/expxmedia:alma` | abre a skill `alma`: cria, completa ou revisa a Alma |
| `/expxmedia:ambiente` | abre a skill `ambiente`: `.env`, capacidades e onde conseguir cada chave |

## Agentes

| Agente | O que faz |
|---|---|
| `copywriter` | escreve a copy e a legenda de post único e carrossel na voz da Alma |
| `revisor-editorial` | só leitura: revisa a copy antes do render e a arte depois |
| `validador-imagem` | só leitura, com visão: aprova ou recusa cada imagem nova de uma peça |
| `roteirista` | escreve o roteiro narrado do reel a partir da fonte lida inteira |
| `revisor-reel` | só leitura: audita o reel narrado e dá o veredito PUBLICAR ou SEGURAR |
| `revisor-video` | só leitura: audita o reel por referência e dá o veredito APROVADO ou REPROVADO |
| `publicador` | roda publicação e agendamento com dry-run e investiga envio que falhou |

## Hooks

Declarados em `hooks/hooks.json`:

- `expxmedia-portao.sh` (antes de cada pedido): confere o portão só com arquivos locais e, se a
  Alma ou o `.env` faltam, injeta a instrução do primeiro degrau que falta (`/expxmedia:alma` ou
  `/expxmedia:ambiente`). Falha aberta: qualquer erro interno não bloqueia o pedido.
- `expxmedia-segredo.sh` (antes de ler, escrever, buscar ou rodar comando): bloqueia qualquer
  acesso ao `.env` e variantes, a arquivos de token e `client_secret*`, a expansão de variável de
  segredo no terminal e o despejo do ambiente inteiro. Os exemplos sem valor (`.env.example`)
  passam. Falha fechada: na dúvida, bloqueia. A chave vai para o `.env` pela mão da pessoa, nunca
  pela conversa.
