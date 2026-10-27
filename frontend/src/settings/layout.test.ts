// @vitest-environment node
import { readFileSync } from "node:fs";
import { expect, it } from "vitest";

const css = readFileSync(new URL("../styles/settings.css", import.meta.url), "utf8");

it("keeps the input and Rescan in a wrapping row without a content inset", () => {
  const heading = css.match(/\.camera-input-heading\s*\{([^}]+)\}/)?.[1];
  expect(heading).toMatch(/display:\s*flex/);
  expect(heading).toMatch(/flex-wrap:\s*wrap/);
  expect(heading).not.toMatch(/padding|margin/);
  expect(css).toMatch(/\.camera-input-heading p\s*\{[^}]*margin:\s*0/);
});
