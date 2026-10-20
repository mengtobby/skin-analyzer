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
  for (const url of ["bad", "ftp://phone/video", "javascript:alert(1)", "rtsp:video", "rtsp://"]) {
    fireEvent.change(input, { target: { value: url } });
    expect(screen.getByRole("button", { name: "Apply" })).toBeDisabled();
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAttribute("aria-describedby", "stream-help stream-error");
    expect(screen.getByText("Enter an address that starts with http://, https:// or rtsp://")).toBeVisible();
  }
  for (const url of ["http://phone/video", "https://phone/video", "rtsp://phone/video"]) {
    fireEvent.change(input, { target: { value: url } });
    expect(screen.getByRole("button", { name: "Apply" })).toBeEnabled();
    expect(input).not.toHaveAttribute("aria-invalid");
    expect(input).toHaveAttribute("aria-describedby", "stream-help");
    expect(screen.queryByText("Enter an address that starts with http://, https:// or rtsp://")).toBeNull();
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
  expect(await screen.findByText("Camera busy")).toHaveAttribute("role", "alert");
  expect(screen.getByRole("button", { name: "Apply" })).toBeEnabled();
});

it("shows file input and scan errors without losing the network option", async () => {
  fetchMock.mockImplementation((path: string) => path.endsWith("cameras") ? Promise.reject(new Error("network")) :
    Promise.resolve(response({ source: { kind: "file", spec: "file:private.png", camera_index: null } })));
  render(<CameraInputSection />);
  expect(await screen.findByText("Video file")).toBeVisible();
  expect(await screen.findByText("Settings service unavailable")).toHaveAttribute("role", "alert");
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
  expect(await screen.findByText("Settings service unavailable")).toHaveAttribute("role", "alert");
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
  expect(screen.getAllByRole("alert").every((region) => region.textContent === "")).toBe(true);
});

it("notifies the dashboard only after a successful switch", async () => {
  const onInputChanged = vi.fn();
  render(<CameraInputSection onInputChanged={onInputChanged} />);
  fireEvent.click(await screen.findByLabelText("Camera 2 · 1280×720"));
  fetchMock.mockImplementationOnce(() => Promise.resolve({ ok: false,
    json: async () => ({ success: false, data: null, error: "Could not open camera 2" }) }));
  fireEvent.click(screen.getByRole("button", { name: "Apply" }));
  expect(await screen.findByText("Could not open camera 2")).toBeVisible();
  expect(onInputChanged).not.toHaveBeenCalled();
  fetchMock.mockImplementationOnce(() => Promise.resolve(response(
    { source: { kind: "camera", spec: "camera:2", camera_index: 2 }, saved: true })));
  fireEvent.click(screen.getByRole("button", { name: "Apply" }));
  await screen.findByText("Now using Camera 2. Earlier results were cleared.");
  expect(onInputChanged).toHaveBeenCalledTimes(1);
});

it("keeps Apply disabled while a camera scan is running", async () => {
  render(<CameraInputSection />);
  fireEvent.click(await screen.findByLabelText("Camera 2 · 1280×720"));
  expect(screen.getByRole("button", { name: "Apply" })).toBeEnabled();
  let finish!: (value: unknown) => void;
  fetchMock.mockImplementationOnce(() => new Promise((resolve) => { finish = resolve; }));
  fireEvent.click(screen.getByRole("button", { name: "Rescan" }));
  expect(await screen.findByText("Scanning for cameras…")).toBeVisible();
  expect(screen.getByRole("button", { name: "Apply" })).toBeDisabled();
  finish(response({ cameras }));
  await waitFor(() => expect(screen.getByRole("button", { name: "Apply" })).toBeEnabled());
});

it("does not offer to re-apply the stream address already in use", async () => {
  render(<CameraInputSection />);
  await screen.findByText("Camera 1");
  fireEvent.click(screen.getByLabelText("Phone / network stream"));
  const input = screen.getByLabelText("Stream URL");
  fireEvent.change(input, { target: { value: "http://phone:8080/video" } });
  fetchMock.mockResolvedValueOnce(response({ source: { kind: "url", spec: "url:http://phone:8080/***", camera_index: null }, saved: true }));
  fireEvent.click(screen.getByRole("button", { name: "Apply" }));
  await screen.findByText(/Earlier results were cleared/);
  fireEvent.change(input, { target: { value: "http://phone:8080/video" } });
  expect(screen.getByRole("button", { name: "Apply" })).toBeDisabled();
  fireEvent.change(input, { target: { value: "http://phone:8080/other" } });
  expect(screen.getByRole("button", { name: "Apply" })).toBeEnabled();
});

it("explains how a stream password is stored", async () => {
  render(<CameraInputSection />);
  await screen.findByText("Camera 1");
  fireEvent.click(screen.getByLabelText("Phone / network stream"));
  const help = screen.getByText(/saved encrypted for your account/);
  expect(help).toHaveTextContent(/elsewhere it is stored in plain text readable only by your user account/i);
  expect(help).toHaveTextContent(/avoid putting passwords on the command line/i);
});

it("keeps live regions mounted before their messages and through updates", async () => {
  render(<CameraInputSection />);
  const alerts = screen.getAllByRole("alert");
  const statuses = screen.getAllByRole("status");
  expect(alerts).toHaveLength(2);
  expect(alerts.every((region) => region.textContent === "")).toBe(true);
  expect(statuses).toHaveLength(3);
  expect(statuses.slice(1).every((region) => region.textContent === "")).toBe(true);
  await screen.findByText("Camera 1");
  fireEvent.click(screen.getByRole("radio", { name: "Phone / network stream" }));
  const input = screen.getByRole("textbox", { name: "Stream URL" });
  expect(input).not.toHaveAttribute("aria-invalid");
  fireEvent.change(input, { target: { value: "bad" } });
  expect(alerts[1]).toHaveTextContent("Enter an address");
  fireEvent.change(input, { target: { value: "https://phone/video" } });
  fetchMock.mockResolvedValueOnce({ ok: false,
    json: async () => ({ success: false, error: "Stream unavailable", data: null }) });
  fireEvent.click(screen.getByRole("button", { name: "Apply" }));
  expect(statuses[1]).toHaveTextContent(/Connecting/);
  await screen.findByText("Stream unavailable");
  expect(input).toHaveAttribute("aria-invalid", "true");
  expect(input).toHaveAttribute("aria-describedby", "stream-help camera-input-error");
  expect(alerts[0]).toHaveTextContent("Stream unavailable");
  fetchMock.mockResolvedValueOnce(response({
    source: { kind: "url", spec: "url:https://phone/video", camera_index: null }, saved: true,
  }));
  fireEvent.click(screen.getByRole("button", { name: "Apply" }));
  await screen.findByText(/Earlier results were cleared/);
  expect(statuses[2]).toHaveTextContent(/Earlier results were cleared/);
  expect(input).not.toHaveAttribute("aria-invalid");
  expect(input).toHaveAttribute("aria-describedby", "stream-help");
  expect(screen.getAllByRole("alert")).toEqual(alerts);
  expect(screen.getAllByRole("status")).toEqual(statuses);
});
