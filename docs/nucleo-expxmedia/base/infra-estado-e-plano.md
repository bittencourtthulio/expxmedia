# Infraestrutura de estado, plano do dia, validação de contrato e padrão de painel

Padrões que o núcleo herda para cumprir `ExpxMedia/docs/contrato/CONTRATO-estado-eventos.md` e as
regras M7, M10, M14 e M15 de `ExpxMedia/docs/contrato/CONVENCOES.md`: JSONL só-acréscimo com trava,
plano do dia em JSON + Markdown, trava de execução, validação por JSON Schema e o painel local com
token. Fontes: `Instagram-Carrosseis` (`daily.py`, `planejar.py`, `rotina.sh`) e `ExpxMeta`
(`estado.py`, `contratos/validar.py`, `painel.py`). Não existe `estado.py` em `Instagram-Carrosseis`;
o módulo de estado reutilizável é o do `ExpxMeta`.

## Contrato de entrada

**JSONL com trava** (`ExpxMeta/estado.py`)
- `acrescentar(caminho, evento, rotular_quando=True)` grava uma linha JSON com `fcntl.flock(LOCK_EX)` e `flush` (`ExpxMeta/estado.py:22-36`).
- Por padrão embrulha: `{"quando": <ISO com fuso>, "evento": {...}}` (`estado.py:31`); `rotular_quando=False` grava o objeto como veio.
- `eventos(caminho)` lê tudo; arquivo inexistente é `[]` (`estado.py:39-45`).
- Hora: `datetime.now().astimezone().isoformat(timespec="seconds")` — fuso da máquina (`estado.py:18-19`; igual em `Instagram-Carrosseis/daily.py:64-65`).

**Daily com trava e leitura sob trava** (`Instagram-Carrosseis/daily.py:75-85`)
- Abre em `a+`, trava, relê o arquivo inteiro, a função `monta(ja)` calcula o evento (ex.: próximo id `d<NNN>` contando eventos `novo`, `daily.py:162-166`) e acrescenta. Isso dá id sequencial sem corrida.
- Tipos de item e estados: `tarefa` (aberta → fazendo → feita|recusada|cancelada), `pergunta`, `nao-fazer`, `aprendizado` (`daily.py:8-12,42-47`).
- Campos gravados observados na última linha de `estado/daily.jsonl`: `autor`, `evento`, `id`, `onde`, `quando`, `status`, `texto`; e em `estado/decisoes.jsonl`: `autor`, `como_desfazer`, `evidencia`, `o_que`, `por_que`, `quando`, `tipo` (leitura de chaves, 2026-09-24).

**Plano do dia** (`Instagram-Carrosseis/planejar.py`)
- Regras vêm de `editorial/cadencia.json` sobre um padrão embutido (`planejar.py:39-46,53-55`), p. ex. `max_posts_feed_dia` 3, `max_por_serie_dia` 1, `nota_minima` 4.0, `antecedencia_min` 30, `publicacao_automatica` false, `trava_expira_min` 50, `max_reels_dia` 2, horários fixos de feed e de reel (`planejar.py:40-44`).
- Plano gravado em `planejamento/AAAA-MM-DD.json` e `.md` derivado (`planejar.py:69-72`); chaves de topo: `data`, `gerado_em`, `analise_base`, `regras`, `resumo`, `vagas`, `teste_do_dia`, `fila_expx_flow`, `recomendacao_para_a_fila`, `fora_do_plano`, `notas_do_analista`, `cruzamento_com_o_cerebro` (`planejar.py:550-565`).
- Chaves de vaga observadas: `id`, `hora`, `serie`, `item`, `modo`, `fixa`, `formato`, `guia`, `requer`, `ler_antes`, `motivo`, `status`, `scheduled_post_id`, `agendado_para`, `atualizado_em`, `pasta`, `nome`, `titulo` (leitura de `planejamento/2026-09-24.json`).
- `pendentes()` percorre todos os planos de hoje em diante; vaga de dia passado vira `perdido`; vaga atrasada é empurrada (≥ `antecedencia_min`, espaçamento de 1 h, múltiplo de 5 min, até 22:30) (`planejar.py:584-637`).
- `comandos()` monta, por vaga, o `--dry-run` e — só se `publicacao_automatica` — o comando real com `--chave-idempotencia plano-...` (`planejar.py:640-652`).
- A fila do provedor é reconstruída dos **logs locais de envio**, não da API (`planejar.py:75-86`).

**Validação de contrato**
- `ExpxMeta/contratos/validar.py`: registro `SCHEMAS` tipo → arquivo, cache, `jsonschema.Draft7Validator`, erro nomeando o caminho do campo (`validar.py:19-52`); API `dados(dict, tipo) -> (ok, erros)` e `arquivo(Path, tipo)`.
- `Instagram-Carrosseis/publicar/contratos.py`: `Draft202012Validator` com `FormatChecker`, injeta o schema de automação no lugar do `$ref` (`contratos.py:92-124`).

**Painel local** (`ExpxMeta/painel.py`, "padrão da central Instagram", `painel.py:6-7`)
- Escuta só em `127.0.0.1`, porta padrão 8765 ou 0 (livre) (`painel.py:47,160-161,461`).
- Recusa `Host` fora de `127.0.0.1`, `localhost`, `[::1]` com 403 (`painel.py:57-59,70-71,111-112`).
- Token de escrita por processo `secrets.token_urlsafe(24)` injetado na página e exigido em toda escrita em `X-Painel-Token` ou `X-CSRF-Token` (`painel.py:51,75,115-117,129-131`).

## Contrato de saída

