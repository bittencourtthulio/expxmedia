"""Runner do Remotion: render e still de UMA composição do kit, em qualquer versão travada (D-17, D-46).

Porta de `Instragram-Videos/pipeline/render_remotion.py` (`npx remotion render ... --codec=h264 --log=error`,
tempo limite de 1800 s, erro com o fim da saída), com três mudanças:

1. **Entry point próprio por render.** A origem fazia bundle de `src/index.ts`, que importa TODAS as
   composições: uma pasta quebrada derrubava o render de todas. Aqui cada render grava um entry temporário em
   `<projeto>/out/entradas/<id>/` que registra só a composição pedida (`src/composicoes/<Nome>/index.tsx`,
   id = nome da pasta) e é apagado no fim. `out/` já é ignorado pelo versionador.
2. **Multi-versão.** A 4.0.528 usa o próprio kit (`motor/kit-remotion`). Outra versão usa um projeto por versão
   num cache fora da instalação (`$XDG_CACHE_HOME/expxmedia/remotion/<versao>` ou
   `~/.cache/expxmedia/remotion/<versao>`). Este módulo só **resolve** esse diretório: se o projeto da versão
   não estiver preparado, o render para com erro dizendo isso. Nada aqui instala pacote.
3. **Browser compartilhado.** O chrome-headless-shell baixado uma vez no kit (T-01.08) é passado a todo render
   com `--browser-executable`, inclusive das outras versões, para nenhuma baixar o seu.

Props vão sempre por arquivo JSON (`--props=<arquivo>`; JSON inline quebra no Windows). Mídia e fontes das
props são servidas pelo `public_dir` (`--public-dir`), com caminhos relativos a ele (M9).

Uso:

    from expxmedia.motion import remotion
    remotion.renderizar("Vazio", "saida.mp4", {"duracaoFrames": 60})
    remotion.stills("TesteSelo", [10, 40], "pasta/", props, escala=0.3, public_dir="publico/")
"""
from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any, Iterator

__all__ = [
    "ErroRemotion",
    "VERSAO_KIT",
    "TEMPO_RENDER_S",
    "TEMPO_STILL_S",
    "KIT",
    "cache_versoes",
    "diretorio_projeto",
    "projeto_pronto",
    "navegador_compartilhado",
    "entrada_temporaria",
    "renderizar",
    "stills",
]

VERSAO_KIT = "4.0.528"  # D-17
TEMPO_RENDER_S = 1800  # origem: Instragram-Videos/pipeline/render_remotion.py:31
TEMPO_STILL_S = 600  # origem: Instragram-Videos/pipeline/render_remotion.py:191
FIM_DA_SAIDA = 1500  # origem: Instragram-Videos/pipeline/render_remotion.py:172 (últimos 1500 caracteres)
KIT = Path(__file__).resolve().parents[3] / "kit-remotion"

_RE_VERSAO = re.compile(r"^\d+\.\d+\.\d+$")
_RE_NOME = re.compile(r"^[A-Za-z0-9_-]+$")
_CLI = Path("node_modules") / "@remotion" / "cli" / "remotion-cli.js"


class ErroRemotion(RuntimeError):
    """Falha de render, de still ou de preparo do projeto Remotion."""


# ---------------------------------------------------------------- projeto por versão


def cache_versoes() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "expxmedia" / "remotion"


def diretorio_projeto(versao: str = VERSAO_KIT, cache: Path | str | None = None) -> Path:
    """Projeto Remotion que renderiza a `versao`: o kit na 4.0.528; senão `<cache>/<versao>` (não cria nada)."""
    if not isinstance(versao, str) or not _RE_VERSAO.match(versao):
        raise ValueError(f"versão do Remotion inválida: {versao!r} (use a versão exata, ex.: {VERSAO_KIT})")
    if versao == VERSAO_KIT:
        return KIT
    return (Path(cache) if cache is not None else cache_versoes()) / versao


def _versao_instalada(projeto: Path, pacote: str) -> str | None:
    manifesto = projeto / "node_modules" / pacote / "package.json"
    try:
        return json.loads(manifesto.read_text(encoding="utf-8")).get("version")
    except (OSError, ValueError):
        return None


