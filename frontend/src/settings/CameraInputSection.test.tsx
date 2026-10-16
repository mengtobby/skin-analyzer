import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { CameraInputSection } from "./CameraInputSection";

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

it("scans, marks the active camera, disables unchanged input and rescans", async () => {
  render(<CameraInputSection />);
  expect(screen.getByText("Scanning for cameras…")).toBeVisible();
  expect(await screen.findByLabelText("Camera 1 · 640×480 (in use)")).toBeChecked();
  expect(screen.getByRole("button", { name: "Apply" })).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "Rescan" }));
  await waitFor(() => expect(fetchMock.mock.calls.filter(([p]) => p.endsWith("cameras"))).toHaveLength(2));
});

it("disables controls while connecting then announces success", async () => {
  let finish!: (value: unknown) => void;
  render(<CameraInputSection />);
  fireEvent.click(await screen.findByLabelText("Camera 2 · 1280×720"));
  fetchMock.mockImplementationOnce(() => new Promise((resolve) => { finish = resolve; }));
  fireEvent.click(screen.getByRole("button", { name: "Apply" }));
  expect(screen.getByText("Connecting… this can take a few seconds")).toBeVisible();
  expect(screen.getByRole("button", { name: "Rescan" })).toBeDisabled();
  expect(screen.getByLabelText("Phone / network stream")).toBeDisabled();
  expect(fetchMock).toHaveBeenLastCalledWith("/api/settings/source", expect.objectContaining({
    body: JSON.stringify({ kind: "camera", index: 2 }),
  }));
  finish(response({ source: { kind: "camera", spec: "camera:2", camera_index: 2 }, saved: true }));
  expect(await screen.findByText("Now using Camera 2. Earlier results were cleared.")).toBeVisible();
  expect(screen.getByRole("button", { name: "Apply" })).toBeDisabled();
});

it("validates stream protocols and clears the URL after success", async () => {
  render(<CameraInputSection />);
  await screen.findByText("Camera 1");
  fireEvent.click(screen.getByLabelText("Phone / network stream"));
  const input = screen.getByLabelText("Stream URL");
  for (const url of ["bad", "ftp://phone/video", "javascript:alert(1)"]) {
    fireEvent.change(input, { target: { value: url } });
    expect(screen.getByRole("button", { name: "Apply" })).toBeDisabled();
  }
  for (const url of ["http://phone/video", "https://phone/video", "rtsp://phone/video"]) {
    fireEvent.change(input, { target: { value: url } });
    expect(screen.getByRole("button", { name: "Apply" })).toBeEnabled();
  }
  fetchMock.mockResolvedValueOnce(response({ source: { kind: "url", spec: "url:rtsp://phone/video", camera_index: null }, saved: true }));
  fireEvent.click(screen.getByRole("button", { name: "Apply" }));
  await screen.findByText(/Earlier results were cleared/);
  expect(input).toHaveValue("");
});

it("shows a server failure and allows retry", async () => {
  render(<CameraInputSection />);
  fireEvent.click(await screen.findByLabelText("Camera 2 · 1280×720"));
  fetchMock.mockResolvedValueOnce({ ok: false, json: async () => ({ success: false, error: "Camera busy", data: null }) });
  fireEvent.click(screen.getByRole("button", { name: "Apply" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Camera busy");
  expect(screen.getByRole("button", { name: "Apply" })).toBeEnabled();
});

it("shows file input and scan errors without losing the network option", async () => {
  fetchMock.mockImplementation((path: string) => path.endsWith("cameras") ? Promise.reject(new Error("network")) :
    Promise.resolve(response({ source: { kind: "file", spec: "file:private.png", camera_index: null } })));
  render(<CameraInputSection />);
  expect(await screen.findByText("Video file")).toBeVisible();
  expect(await screen.findByRole("alert")).toHaveTextContent("Settings service unavailable");
  expect(screen.getByLabelText("Phone / network stream")).toBeEnabled();
  expect(screen.queryByText(/private.png/)).toBeNull();
});

it("handles an empty scan and retries it", async () => {
  fetchMock.mockImplementation((path: string) => Promise.resolve(response(path.endsWith("cameras") ? { cameras: [] } : { source })));
  render(<CameraInputSection />);
  expect(await screen.findByText("No local cameras found.")).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Rescan" }));
  await waitFor(() => expect(fetchMock.mock.calls.filter(([p]) => p.endsWith("cameras"))).toHaveLength(2));
});

it("disables apply if current settings cannot be loaded", async () => {
  fetchMock.mockImplementation((path: string) => path.endsWith("cameras") ? Promise.resolve(response({ cameras })) :
    Promise.reject(new Error("transport")));
  render(<CameraInputSection />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Settings service unavailable");
  expect(screen.getByRole("button", { name: "Apply" })).toBeDisabled();
});

it("reports a successful live switch when the preference could not be saved", async () => {
  render(<CameraInputSection />);
  fireEvent.click(await screen.findByLabelText("Camera 2 · 1280×720"));
  fetchMock.mockResolvedValueOnce(response({ source: { kind: "camera", spec: "camera:2", camera_index: 2 }, saved: false }));
  fireEvent.click(screen.getByRole("button", { name: "Apply" }));
  expect(await screen.findByText(
    "Now using Camera 2. Earlier results were cleared. This choice could not be saved for next launch.")).toHaveAttribute("role", "status");
  expect(screen.getByText("Camera 2", { exact: true })).toBeVisible();
  expect(screen.getByRole("button", { name: "Apply" })).toBeDisabled();
  expect(screen.queryByRole("alert")).toBeNull();
});
