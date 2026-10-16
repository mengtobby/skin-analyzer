import { useEffect, useState } from "react";
import { getCameras, getSettings, setSource, sourceLabel } from "./api";
import type { CameraOption, SourceView } from "./api";

const validUrl = (value: string) => {
  try { return ["http:", "https:", "rtsp:"].includes(new URL(value).protocol); }
  catch { return false; }
};

function useCameraInput() {
  const [source, updateSource] = useState<SourceView | null>(null);
  const [cameras, updateCameras] = useState<CameraOption[]>([]);
  const [selection, select] = useState("");
  const [url, updateUrl] = useState("");
  const [scanning, scan] = useState(true);
  const [pending, connect] = useState(false);
  const [error, fail] = useState("");
  const [scanError, failScan] = useState("");
  const [status, notify] = useState("");
  const [scanNumber, rescan] = useState(0);

  useEffect(() => {
    let active = true;
    getSettings().then((value) => {
      if (active) { updateSource(value); select(value.kind === "camera" ? String(value.camera_index) : "url"); }
    }).catch((e: Error) => { if (active) fail(e.message); });
    return () => { active = false; };
  }, []);
  useEffect(() => {
    let active = true;
    scan(true); failScan("");
    getCameras().then((value) => { if (active) updateCameras(value); })
      .catch((e: Error) => { if (active) failScan(e.message); })
      .finally(() => { if (active) scan(false); });
    return () => { active = false; };
  }, [scanNumber]);

  const changed = selection === "url" ? validUrl(url) && `url:${url}` !== source?.spec :
    selection !== "" && !(source?.kind === "camera" && String(source.camera_index) === selection);
  async function apply() {
    connect(true); fail(""); notify("");
    try {
      const value = await setSource(selection === "url" ? { kind: "url", url } :
        { kind: "camera", camera_index: Number(selection) });
      updateSource(value); updateUrl("");
      select(value.kind === "camera" ? String(value.camera_index) : "url");
      notify(`Now using ${sourceLabel(value)}. Earlier results were cleared.`);
    } catch (e) { fail(e instanceof Error ? e.message : "Settings service unavailable"); }
    finally { connect(false); }
  }

  return { source, cameras, selection, select, url, updateUrl, scanning, pending, error,
    scanError, status, rescan, changed, apply };
}

export function CameraInputSection() {
  const { source, cameras, selection, select, url, updateUrl, scanning, pending, error,
    scanError, status, rescan, changed, apply } = useCameraInput();
  return <div className="camera-settings">
    <p>Current input: <strong>{source ? sourceLabel(source) : "Loading current input…"}</strong></p>
    {error && <p role="alert">{error}</p>}
    {scanError && <p role="alert">{scanError}</p>}
    <div className="camera-scan">
      {scanning ? <span role="status">Scanning for cameras…</span> :
        cameras.length === 0 && <span className="muted">No local cameras found.</span>}
      <button disabled={pending || scanning} onClick={() => rescan((n) => n + 1)}>Rescan</button>
    </div>
    <fieldset disabled={pending || !source}>
      <legend>Choose an input</legend>
      {cameras.map((camera) => <label className="camera-option" key={camera.index}>
        <input type="radio" name="camera-source" value={camera.index}
          checked={selection === String(camera.index)} onChange={() => select(String(camera.index))} />
        Camera {camera.index} · {camera.width}×{camera.height}
        {source?.kind === "camera" && source.camera_index === camera.index && " (in use)"}
      </label>)}
      <label className="camera-option"><input type="radio" name="camera-source"
        checked={selection === "url"} onChange={() => select("url")} />Phone / network stream</label>
      {selection === "url" && <div className="stream-address">
        <label htmlFor="stream-url">Stream URL</label>
        <input id="stream-url" type="url" value={url} onChange={(event) => updateUrl(event.target.value)}
          placeholder="http://192.168.1.20:8080/video" aria-describedby="stream-help" autoComplete="off" />
        <p className="muted" id="stream-help">Install an IP-camera app on your phone, connect to the same Wi-Fi,
          and paste the stream address shown in the app. Use an http, https or rtsp URL.</p>
      </div>}
    </fieldset>
    <button disabled={pending || !source || !changed} onClick={() => void apply()}>Apply</button>
    {pending && <p role="status">Connecting… this can take a few seconds</p>}
    {status && <p role="status">{status}</p>}
  </div>;
}