- JSONL: uma linha por evento, nunca reescrita (M15). Formato da origem difere do contrato: `ExpxMeta` embrulha em `quando`/`evento`; o contrato exige doze chaves planas com `ts` primeiro (`CONTRATO-estado-eventos.md:39-47`).
- Plano: JSON indentado (`indent=1`) + Markdown gerado a partir do JSON (`planejar.py:71-72`), coerente com M1 e com a regra 4 do plano (`CONTRATO-estado-eventos.md:182`).
- Status de vaga na origem: `pendente`, `produzindo`, `produzido`, `agendado`, `falhou`, `perdido`, `pulado` (`planejar.py:19,757`). No contrato: `pendente`, `produzindo`, `produzida`, `agendada`, `publicada`, `falhou`, `cancelada` (`CONTRATO-estado-eventos.md:172`).
- Validação: lista de mensagens `"<caminho>: <mensagem>"`; nunca exceção por dado inválido (`validar.py:43-52`; `contratos.py:100-109`).

## Limites e cotas

| Item | Valor | Fonte |
|---|---|---|
| Trava de execução do plano | expira em 50 min | `planejar.py:43,655-660` |
| Trava da rotina (cron) | expira em 120 min | `Instagram-Carrosseis/rotina.sh:46-48` |
| Tentativas por vaga que falhou | 2 (`MAX_TENTATIVAS`) | `planejar.py:584,588-589` |
| Último horário para empurrar vaga | 22:30 | `planejar.py:585` |
| Fila de testes | 10 (`MAX_NA_FILA`) | `planejar.py:252` |
| Título de item da daily | 120 caracteres | `daily.py:152-153` |
| Portabilidade da trava | `fcntl` é só POSIX (Unix); Windows: NÃO DOCUMENTADO na origem | `estado.py:12`; `daily.py:33` |

## Erros conhecidos e tratamento

- Plano ausente: `SystemExit` com instrução de rodar `criar` (`planejar.py:62-66`).
- Trava viva: `travar()` devolve `False` e a execução não começa (`planejar.py:655-660`); `liberar` solta a trava de processo morto (`planejar.py:14`).
- Registro de automação com versão diferente de 1: `sys.exit` (`Instagram-Carrosseis/publicar/publicar.py:184-185`) — comportamento compatível com M2.
- Tipo de contrato desconhecido: `ErroContrato` (`validar.py:31-37`).
- Painel: `403` para host inválido e token ausente ou errado (`painel.py:70-71,115-117`).

## Riscos para a nossa implementação

1. **Escrita não atômica de JSON**: `planejar.salvar` usa `write_text` direto (`planejar.py:69-72`); o log de publicações e `uploads.json` também (`publicar.py:148,290`). M15 exige temporário na mesma pasta + `rename`; o padrão correto já existe em `publicar.py:236-239`.
2. **`fcntl` não existe no Windows**; o contrato promete agendador no Windows (`CONTRATO-capacidades.md:75`). A trava de JSONL do núcleo precisa de alternativa (ex.: `msvcrt.locking`) — NÃO DOCUMENTADO na origem.
3. **Forma do evento diverge do contrato** (embrulho `quando`/`evento` vs doze chaves planas com `ts`); o validador deve checar que as doze estão **contidas**, não igualdade de conjunto (`CONTRATO-estado-eventos.md:47-50`).
4. **Dois dialetos de JSON Schema** (Draft 7 no ExpxMeta, 2020-12 nos carrosséis): escolher um para os schemas do núcleo.
5. **Enums de status diferentes** (masculino/sem `publicada`/com `perdido` e `pulado` na origem): a migração de planos antigos precisa de tabela de tradução.
6. **Fila do provedor por log local**: publicação feita pela tela do provedor, ou envio sem log, não entra na contagem do limite diário (`planejar.py:75-86`). No núcleo a fonte são os `peca.json.publicacoes[]`.
7. **Reagendamento automático de vaga atrasada** (`planejar.py:592-609`) é permitido para o `expxflow` (o servidor agenda), mas conflita com a regra de não publicar atrasado do agendador local (`CONTRATO-capacidades.md:84-85`).
8. **Hora pelo fuso da máquina** (`estado.py:18-19`; `daily.py:64-65`); M5 pede o fuso da Alma.
9. **Painel compara token com `!=`** (`painel.py:115-116,129-130`), não com comparação de tempo constante; risco baixo por ser só `127.0.0.1`, mas o núcleo pode usar `secrets.compare_digest`.
10. **Acoplamentos de pessoa/marca** a tirar (M13): `THULIO = "thulio"` e papéis exclusivos dele (`daily.py:2,43-53`); docstring de `ja_agendados` (`planejar.py:76-77`); lista `PARA` com nomes de agentes do pack de carrosséis (`daily.py:48`); horários padrão de publicação (`planejar.py:41,44`) → cadência do pack.

## Fonte

- `ExpxMeta/estado.py:1-45`
- `ExpxMeta/contratos/validar.py:1-57`
- `ExpxMeta/painel.py:1-160,441-467` (só padrão de token e host)
- `Instagram-Carrosseis/daily.py:1-172`
- `Instagram-Carrosseis/planejar.py:1-86,546-660`
- `Instagram-Carrosseis/rotina.sh:41-62`
- `Instagram-Carrosseis/publicar/contratos.py:92-124`; `Instagram-Carrosseis/publicar/publicar.py:179-239,276-291`
- `Instagram-Carrosseis/estado/daily.jsonl`, `estado/decisoes.jsonl`, `planejamento/2026-09-24.json` (só nomes de chave)
- `ExpxMedia/docs/contrato/CONTRATO-estado-eventos.md`, `CONVENCOES.md`
