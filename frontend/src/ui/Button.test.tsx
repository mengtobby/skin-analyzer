import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Button } from "./Button";

afterEach(cleanup);
it.each(["primary", "secondary", "ghost"] as const)("renders the %s variant and size", variant => {
  render(<Button variant={variant} size="lg" icon={<svg data-testid="icon" />}>Continue</Button>);
  expect(screen.getByRole("button")).toHaveClass(`ui-button--${variant}`, "ui-button--lg");
  expect(screen.getByTestId("icon").parentElement).toHaveAttribute("aria-hidden", "true");
});
it("forwards attributes and clicks, and respects disabled", () => {
  const onClick = vi.fn();
  const { rerender } = render(<Button onClick={onClick} name="continue" type="submit">Continue</Button>);
  const button = screen.getByRole("button");
  expect(button).toHaveAttribute("name", "continue");
  expect(button).toHaveAttribute("type", "submit");
  fireEvent.click(button);
  expect(onClick).toHaveBeenCalledTimes(1);
  rerender(<Button disabled onClick={onClick}>Continue</Button>);
  fireEvent.click(button);
  expect(button).toBeDisabled();
  expect(onClick).toHaveBeenCalledTimes(1);
});
