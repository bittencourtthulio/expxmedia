---
expx_schema: 1
expx_tool: sprintx
kind: bloqueios
trabalho_id: nucleo-expxmedia
atualizado_em: 2026-09-25
bloqueios:
  - id: B-01
    task: T-01.03
    aberto_em: 2026-09-24
    resolvido_em: 2026-09-24
    descricao: uv resolveu opencv-python-headless 5 que removeu CascadeClassifier; resolvido fixando opencv>=4.8,<5 no pyproject
  - id: B-02
    task: T-10.02
    aberto_em: 2026-09-25
    resolvido_em: 2026-09-25
    descricao: Aviso de escolha implicita de provedor existe no verificador mas nao chega a saida de publicar e agendar
---

# Bloqueios

B-01 | T-01.03 | uv resolveu opencv-python-headless 5.0, que removeu cv2.CascadeClassifier (usado também por cut.py e abertura.py da origem) | RESOLVIDO pelo orquestrador: `opencv-python-headless>=4.8,<5` em motor/pyproject.toml e uv.lock regerado (OpenCV 4.14.0)
B-02 | T-10.02 | `Verificador.aviso()` existe mas publicar/agendar não devolvem o aviso de escolha implícita exigido pelo CONTRATO-capacidades (regra 2) | RESOLVIDO: `avisos` no retorno de publicar/base.py (dry-run e envio) e `aviso` por capacidade em `capacidades`; test_publicacao.py passa sem mudança
