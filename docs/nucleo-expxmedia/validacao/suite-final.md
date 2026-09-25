# Suíte final — nucleo-expxmedia

Data: 2026-09-25 · máquina: macOS (Apple Silicon), Python 3.11, Node 20.20.1, ffmpeg 8.0.1

## Suíte inteira

```
$ cd motor && uv run pytest -q -rs
........................................................................ [ 95%]
...................................................                      [100%]
1131 passed in 1554.04s (0:25:54)
```

0 failed, 0 skipped.

## Varredura de marca (M13)

```
$ cd motor && uv run pytest tests/test_marca.py -q
7 passed in 0.86s
```

Raízes varridas: `motor/src`, `motor/kit-remotion/src`, `motor/kit-remotion/scripts`, `nucleo/`, `templates/`. Nenhum termo proibido.

## Plugin

```
$ claude plugin validate nucleo
✔ Validation passed
```
