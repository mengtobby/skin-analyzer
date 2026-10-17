import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Stepper } from "./Stepper";

const steps = ["Start", "Camera", "Results", "Treatments"].map(label => ({ id: label.toLowerCase(), label }));
afterEach(cleanup);
it("marks the current step and exposes the step count", () => {
  render(<Stepper steps={steps} current={1} />);
  const nav = screen.getByRole("navigation", { name: "Analysis progress" });
  const items = within(nav).getAllByRole("listitem");
  expect(items[1]).toHaveAttribute("aria-current", "step");
  expect(items[0]).not.toHaveAttribute("aria-current");
  expect(within(items[1]).getByText("Step 2 of 4")).toBeInTheDocument();
  expect(items[1].querySelector(".ui-stepper__segment > span")).toHaveStyle({ width: "35%" });
});
it("only makes completed steps selectable", () => {
  const onSelect = vi.fn();
  render(<Stepper steps={steps} current={2} onSelect={onSelect} />);
  fireEvent.click(screen.getByRole("button", { name: "Camera" }));
  expect(onSelect).toHaveBeenCalledWith(1);
  expect(screen.queryByRole("button", { name: "Results" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Treatments" })).not.toBeInTheDocument();
});
it("uses plain text without a selection handler and clamps progress", () => {
  const { rerender } = render(<Stepper steps={steps} current={1} currentProgress={4} />);
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
  const segment = screen.getAllByRole("listitem")[1].querySelector(".ui-stepper__segment > span");
  expect(segment).toHaveStyle({ width: "100%" });
  rerender(<Stepper steps={steps} current={1} currentProgress={-1} />);
  expect(segment).toHaveStyle({ width: "0%" });
  rerender(<Stepper steps={steps} current={1} currentProgress={NaN} />);
  expect(segment).toHaveStyle({ width: "35%" });
});
