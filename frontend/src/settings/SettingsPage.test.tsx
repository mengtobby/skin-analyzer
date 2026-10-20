import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { SettingsPage } from "./SettingsPage";

const response = (data: unknown) => ({ ok: true, json: async () => ({ success: true, data, error: null }) });
const source = { kind: "camera", spec: "camera:1", camera_index: 1 };
const cameras = [{ index: 1, width: 640, height: 480, active: true },
  { index: 2, width: 1280, height: 720, active: false }];
let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  fetchMock = vi.fn().mockImplementation((path: string) => Promise.resolve(response(
    path.endsWith("cameras") ? { cameras } : { source })));
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

it("renders every settings section with an accessible heading", async () => {
  render(<SettingsPage />);
  expect(screen.getByRole("heading", { level: 1, name: "Settings" })).toBeVisible();
  expect(screen.getAllByRole("heading")[0]).toHaveTextContent("Settings");
  const titles = ["Camera input"];
  expect(screen.getAllByRole("region")).toHaveLength(titles.length);
  expect(screen.getAllByRole("heading", { level: 2 })).toHaveLength(titles.length);
  for (const title of titles) {
    expect(within(screen.getByRole("region", { name: title }))
      .getByRole("heading", { level: 2, name: title })).toBeVisible();
  }
  expect(await screen.findByRole("radio", { name: /Camera 1/ })).toBeChecked();
});

it("passes onInputChanged to the camera input section", async () => {
  const onInputChanged = vi.fn();
  render(<SettingsPage onInputChanged={onInputChanged} />);
  fireEvent.click(await screen.findByRole("radio", { name: /Camera 2/ }));
  expect(onInputChanged).not.toHaveBeenCalled();
  fetchMock.mockResolvedValueOnce(response({
    source: { kind: "camera", spec: "camera:2", camera_index: 2 }, saved: true,
  }));
  fireEvent.click(screen.getByRole("button", { name: "Apply" }));
  expect(await screen.findByText("Now using Camera 2. Earlier results were cleared.")).toBeVisible();
  expect(fetchMock).toHaveBeenLastCalledWith("/api/settings/source", expect.objectContaining({
    body: JSON.stringify({ kind: "camera", index: 2 }),
  }));
  expect(onInputChanged).toHaveBeenCalledTimes(1);
});
