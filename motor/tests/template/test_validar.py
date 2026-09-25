"""T-02.12: schema do template.json e validação dos arquivos do template (CONTRATO-template, D-36)."""
import copy
import json
from pathlib import Path

import pytest

from expxmedia.template import schema, validar

CONTRATO = Path(__file__).resolve().parents[3] / "docs" / "contrato" / "CONTRATO-template.md"


def _exemplo_contrato():
    texto = CONTRATO.read_text(encoding="utf-8")
    return json.loads(texto.split("```json", 1)[1].split("```", 1)[0])


def _template_remotion():
    dados = _exemplo_contrato()
    dados.update({
        "template_id": "reel-gancho-numerico-a1b2c3", "tipo": "reel", "motor": "remotion", "formato": "9:16",
        "canvas": {"w": 1080, "h": 1920},
    })
    dados["versoes"]["remotion"] = "4.0.290"
    dados["dependencias"] = {"remotion": "4.0.290"}
    return dados


def _pasta(tmp_path, arquivos, dados=None):
    pasta = tmp_path / "tpl"
    for nome, conteudo in arquivos.items():
        destino = pasta / nome
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(conteudo, encoding="utf-8")
    if dados is not None:
        (pasta / "template.json").write_text(json.dumps(dados), encoding="utf-8")
    return pasta


def _tipos(achados):
    return sorted(a["tipo"] for a in achados)


TSX_LIMPO = """import React from 'react';
import {AbsoluteFill, useCurrentFrame} from "remotion";
import {Audio} from '@remotion/media';
import {useAlma, useSlot} from '@expxmedia/template';
import {Cena} from './cenas/Cena';

// fetch, process e eval em comentário não contam
export const Composicao: React.FC = () => {
  const alma = useAlma();
  const frame = useCurrentFrame();
  const texto = `frame ${frame}: process eval fetch`;
  return <AbsoluteFill style={{background: alma.cores.fundo, color: 'white', borderColor: '#000'}}>
    <Cena texto={useSlot('titulo')} sombra="rgba(0, 0, 0, 0.4)" />
  </AbsoluteFill>;
};
"""


# ---------------------------------------------------------------- integração


def test_tsx_com_fs_e_css_com_url_externa_geram_um_achado_cada(tmp_path):
    pasta = _pasta(tmp_path, {
        "src/Composicao.tsx": "import fs from 'fs';\n" + TSX_LIMPO,
        "src/cenas/Cena.tsx": "import React from 'react';\nexport const Cena = (p: any) => <div>{p.texto}</div>;\n",
        "template.css": ":root { --cor-fundo: var(--alma-fundo); }\n"
                        ".capa { background: url(https://externo.example/fundo.png) no-repeat; color: var(--cor-fundo); }\n",
    }, _template_remotion())
    achados = validar.validar_template(pasta, modo="template")
    assert _tipos(achados) == ["import_proibido", "url_externa"]
    por_tipo = {a["tipo"]: a for a in achados}
    assert por_tipo["import_proibido"]["arquivo"] == "src/Composicao.tsx"
    assert por_tipo["import_proibido"]["linha"] == 1
    assert "fs" in por_tipo["import_proibido"]["detalhe"]
    assert por_tipo["url_externa"]["arquivo"] == "template.css" and por_tipo["url_externa"]["linha"] == 2


def test_template_limpo_nao_tem_achado(tmp_path):
    pasta = _pasta(tmp_path, {
        "src/Composicao.tsx": TSX_LIMPO,
        "src/cenas/Cena.tsx": "export const Cena = (p: any) => null;\n",
        "template.css": "@import url('https://fonts.googleapis.com/css2?family=Inter');\n"
                        ":root { --cor-destaque: var(--alma-destaque); --brilho: #ff0000; }\n"
                        ".a { color: var(--cor-destaque); background: color-mix(in srgb, var(--alma-destaque) 20%, white); "
                        "border: 1px solid #FFF; box-shadow: 0 0 4px rgba(0,0,0,.3); outline-color: transparent; }\n",
        "slides/capa.html": "<link rel=\"stylesheet\" href=\"https://fonts.googleapis.com/css2?family=Inter\">"
                            "<img src=\"assets/malha.svg\"><a href=\"https://externo.example\">link não carrega</a>"
                            "<div style=\"color: black\">{{titulo}}</div>",
    }, _template_remotion())
    assert validar.validar_template(pasta, modo="template") == []


