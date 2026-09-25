"""Atualiza o status de uma task no YAML e na prosa de sprint-NN/tasks.md ao mesmo tempo.

Uso:
  python3 docs/nucleo-expxmedia/marcar.py T-01.01 em_andamento
  python3 docs/nucleo-expxmedia/marcar.py T-01.01 concluida "12 passed, 0 failed"
  python3 docs/nucleo-expxmedia/marcar.py T-01.01 bloqueada
"""
import datetime
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
VALIDOS = {"pendente", "em_andamento", "concluida", "bloqueada"}


def main(tid, status, resultado=None):
    assert status in VALIDOS, status
    hoje = datetime.date.today().isoformat()
    sprint = f"sprint-{tid[2:4]}"
    caminho = os.path.join(AQUI, sprint, "tasks.md")
    texto = open(caminho, encoding="utf-8").read()
    _, yaml, prosa = texto.split("---\n", 2)

    bloco = re.search(rf"  - id: {re.escape(tid)}\n(?:    .*\n|      .*\n)+", yaml)
    assert bloco, f"{tid} não encontrada no YAML de {sprint}"
    b = bloco.group(0)
    b = re.sub(r"    status: \w+", f"    status: {status}", b)
    b = re.sub(r"    concluida_em: .*", f"    concluida_em: {hoje if status == 'concluida' else 'null'}", b)
    if status == "concluida":
        b = re.sub(r"    suite: \w+", "    suite: verde", b)
    yaml = yaml.replace(bloco.group(0), b)
    yaml = re.sub(r"atualizado_em: .*", f"atualizado_em: {hoje}", yaml, count=1)

    pb = re.search(rf"```yaml\nid: {re.escape(tid)}\n.*?```", prosa, re.S)
    assert pb, f"{tid} não encontrada na prosa de {sprint}"
    p = pb.group(0)
    p = re.sub(r"status: .*", f"status: {status}", p)
    p = re.sub(r"\nconcluida: .*", "", p)
    if status == "concluida":
        p = p.replace(f"status: {status}", f"status: {status}\nconcluida: {hoje} · suíte: {resultado or 'verde'}")
    prosa = prosa.replace(pb.group(0), p)

    tmp = caminho + ".tmp"
    open(tmp, "w", encoding="utf-8").write("---\n" + yaml + "---\n" + prosa)
    os.replace(tmp, caminho)
    print(f"{tid} -> {status}")


if __name__ == "__main__":
    main(*sys.argv[1:])
