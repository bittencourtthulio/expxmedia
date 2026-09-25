# Infraestrutura: escrita atômica, JSONL com trava e utilitários (youtube-squad `comum.py`)

Área: o padrão de persistência de estado que o contrato exige (M15, `ExpxMedia/docs/contrato/CONVENCOES.md:146-151`;
`peca.json` com escrita atômica, `ExpxMedia/docs/contrato/CONTRATO-peca.md:228-229`). Origem:
`youtube-squad/comum.py` (105 linhas), usado por todo módulo do harness do canal ("Todo módulo do harness lê e
grava estado por aqui", `youtube-squad/comum.py:3-5`). Em `cursos-ia` não há equivalente: os scripts gravam
com `write_text`/`json.dump` direto (`cursos-ia/radar-ia-09-jev-calibracao/gerar_voz.py:50,67`;
`cursos-ia/radar-ia-09-jev-calibracao/editar_demo.py:69`; `cursos-ia/radar-ia-09-jev-calibracao/gerar_legendas.py:131`).

## Contrato de entrada

| Função | Assinatura | Linhas |
|---|---|---|
| `ler_json` | `(caminho, padrao=None)` | `youtube-squad/comum.py:21-26` |
| `gravar_json` | `(caminho, dados)` | `comum.py:29-41` |
| `anexar_jsonl` | `(caminho, evento: dict)` | `comum.py:44-55` |
| `ler_jsonl` | `(caminho) -> (eventos, corrompidas)` | `comum.py:58-77` |
| `numero` | `(v, sinal=False) -> bool` | `comum.py:80-84` |
| `valor` | `(v, sinal=False) -> v ou None` | `comum.py:87-89` |
| `agora`, `agora_iso` | `() -> datetime SP`, `() -> ISO segundos` | `comum.py:92-97` |
| `hoje_sp`, `hoje_pacifico` | `(instante=None) -> AAAA-MM-DD` | `comum.py:100-105` |

Fusos fixos: `America/Sao_Paulo` e `America/Los_Angeles` ("o dia da YouTube Analytics API") (`comum.py:16-18`).

## Contrato de saída

- `gravar_json`: cria as pastas pai; grava em `mkstemp` **na mesma pasta** com prefixo = nome do arquivo e
  sufixo `.tmp`; UTF-8, `ensure_ascii=False`, `indent=2`, `\n` final; troca com `os.replace`; qualquer
  exceção (inclusive `KeyboardInterrupt`, por ser `BaseException`) apaga o temporário e relança
  (`comum.py:29-41`).
- `ler_json`: devolve `padrao` se o arquivo não existe (`OSError`) ou não é JSON (`ValueError`); nunca lança
  (`comum.py:21-26`).
- `anexar_jsonl`: uma linha `json.dumps(ensure_ascii=False) + "\n"` em modo `a`, sob `fcntl.flock(LOCK_EX)`,
  com `flush` antes de soltar a trava (`comum.py:44-55`).
- `ler_jsonl`: ignora linha em branco; linha que não é JSON ou não é objeto é pulada e **contada**
  (`comum.py:58-77`). Arquivo ausente → `([], 0)`.
- `numero`/`valor`: número de verdade é `int`/`float` finito, não `bool`; negativo só com `sinal=True`;
  "Ausência nunca vira zero" (`comum.py:80-89`).
- `agora_iso`: `2026-09-24T07:35:47-03:00` (formato real em
  `youtube-squad/apresentacoes/decks/2026-09-24-claude-code-ficou-caro-quanto-custa-de-verdade-e/estado.json`),
  compatível com M5 (horário com fuso).

## Limites e cotas

- A trava é `fcntl.flock` (`comum.py:7,50`): só POSIX; não existe no Windows. O contrato prevê Windows
  para o agendador local (`ExpxMedia/docs/contrato/CONTRATO-capacidades.md:72-76`).
- `flock` é consultiva: protege só contra quem também usa `anexar_jsonl`.
- `gravar_json` não faz `fsync` do arquivo nem da pasta (`comum.py:35-38`): atômico contra leitor
  concorrente, não garantido contra queda de energia.
- Não há trava para leitura-modifica-grava de JSON: duas gravações concorrentes do mesmo JSON terminam com
  a última vencendo (ex.: `apresentacao.validar` lê e grava `estado.json`, `youtube-squad/apresentacao.py:308-313`).
- Tamanho de linha JSONL: sem limite no código.

## Erros conhecidos e tratamento

- Leitor vê meio arquivo: evitado por `os.replace` (`comum.py:30,38`).
- Temporário órfão após erro: apagado no `except BaseException` (`comum.py:39-41`); após `kill -9` fica um
  `<nome>*.tmp` na pasta (sem limpeza no código).
- Linha JSONL corrompida: não derruba a leitura, é contada (`comum.py:65-76`); testado em
  `youtube-squad/tests/test_comum.py:31-37`.
- JSON ausente ou quebrado: `padrao` (`test_comum.py:16-20`).
- Testes: `youtube-squad/tests/test_comum.py:9-60` (gravação atômica, leitura tolerante, ordem do JSONL,
  linha corrompida, arquivo ausente, `numero`, fusos); rodados nesta ingestão junto com os de apresentação
  (72 passed).

## Riscos para a nossa implementação

1. **Windows**: `fcntl` não existe; o núcleo precisa de uma trava portátil (ou `msvcrt.locking`) para o
   rastro JSONL, senão o agendador local no Windows quebra na importação.
2. **Leitura-modifica-grava sem trava** no JSON: `peca.json` é atualizado por produção, painel e agendador;
   o padrão de origem só garante que ninguém lê meio arquivo, não que duas escritas não se percam.
3. **`ensure_ascii=False` e `indent=2`** estão fixos; M16 pede UTF-8 sem BOM (atendido) e leitor que tolere
   BOM na entrada: `ler_json` usa `encoding="utf-8"`, que **não** remove BOM
   (`comum.py:24`), e o JSON com BOM cai em `ValueError` → `padrao` em silêncio.
4. **`ler_json` engole erro**: JSON corrompido vira `padrao` sem aviso; para `peca.json` isso pode esconder
   perda de dado. `apresentacao.py` contorna lendo com `json.loads` próprio e lançando `Erro`
   (`youtube-squad/apresentacao.py:55-72`).
5. **Fuso fixo em São Paulo** (`comum.py:16`) e `PACIFICO` específico do YouTube: no núcleo o fuso é da
   instalação (M5), e o dia do Pacífico é do pack do YouTube.
6. **cursos-ia não usa nada disso**: ao extrair o pipeline de aula, todas as gravações (`cues.json`,
   `legendas.json`, `demo.json`, MP3) precisam passar a escrita atômica; os scripts de origem gravam direto.

## Fonte

- `youtube-squad/comum.py`
- `youtube-squad/tests/test_comum.py`
- `youtube-squad/apresentacao.py` (uso de `comum.gravar_json`, `comum.ler_json`, `comum.agora_iso`, `comum.hoje_sp`)
- `youtube-squad/apresentacoes/decks/*/estado.json` (formato real de data)
- `cursos-ia/radar-ia-09-jev-calibracao/{gerar_voz.py, gerar_legendas.py, editar_demo.py}` (ausência do padrão)
- `ExpxMedia/docs/contrato/CONVENCOES.md` (M5, M15, M16), `ExpxMedia/docs/contrato/CONTRATO-peca.md`, `ExpxMedia/docs/contrato/CONTRATO-capacidades.md`