@pytest.mark.parametrize("codigo,tipo", [
    ("import {x} from 'child_process';", "import_proibido"),
    ("import * as n from 'node:net';", "import_proibido"),
    ("import http from 'http';", "import_proibido"),
    ("export {get} from 'https';", "import_proibido"),
    ("import 'lodash';", "import_proibido"),
    ("const r = require('fs/promises');", "import_proibido"),
    ("const m = require(nome);", "api_proibida"),
    ("const m = await import('remotion');", "api_proibida"),
    ("fetch('/x');", "api_proibida"),
    ("const r = window.fetch;", "api_proibida"),
    ("new XMLHttpRequest();", "api_proibida"),
    ("const w = new WebSocket(u);", "api_proibida"),
    ("eval('1+1');", "api_proibida"),
    ("const f = new Function('return 1');", "api_proibida"),
    ("const v = process.env.CHAVE;", "api_proibida"),
    ("const g = globalThis['fetch'];", "api_proibida"),
    ("const t = `${fetch}`;", "api_proibida"),
    ("const u = 'https://cdn.externo.example/x.png';", "url_externa"),
])
def test_codigo_proibido_no_tsx(codigo, tipo):
    achados = validar.validar_codigo(codigo + "\n", arquivo="src/X.tsx", modo="template")
    assert [a["tipo"] for a in achados] == [tipo], achados


def test_import_extra_so_com_dependencia_e_lista_da_galeria(tmp_path):
    codigo = "import {motion} from 'framer-motion';\n"
    assert _tipos(validar.validar_codigo(codigo, arquivo="a.tsx")) == ["import_proibido"]
    assert _tipos(validar.validar_codigo(codigo, arquivo="a.tsx", permitidos={"framer-motion"})) == []
    dados = _template_remotion()
    pasta = _pasta(tmp_path, {"src/Composicao.tsx": codigo}, dados)
    # na lista da galeria mas fora de dependencias: continua proibido
    assert _tipos(validar.validar_template(pasta, permitidos_galeria={"framer-motion"})) == ["import_proibido"]
    dados["dependencias"]["framer-motion"] = "11.0.0"
    (pasta / "template.json").write_text(json.dumps(dados), encoding="utf-8")
    assert validar.validar_template(pasta, permitidos_galeria={"framer-motion"}) == []
    assert _tipos(validar.validar_template(pasta)) == ["import_proibido"]


def test_import_relativo_nao_sai_da_pasta_do_template(tmp_path):
    pasta = _pasta(tmp_path, {"src/Composicao.tsx": "import x from '../../fora/segredo';\n"}, _template_remotion())
    assert _tipos(validar.validar_template(pasta)) == ["import_proibido"]


# ---------------------------------------------------------------- funcional


def test_cor_literal_fora_de_root_so_no_modo_template():
    css = ":root { --cor: #ff0000; }\n.titulo { color: #ff0000; }\n"
    achados = validar.validar_css(css, arquivo="template.css", modo="template")
    assert [(a["tipo"], a["linha"]) for a in achados] == [("cor_literal", 2)]
    assert "#ff0000" in achados[0]["detalhe"]
    assert validar.validar_css(css, arquivo="template.css", modo="sob_medida") == []


@pytest.mark.parametrize("valor", ["#f00", "#FF000080", "rgb(255, 0, 0)", "hsl(0 100% 50%)", "tomato",
                                   "oklch(0.6 0.2 30)", "linear-gradient(red, blue)"])
def test_cores_literais_detectadas(valor):
    css = f".a {{ background: {valor}; }}"
    assert _tipos(validar.validar_css(css, arquivo="t.css", modo="template")) == ["cor_literal"]


@pytest.mark.parametrize("valor", ["black", "white", "transparent", "#000", "#FFFFFF", "#00000080", "rgba(255,255,255,0.5)",
                                   "var(--alma-destaque)", "currentColor", "'Red Hat Display', sans-serif"])
def test_preto_branco_transparente_e_tokens_permitidos(valor):
    css = f".a {{ color: {valor}; font-family: 'Red Hat Display'; }}"
    assert validar.validar_css(css, arquivo="t.css", modo="template") == []


def test_media_query_com_root_e_regra_dentro():
    css = "@media (min-width: 10px) {\n  :root { --x: #123456; }\n  .a { color: #123456; }\n}\n"
    assert [a["linha"] for a in validar.validar_css(css, arquivo="t.css", modo="template")] == [3]


