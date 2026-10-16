import { afterEach, expect, it, vi } from "vitest";
import { getCameras, getSettings, setSource, sourceLabel } from "./api";

afterEach(() => vi.unstubAllGlobals());
const reply = (data: unknown, success = true, error: string | null = null) =>
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: success,
    json: async () => ({ success, data, error }) }));

it("validates sources and sends a typed source request", async () => {
  const source = { kind: "camera", spec: "camera:2", camera_index: 2 };
  reply(source);
  expect(await getSettings()).toEqual(source);
  expect(await setSource({ kind: "camera", camera_index: 2 })).toEqual(source);
  expect(fetch).toHaveBeenLastCalledWith("/api/settings/source", expect.objectContaining({
    method: "POST", body: JSON.stringify({ kind: "camera", camera_index: 2 }),
  }));
});

it.each([null, {}, { kind: "camera", spec: "camera:0", camera_index: -1 },
  { kind: "other", spec: "x", camera_index: null }])("rejects malformed settings %j", async (data) => {
  reply(data);
  await expect(getSettings()).rejects.toThrow("Settings service unavailable");
});

it("validates every camera and accepts an empty scan", async () => {
  reply([]); expect(await getCameras()).toEqual([]);
  reply([{ index: 0, width: 640, height: 480 }]); expect(await getCameras()).toHaveLength(1);
  reply([{ index: 0, width: "640", height: 480 }]);
  await expect(getCameras()).rejects.toThrow("Settings service unavailable");
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
