// @vitest-environment node
import { readFileSync } from "node:fs";
import { expect, it } from "vitest";

const css = readFileSync(new URL("./tokens.css", import.meta.url), "utf-8");
const token = (name: string): string => {
  const match = css.match(new RegExp(String.raw`--${name}:\s*(#[0-9a-fA-F]{3,6})`));
  if (!match) throw new Error(`missing token --${name}`);
  return match[1];
};
const luminance = (hex: string): number => {
  const full = hex.length === 4 ? `#${[...hex.slice(1)].map((c) => c + c).join("")}` : hex;
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(full.slice(i, i + 2), 16) / 255)
    .map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};
const contrast = (a: string, b: string): number => {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
};

it.each([
  ["text", "bg", 4.5], ["muted", "bg", 4.5], ["muted", "surface", 4.5],
  ["accent-text", "bg", 4.5], ["accent-text", "surface", 4.5],
  ["control-border", "surface", 3], ["control-border", "bg", 3],
  ["accent", "bg", 3], ["progress", "bg", 3],
])("--%s on --%s meets %s:1 (WCAG AA)", (fg, bg, minimum) => {
  expect(contrast(token(fg), token(bg))).toBeGreaterThanOrEqual(minimum as number);
});
