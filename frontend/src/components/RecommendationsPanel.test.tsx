import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { RecommendationsPanel } from "./RecommendationsPanel";
import { reportFixture } from "../protocol/fixtures";

afterEach(cleanup);

it("groups routines, repeats AM/PM products and exposes warnings and cautions", () => {
  const base = reportFixture.products[0];
  render(<RecommendationsPanel report={{
    ...reportFixture,
    products: [base, { ...base, id: "am", name: "Day product", routine: "AM" },
      { ...base, id: "pm", name: "Night product", routine: "PM" }],
  }} />);
  const am = screen.getByRole("heading", { name: "AM / Morning" }).parentElement!;
  const pm = screen.getByRole("heading", { name: "PM / Evening" }).parentElement!;
  expect(within(am).getByText("Gentle cleanser")).toBeVisible();
  expect(within(pm).getByText("Gentle cleanser")).toBeVisible();
  expect(within(am).getByText("Day product")).toBeVisible();
  expect(within(am).queryByText("Night product")).toBeNull();
  expect(within(pm).getByText("Night product")).toBeVisible();
  expect(screen.getByText(reportFixture.warnings[0])).toBeVisible();
  expect(screen.getByText("Salicylic acid")).toHaveAttribute(
    "title", "Helps with clogged pores\nIntroduce gradually",
  );
  const ingredient = screen.getByRole("button", { name: /Salicylic acid/ });
  expect(ingredient).toHaveAttribute("aria-expanded", "false");
  fireEvent.click(ingredient);
  expect(ingredient).toHaveAttribute("aria-expanded", "true");
  expect(screen.getByText("Introduce gradually")).toBeVisible();
});