def test_cor_literal_no_tsx_e_no_html_so_no_modo_template():
    tsx = "export const A = () => <div style={{color: '#1E5EFF'}} />;\n"
    html = "<div style=\"color: #1E5EFF\"><svg><rect fill=\"#1E5EFF\"/></svg></div>"
    assert _tipos(validar.validar_codigo(tsx, arquivo="a.tsx", modo="template")) == ["cor_literal"]
    assert validar.validar_codigo(tsx, arquivo="a.tsx", modo="sob_medida") == []
    assert _tipos(validar.validar_html(html, arquivo="s.html", modo="template")) == ["cor_literal", "cor_literal"]
    assert validar.validar_html(html, arquivo="s.html", modo="sob_medida") == []


def test_sob_medida_mantem_imports_apis_e_rede():
    """D-36: o código por referência pode usar cor literal, mas as outras regras valem igual."""
    tsx = "import fs from 'fs';\nconst c = '#ABCDEF';\nfetch('/x');\n"
    assert _tipos(validar.validar_codigo(tsx, arquivo="a.tsx", modo="sob_medida")) == ["api_proibida", "import_proibido"]
    css = ".a { color: #abcdef; background: url(//externo.example/a.png); }"
    assert _tipos(validar.validar_css(css, arquivo="t.css", modo="sob_medida")) == ["url_externa"]


def test_modo_desconhecido_e_recusado():
    with pytest.raises(ValueError):
        validar.validar_css("", arquivo="t.css", modo="livre")


# ---------------------------------------------------------------- schema


def test_exemplo_do_contrato_valida():
    assert schema.validar(_exemplo_contrato()) == []
    assert schema.validar(_template_remotion()) == []


def test_schema_aponta_chave_omitida_e_valores_fora():
    dados = _exemplo_contrato()
    del dados["kinds"]["numero"]["slots"]["numero"]["max"]
    del dados["compartilhamento"]
    dados["tokens"].append("azul")
    caminhos = {(v["tipo"], v["caminho"]) for v in schema.validar(dados)}
    assert ("chave_omitida", "kinds.numero.slots.numero.max") in caminhos
    assert ("chave_omitida", "compartilhamento") in caminhos
    assert ("valor_invalido", "tokens[7]") in caminhos


def test_schema_coerencia_tipo_formato_motor():
    dados = copy.deepcopy(_exemplo_contrato())
    dados["formato"] = "9:16"  # carrossel não é 9:16
    assert ("valor_invalido", "formato") in {(v["tipo"], v["caminho"]) for v in schema.validar(dados)}
    dados = _template_remotion()
    dados["versoes"]["remotion"] = None  # motor remotion trava a versão
    assert ("valor_invalido", "versoes.remotion") in {(v["tipo"], v["caminho"]) for v in schema.validar(dados)}
    dados = _exemplo_contrato()
    dados["template_id"] = "Carrossel Azul"
    assert ("valor_invalido", "template_id") in {(v["tipo"], v["caminho"]) for v in schema.validar(dados)}


def test_schema_rejeita_versao_maior():
    dados = _exemplo_contrato()
    dados["expxmedia_template"] = 2
    with pytest.raises(schema.ErroTemplateRejeitado):
        schema.validar(dados)


def test_template_json_invalido_entra_como_achado(tmp_path):
    dados = _template_remotion()
    del dados["requisitos"]
    pasta = _pasta(tmp_path, {"src/Composicao.tsx": TSX_LIMPO,
                              "src/cenas/Cena.tsx": "export const Cena = () => null;\n"}, dados)
    achados = validar.validar_template(pasta)
    assert [(a["tipo"], a["arquivo"]) for a in achados] == [("chave_omitida", "template.json")]
    assert "requisitos" in achados[0]["detalhe"]


@pytest.mark.parametrize("html,n", [
    ('<link rel="stylesheet" href="https://cdn.externo.example/x.css">', 1),
    ('<img src="http://externo.example/a.png">', 1),
    ('<img srcset="a.png 1x, https://externo.example/b.png 2x">', 1),
    ('<style>\n.a { background: url("//externo.example/a.png"); }\n</style>', 1),
    ('<a href="https://externo.example">não carrega</a><img src="data:image/png;base64,AAAA">', 0),
])
def test_urls_do_html(html, n):
    achados = validar.validar_html(html, arquivo="s.html", modo="sob_medida")
    assert [a["tipo"] for a in achados] == ["url_externa"] * n
