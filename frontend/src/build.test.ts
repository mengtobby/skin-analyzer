// @vitest-environment node
import { readFileSync } from "node:fs";
import { expect, it } from "vitest";

const manifest = JSON.parse(readFileSync(new URL("../package.json", import.meta.url), "utf8")) as {
  scripts: Record<string, string>;
};

it.each(Object.entries(manifest.scripts))("%s does not install packages", (_name, command) => {
  expect(command).not.toMatch(/\bnpm(?:\.cmd)?\s+(?:--\S+\s+)*install\b/i);
  expect(command).not.toMatch(/npm_execpath[\s\S]*['"]install['"]/i);
});
