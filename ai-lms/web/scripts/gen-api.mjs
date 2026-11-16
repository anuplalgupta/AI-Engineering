// Regenerates src/api/schema.gen.ts from the backend OpenAPI file.
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const webDir = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const input = resolve(webDir, "..", "backend", "openapi.json");
const output = resolve(webDir, "src", "api", "schema.gen.ts");

if (!existsSync(input)) {
  console.error(`gen:api failed: ${input} does not exist.`);
  console.error("Export the OpenAPI file from the backend first, then run this again.");
  process.exit(1);
}

const cli = resolve(webDir, "node_modules", "openapi-typescript", "bin", "cli.js");
const result = spawnSync(process.execPath, [cli, input, "--output", output], { stdio: "inherit" });
if (result.status !== 0) {
  console.error("gen:api failed: openapi-typescript returned an error.");
  process.exit(result.status ?? 1);
}
console.log(`Wrote ${output}`);
