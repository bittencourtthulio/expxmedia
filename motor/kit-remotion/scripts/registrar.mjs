// Gera src/composicoes/registro.generated.ts a partir das pastas de src/composicoes/ (D-46).
//
//   node scripts/registrar.mjs
//
// Cada pasta src/composicoes/<Nome>/index.tsx exporta `composicao` com id, component, fps, width,
// height, durationInFrames, defaultProps (e, opcional, calculateMetadata). O Root importa o registro
// gerado, então uma composição nova é só uma pasta nova: nenhuma task edita o Root.
// A escrita é atômica (temporário no mesmo diretório + rename) para que execuções concorrentes
// nunca deixem o registro pela metade.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const PASTA = path.resolve(AQUI, "..", "src", "composicoes");
const DESTINO = path.join(PASTA, "registro.generated.ts");

const pastas = fs
  .readdirSync(PASTA, { withFileTypes: true })
  .filter((e) => e.isDirectory() && fs.existsSync(path.join(PASTA, e.name, "index.tsx")))
  .map((e) => e.name)
  .sort();

const linhas = [
  "// GERADO por scripts/registrar.mjs — não edite à mão. Uma composição por pasta de src/composicoes/.",
  'import type React from "react";',
  'import type { CalculateMetadataFunction } from "remotion";',
  "",
  "export type Composicao<P extends Record<string, unknown> = Record<string, unknown>> = {",
  "  id: string;",
  "  component: React.ComponentType<P>;",
  "  fps: number;",
  "  width: number;",
  "  height: number;",
  "  durationInFrames: number;",
  "  defaultProps: P;",
  "  calculateMetadata?: CalculateMetadataFunction<P>;",
  "};",
  "",
  ...pastas.map((nome, i) => `import { composicao as c${i} } from ${JSON.stringify(`./${nome}`)};`),
  "",
  "// eslint-disable-next-line @typescript-eslint/no-explicit-any",
  `export const COMPOSICOES: Composicao<any>[] = [${pastas.map((_, i) => `c${i}`).join(", ")}];`,
  "",
];

const temporario = path.join(PASTA, `.registro.${process.pid}.${Date.now()}.tmp`);
try {
  fs.writeFileSync(temporario, linhas.join("\n"), "utf8");
  fs.renameSync(temporario, DESTINO);
} finally {
  if (fs.existsSync(temporario)) fs.rmSync(temporario);
}
console.log(`registro: ${pastas.length} composição(ões) — ${pastas.join(", ") || "nenhuma"}`);
