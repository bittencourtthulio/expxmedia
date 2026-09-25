"""Fixture `instalacao`: uma instalação do ExpxMedia em pasta temporária, com a Alma fictícia (D-02).

A raiz devolvida tem:
  alma/      cópia de tests/fixtures/alma-ficticia/alma (alterar a cópia não toca a fixture)
  pecas/     vazia
  estado/    vazia
  eventos/   vazia
  .env       vazio (o portão do ambiente só exige que exista; nenhuma chave, D-15)
"""
import shutil
from pathlib import Path

import pytest

ALMA_FICTICIA = Path(__file__).resolve().parent / "alma-ficticia" / "alma"
PASTAS = ("pecas", "estado", "eventos")


def montar_instalacao(raiz: Path) -> Path:
    raiz.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ALMA_FICTICIA, raiz / "alma")
    for pasta in PASTAS:
        (raiz / pasta).mkdir()
    (raiz / ".env").write_bytes(b"")
    return raiz


@pytest.fixture
def instalacao(tmp_path) -> Path:
    return montar_instalacao(tmp_path / "instalacao")
