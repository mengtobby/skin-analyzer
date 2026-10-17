import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { Badge, Card, HomeIcon } from "./index";

afterEach(cleanup);
it("renders a section with title, action and forwarded attributes", () => {
  render(<Card title={<span>Overview</span>} action={<button>Details</button>} className="custom" aria-label="Summary"><p>Analysis ready</p></Card>);
  const card = screen.getByRole("region", { name: "Summary" });
  expect(card.tagName).toBe("SECTION");
  expect(card).toHaveClass("ui-card", "custom");
  expect(screen.getByRole("heading", { name: "Overview" })).toBeVisible();
  expect(screen.getByRole("button", { name: "Details" })).toBeVisible();
  expect(card).toHaveTextContent("Analysis ready");
});
it.each(["neutral", "accent", "success", "warning"] as const)("renders a %s badge", tone => {
  render(<Badge tone={tone}>Rx</Badge>);
  expect(screen.getByText("Rx")).toHaveClass(`ui-badge--${tone}`);
});
it("hides decorative icons and exposes titled icons", () => {
  const { container, rerender } = render(<HomeIcon />);
  expect(container.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
  rerender(<HomeIcon title="Home" className="custom-icon" />);
  expect(screen.getByRole("img", { name: "Home" })).toHaveClass("custom-icon");
  expect(screen.getByRole("img", { name: "Home" })).not.toHaveAttribute("aria-hidden");
});