def projeto_pronto(projeto: Path | str, versao: str | None = None) -> bool:
    """O projeto tem o CLI do Remotion instalado (e, se pedida, na `versao` exata de remotion e @remotion/cli)."""
    projeto = Path(projeto)
    if not (projeto / _CLI).is_file():
        return False
    if versao is None:
        return True
    return _versao_instalada(projeto, "remotion") == versao and _versao_instalada(projeto, "@remotion/cli") == versao


def navegador_compartilhado(kit: Path | str = KIT) -> Path | None:
    """chrome-headless-shell baixado pelo Remotion no kit (T-01.08), ou None."""
    base = Path(kit) / "node_modules" / ".remotion" / "chrome-headless-shell"
    if not base.is_dir():
        return None
    for candidato in sorted(base.rglob("chrome-headless-shell*")):
        if candidato.is_file() and candidato.name in ("chrome-headless-shell", "chrome-headless-shell.exe"):
            return candidato
    return None


def _resolver_projeto(versao: str, projeto: Path | str | None, cache: Path | str | None) -> Path:
    if projeto is not None:
        projeto = Path(projeto)
        if not projeto_pronto(projeto):
            raise ErroRemotion(f"projeto Remotion sem node_modules/@remotion/cli: {projeto}")
        return projeto
    dir_versao = diretorio_projeto(versao, cache)
    if not projeto_pronto(dir_versao, versao):
        if dir_versao == KIT:
            raise ErroRemotion(f"o kit Remotion não está instalado na {VERSAO_KIT} em {KIT}: rode a preparação do ambiente")
        raise ErroRemotion(
            f"a versão {versao} do Remotion não está preparada em {dir_versao}: prepare o projeto dessa versão "
            f"(package.json com remotion e @remotion/cli {versao} e npm ci) antes de renderizar"
        )
    return dir_versao


# ---------------------------------------------------------------- entry point próprio


def _modulo_composicao(projeto: Path, composicao: str) -> Path:
    if not isinstance(composicao, str) or not _RE_NOME.match(composicao):
        raise ValueError(f"nome de composição inválido: {composicao!r} (é o nome da pasta em src/composicoes)")
    modulo = projeto / "src" / "composicoes" / composicao / "index.tsx"
    if not modulo.is_file():
        raise ErroRemotion(f"composição {composicao} não existe: falta {modulo}")
    return modulo


def _texto_entrada(composicao: str) -> str:
    return (
        "// GERADO pelo runner (expxmedia.motion.remotion) para um render só; apagado no fim.\n"
        'import React from "react";\n'
        'import { Composition, registerRoot } from "remotion";\n'
        f'import {{ composicao as c }} from "../../../src/composicoes/{composicao}/index";\n'
        "\n"
        "const Raiz: React.FC = () => (\n"
        "  <Composition\n"
        f"    id={json.dumps(composicao)}\n"
        "    component={c.component}\n"
        "    fps={c.fps}\n"
        "    width={c.width}\n"
        "    height={c.height}\n"
        "    durationInFrames={c.durationInFrames}\n"
        "    defaultProps={c.defaultProps}\n"
        "    calculateMetadata={c.calculateMetadata}\n"
        "  />\n"
        ");\n"
        "\n"
        "registerRoot(Raiz);\n"
    )


@contextlib.contextmanager
def entrada_temporaria(projeto: Path | str, composicao: str) -> Iterator[Path]:
    """Grava `<projeto>/out/entradas/<id>/entrada.tsx` registrando só `composicao`; apaga ao sair."""
    projeto = Path(projeto)
    _modulo_composicao(projeto, composicao)
    pasta = projeto / "out" / "entradas" / f"{composicao}-{uuid.uuid4().hex[:12]}"
    pasta.mkdir(parents=True)
    try:
        entrada = pasta / "entrada.tsx"
        entrada.write_text(_texto_entrada(composicao), encoding="utf-8")
        yield entrada
    finally:
        shutil.rmtree(pasta, ignore_errors=True)


# ---------------------------------------------------------------- execução


def _node() -> str:
    node = shutil.which("node")
    if node is None:
        raise ErroRemotion("node não encontrado no PATH (o Remotion exige Node)")
    return node


def _base(projeto: Path, comando: str) -> list[str]:
    return [_node(), str(projeto / _CLI), comando]


