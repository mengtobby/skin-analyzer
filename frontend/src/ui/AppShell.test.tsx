import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { AppShell } from "./AppShell";
import { HomeIcon, SettingsIcon } from "./icons";

afterEach(cleanup);
it("renders hash links, active navigation, content and right slot", () => {
  render(<AppShell nav={[
    { id: "home", label: "Home", href: "#home", icon: <HomeIcon /> },
    { id: "settings", label: "Settings", href: "#settings", icon: <SettingsIcon /> },
  ]} active="settings" right={<span>Connected</span>}><h1>Skin</h1></AppShell>);
  expect(screen.getByRole("link", { name: "Settings" })).toHaveAttribute("aria-current", "page");
  expect(screen.getByRole("link", { name: "Settings" })).toHaveAttribute("href", "#settings");
  expect(screen.getByRole("link", { name: "Home" })).toHaveAttribute("href", "#home");
  expect(screen.getByRole("link", { name: "Home" })).not.toHaveAttribute("aria-current");
  expect(screen.getByText("Connected")).toBeVisible();
  expect(screen.getByRole("main")).toContainElement(screen.getByRole("heading", { name: "Skin" }));
  expect(screen.getByRole("link", { name: "Skin Analyzer home" })).toBeVisible();
  const header = screen.getByRole("banner");
  expect(Array.from(header.children)).toEqual([
    screen.getByRole("link", { name: "Skin Analyzer home" }),
    screen.getByRole("navigation", { name: "Main navigation" }),
    screen.getByText("Connected").parentElement,
  ]);
});
