"""Marca sprint.md e fases.md de uma sprint como concluídos (YAML e atualizado_em)."""
import datetime, re, sys, os
n = sys.argv[1]; d = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"sprint-{n}")
hoje = datetime.date.today().isoformat()
for arq in ("sprint.md", "fases.md"):
    p = os.path.join(d, arq); s = open(p, encoding="utf-8").read()
    _, y, prosa = s.split("---\n", 2)
    y = re.sub(r"status: \w+", "status: concluido", y)
    y = re.sub(r"atualizado_em: .*", f"atualizado_em: {hoje}", y)
    open(p, "w", encoding="utf-8").write("---\n" + y + "---\n" + prosa)
print(f"sprint-{n} concluida")
