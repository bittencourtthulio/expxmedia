# ExpxMedia

A central de mídias sociais do método Expx: instala, atualiza e diagnostica **packs** de
especialidade (Instagram, YouTube, anúncios Meta, cursos) como um plugin do Claude Code,
mantém a **Alma** da empresa e sobe o painel que mostra o andamento de tudo.

É um produto genérico: nada nele pertence a uma marca. Na primeira vez que qualquer skill
roda, o sistema cria a Alma da empresa (pelo site dela ou por entrevista) e orienta a
configuração do `.env` — e cada recurso só é habilitado quando a chave dele está lá.

> **Estado atual:** passo 0 — os contratos. Nenhum código ainda.

## Os contratos

| Documento | O que define |
|---|---|
| [`CONVENCOES.md`](docs/contrato/CONVENCOES.md) | as regras M1–M16, válidas em todo artefato |
| [`CONTRATO-alma.md`](docs/contrato/CONTRATO-alma.md) | a identidade da empresa e o portão de primeiro uso |
| [`CONTRATO-capacidades.md`](docs/contrato/CONTRATO-capacidades.md) | o que o sistema sabe fazer, quem faz e que chave habilita |
| [`CONTRATO-peca.md`](docs/contrato/CONTRATO-peca.md) | todo conteúdo produzido: post, carrossel, reel, apresentação, aula |
| [`CONTRATO-template.md`](docs/contrato/CONTRATO-template.md) | templates, galeria local e galeria compartilhada |
| [`CONTRATO-estado-eventos.md`](docs/contrato/CONTRATO-estado-eventos.md) | rastro, daily, decisões, plano do dia, relatórios |
| [`CONTRATO-pack.md`](docs/contrato/CONTRATO-pack.md) | o que um pack ou camada declara ao ser instalado |

## Ordem de construção

1. Contratos ✅
2. Núcleo (Python) — o motor com as capacidades e a produção genérica dos cinco tipos de peça, sem pack nenhum
3. Central — CLI (TypeScript, a partir do expxdev) e casca do painel
4. `expx-instagram` — o pack piloto
5. `expx-galeria` — camada, versão local
6. `expx-youtube`
7. `expx-meta`
8. `expx-cursos`
9. Galeria compartilhada (`expxmedia-gallery`)

## Licença

MIT
