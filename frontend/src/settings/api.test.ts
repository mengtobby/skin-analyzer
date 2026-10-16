import { afterEach, expect, it, vi } from "vitest";
import { getCameras, getSettings, setSource, sourceLabel } from "./api";

afterEach(() => vi.unstubAllGlobals());
const reply = (data: unknown, success = true, error: string | null = null) =>
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: success,
    json: async () => ({ success, data, error }) }));

it("validates sources and sends a typed source request", async () => {
  const source = { kind: "camera", spec: "camera:2", camera_index: 2 };
  reply({ source });
  expect(await getSettings()).toEqual(source);
  reply({ source, saved: true });
  expect(await setSource({ kind: "camera", index: 2 })).toEqual({ source, saved: true });
  expect(fetch).toHaveBeenLastCalledWith("/api/settings/source", expect.objectContaining({
    method: "POST", body: JSON.stringify({ kind: "camera", index: 2 }),
  }));
});

it.each([null, {}, { kind: "camera", spec: "camera:0", camera_index: -1 },
  { kind: "other", spec: "x", camera_index: null }])("rejects malformed settings %j", async (data) => {
  reply({ source: data });
  await expect(getSettings()).rejects.toThrow("Settings service unavailable");
});

it("validates every camera and accepts an empty scan", async () => {
  reply({ cameras: [] }); expect(await getCameras()).toEqual([]);
  const camera = { index: 0, width: 640, height: 480, active: true };
  reply({ cameras: [camera] }); expect(await getCameras()).toEqual([camera]);
  reply({ cameras: [{ ...camera, width: "640" }] });
  await expect(getCameras()).rejects.toThrow("Settings service unavailable");
});

it("requires boolean active flags and wrapped camera lists", async () => {
  for (const data of [[], { cameras: [{}] },
    { cameras: [{ index: 0, width: 640, height: 480, active: "true" }] }]) {
    reply(data);
    await expect(getCameras()).rejects.toThrow("Settings service unavailable");
  }
});

it("returns persistence failures and validates switch results", async () => {
  const source = { kind: "url", spec: "url:rtsp://phone/live", camera_index: null };
  reply({ source, saved: false });
  expect(await setSource({ kind: "url", url: "rtsp://phone/live" })).toEqual({ source, saved: false });
  for (const data of [source, { source }, { source, saved: "false" }, { source: {}, saved: true }]) {
    reply(data);
    await expect(setSource({ kind: "url", url: "rtsp://phone/live" })).rejects.toThrow("Settings service unavailable");
  }
});

it("uses server errors and hides transport errors", async () => {
  reply(null, false, "Camera unavailable");
  await expect(getSettings()).rejects.toThrow("Camera unavailable");
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("secret URL")));
  await expect(getSettings()).rejects.toThrow("Settings service unavailable");
});

it("rejects invalid envelopes and unreadable responses", async () => {
  for (const envelope of [null, { success: true }, { success: "true", data: [] },
    { success: false, data: [], error: null }]) {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => envelope }));
    await expect(getCameras()).rejects.toThrow("Settings service unavailable");
  }
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, json: async () => { throw new Error("bad JSON"); } }));
  await expect(getSettings()).rejects.toThrow("Settings service unavailable");
});

it("redacts network credentials and queries defensively", () => {
  expect(sourceLabel({ kind: "url", camera_index: null,
    spec: "url:rtsp://alice:secret@phone/live?token=private" }))
    .toBe("Phone / network stream (url:rtsp://phone/live)");
});
