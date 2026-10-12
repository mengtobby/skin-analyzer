import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { InsightsPanel } from "./InsightsPanel";
import { reportFixture } from "../protocol/fixtures";

afterEach(cleanup);

it("expands accessible insight controls to reveal mechanisms and clinical advice", () => {
  render(<InsightsPanel report={reportFixture} />);
  const button = screen.getByRole("button", { name: /Inflammatory acne/ });
  expect(button).toHaveAttribute("aria-expanded", "false");
  expect(screen.getByText("Follicular inflammation")).not.toBeVisible();
  fireEvent.click(button);
  expect(button).toHaveAttribute("aria-expanded", "true");
  expect(screen.getByText("Follicular inflammation")).toBeVisible();
  expect(screen.getByText("Occlusive products")).toBeVisible();
  expect(screen.getByText("When to see a dermatologist")).toBeVisible();
  fireEvent.click(button);
  expect(button).toHaveAttribute("aria-expanded", "false");
});