def _opcoes(props_arquivo: Path | None, public_dir: Path | str | None) -> list[str]:
    opcoes = ["--log=error"]
    if props_arquivo is not None:
        opcoes.append(f"--props={props_arquivo}")
    if public_dir is not None:
        opcoes.append(f"--public-dir={Path(public_dir).resolve()}")
    navegador = navegador_compartilhado()
    if navegador is not None:
        opcoes.append(f"--browser-executable={navegador}")
    return opcoes


def _rodar(cmd: list[str], cwd: Path, timeout: float, o_que: str) -> None:
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise ErroRemotion(f"{o_que} passou do tempo limite de {timeout:.0f} s") from e
    if r.returncode:
        raise ErroRemotion(f"{o_que} falhou:\n{((r.stdout or '') + (r.stderr or ''))[-FIM_DA_SAIDA:]}")


def _gravar_props(pasta: Path, props: dict[str, Any] | None) -> Path | None:
    if props is None:
        return None
    if not isinstance(props, dict):
        raise ValueError("props do Remotion precisam ser um objeto JSON")
    arquivo = pasta / "props.json"
    arquivo.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    return arquivo


def renderizar(
    composicao: str,
    saida: Path | str,
    props: dict[str, Any] | None = None,
    *,
    versao: str = VERSAO_KIT,
    projeto: Path | str | None = None,
    cache: Path | str | None = None,
    public_dir: Path | str | None = None,
    codec: str = "h264",
    timeout: float = TEMPO_RENDER_S,
) -> Path:
    """Renderiza `composicao` (pasta de src/composicoes) em `saida`, com props JSON, e devolve o caminho."""
    raiz = _resolver_projeto(versao, projeto, cache)
    saida = Path(saida).resolve()
    saida.parent.mkdir(parents=True, exist_ok=True)
    with entrada_temporaria(raiz, composicao) as entrada:
        arq_props = _gravar_props(entrada.parent, props)
        cmd = [*_base(raiz, "render"), str(entrada), composicao, str(saida), f"--codec={codec}",
               *_opcoes(arq_props, public_dir)]
        _rodar(cmd, raiz, timeout, f"render do Remotion ({composicao})")
    if not saida.is_file():
        raise ErroRemotion(f"render do Remotion ({composicao}) terminou sem gerar {saida}")
    return saida


def stills(
    composicao: str,
    quadros: list[int],
    pasta: Path | str,
    props: dict[str, Any] | None = None,
    *,
    escala: float = 1.0,
    nomes: list[str] | None = None,
    versao: str = VERSAO_KIT,
    projeto: Path | str | None = None,
    cache: Path | str | None = None,
    public_dir: Path | str | None = None,
    timeout: float = TEMPO_STILL_S,
) -> list[Path]:
    """Um PNG por quadro de `quadros`, com um bundle só (a origem refazia o bundle a cada still)."""
    raiz = _resolver_projeto(versao, projeto, cache)
    pasta = Path(pasta).resolve()
    pasta.mkdir(parents=True, exist_ok=True)
    nomes = nomes or [f"quadro-{q:06d}.png" for q in quadros]
    if len(nomes) != len(quadros):
        raise ValueError("nomes e quadros precisam ter o mesmo tamanho")
    feitos: list[Path] = []
    with entrada_temporaria(raiz, composicao) as entrada:
        arq_props = _gravar_props(entrada.parent, props)
        bundle = entrada.parent / "bundle"
        cmd = [*_base(raiz, "bundle"), str(entrada), f"--out-dir={bundle}", "--log=error"]
        if public_dir is not None:
            cmd.append(f"--public-dir={Path(public_dir).resolve()}")
        _rodar(cmd, raiz, timeout, f"bundle do Remotion ({composicao})")
        for quadro, nome in zip(quadros, nomes):
            png = pasta / nome
            cmd = [*_base(raiz, "still"), str(bundle), composicao, str(png), f"--frame={int(quadro)}",
                   f"--scale={escala}", *_opcoes(arq_props, None)]
            _rodar(cmd, raiz, timeout, f"still do quadro {quadro} ({composicao})")
            if not png.is_file():
                raise ErroRemotion(f"still do quadro {quadro} ({composicao}) terminou sem gerar {png}")
            feitos.append(png)
    return feitos
