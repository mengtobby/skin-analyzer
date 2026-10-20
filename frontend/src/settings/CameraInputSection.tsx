import { useEffect, useState } from "react";
import { getCameras, getSettings, setSource, sourceLabel } from "./api";
import type { CameraOption, SourceView } from "./api";
import type { SettingsSectionProps } from "./SettingsPage";

const validUrl = (value: string) => {
  try {
    const address = new URL(value);
    return ["http:", "https:", "rtsp:"].includes(address.protocol) && address.hostname !== "";
  }
  catch { return false; }
};

function useCameraInput(onInputChanged?: () => void) {
  const [source, updateSource] = useState<SourceView | null>(null);
  const [cameras, updateCameras] = useState<CameraOption[]>([]);
  const [selection, select] = useState("");
  const [url, updateUrl] = useState("");
  const [appliedUrl, rememberApplied] = useState<string | null>(null);
  const [scanning, scan] = useState(false);
  const [pending, connect] = useState(false);
  const [error, fail] = useState("");
  const [urlFailed, markUrlFailed] = useState(false);
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

  // The server hides the path, so compare against the address this window last applied.
  const changed = selection === "url" ? validUrl(url) && url !== appliedUrl && `url:${url}` !== source?.spec :
    selection !== "" && !(source?.kind === "camera" && String(source.camera_index) === selection);
  async function apply() {
    connect(true); fail(""); markUrlFailed(false); notify("");
    try {
      const { source: value, saved } = await setSource(selection === "url" ? { kind: "url", url } :
        { kind: "camera", index: Number(selection) });
      updateSource(value); updateUrl("");
      rememberApplied(value.kind === "url" && selection === "url" ? url : null);
      select(value.kind === "camera" ? String(value.camera_index) : "url");
      onInputChanged?.();
      notify(`Now using ${sourceLabel(value)}. Earlier results were cleared.` +
        (saved ? "" : " This choice could not be saved for next launch."));
    } catch (e) {
      markUrlFailed(selection === "url");
      fail(e instanceof Error ? e.message : "Settings service unavailable");
    }
    finally { connect(false); }
  }

  return { source, cameras, selection, select, url, updateUrl, scanning, pending, error, urlFailed,
    scanError, status, rescan, changed, apply };
}

export function CameraInputSection({ onInputChanged }: SettingsSectionProps) {
  const { source, cameras, selection, select, url, updateUrl, scanning, pending, error, urlFailed,
    scanError, status, rescan, changed, apply } = useCameraInput(onInputChanged);
  const invalidUrl = url !== "" && !validUrl(url);
  const serverUrlError = urlFailed && error !== "";
  const description = ["stream-help", invalidUrl && "stream-error", serverUrlError && "camera-input-error"]
    .filter(Boolean).join(" ");
  return <div className="camera-settings">
    <p>Current input: <strong>{source ? sourceLabel(source) : "Loading current input…"}</strong></p>
    <p id="camera-input-error" role="alert">{[error, scanError].filter(Boolean).join(" ")}</p>
    <div className="camera-scan">
      <span role="status">{scanning ? "Scanning for cameras…" : ""}</span>
      {!scanning && cameras.length === 0 && <span className="muted">No local cameras found.</span>}
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
          placeholder="http://192.168.1.20:8080/video" aria-describedby={description}
          aria-invalid={invalidUrl || serverUrlError || undefined} autoComplete="off" />
        <p className="muted" id="stream-help">Install an IP-camera app on your phone, connect to the same Wi-Fi,
          and paste the stream address shown in the app. Use an http, https or rtsp URL. On Windows, a password in the stream address is saved encrypted for your account; elsewhere it is stored in plain text readable only by your user account. Avoid putting passwords on the command line.</p>
      </div>}
    </fieldset>
    <p id="stream-error" role="alert">{selection === "url" && invalidUrl ?
      "Enter an address that starts with http://, https:// or rtsp://" : ""}</p>
    <button disabled={pending || scanning || !source || !changed} onClick={() => void apply()}>Apply</button>
    <p role="status">{pending ? "Connecting… this can take a few seconds" : ""}</p>
    <p role="status">{status}</p>
  </div>;
}
