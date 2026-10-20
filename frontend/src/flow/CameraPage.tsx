import { useEffect, useRef, useState } from "react";
import { LiveView } from "../components/LiveView";
import { qualityGuidance } from "../components/qualityGuidance";
import { QualityBanner } from "../components/QualityBanner";
import { Badge, Button, Card } from "../ui";
import { useScan, type SkinStream } from "./useScan";
import type { AnalysisSnapshot } from "./snapshot";
export function CameraPage({ stream, onCapture, onProgress }: {
  stream: SkinStream; onCapture: (snapshot: AnalysisSnapshot) => void; onProgress?: (value: number) => void;
}) {
  const scan = useScan(stream, onCapture);
  const ready = stream.connection === 'connected' && !!stream.header?.face && stream.header.quality?.ok === true;
  useEffect(() => { onProgress?.(scan.progress); }, [scan.progress, onProgress]);
  const [guidance, setGuidance] = useState({ face: '', issues: '' });
  const [announcedError, setAnnouncedError] = useState('');
  const error = scan.error || stream.error || '';
  useEffect(() => { setAnnouncedError(error); }, [error]);
  const faceGuidance = stream.header?.face ? 'Face found. Keep looking straight ahead.' : 'No face detected - centre your face in the camera.';
  const issues = stream.header?.face && stream.header.quality && !stream.header.quality.ok
    ? [...new Set(stream.header.quality.issues)].map(issue => qualityGuidance[issue] ?? 'Centre your face in even, diffuse light').join('. ') : '';
  useEffect(() => { setGuidance({ face: faceGuidance, issues }); }, [faceGuidance, issues]);
  const pageRef = useRef<HTMLDivElement>(null);
  const wasScanning = useRef(false);
  const hasScanned = useRef(false);
  useEffect(() => {
    if (scan.scanning || wasScanning.current) {
      pageRef.current?.querySelector<HTMLButtonElement>('[data-scan-action]')?.focus();
    }
    wasScanning.current = scan.scanning;
  }, [scan.scanning]);
  return <div className="camera-page" ref={pageRef}><header><h1>A moment for your skin</h1><p>Face the camera and settle into even light.</p></header>
    <div className="camera-layout"><LiveView {...stream} headerRef={stream.displayHeaderRef} />
      <Card title="Let's get a clear view">
        <Badge tone={stream.connection === 'connected' ? 'success' : 'neutral'}>{stream.connection === 'connected' ? 'Camera connected' : 'Reconnecting'}{stream.header ? ` - ${Math.round(stream.header.perf.fps)} fps` : ''}</Badge>
        <div role="status" aria-live="polite" aria-atomic="false">
          <p>{guidance.face}</p>
          <span className="sr-only">{guidance.issues ? `Improve capture conditions. ${guidance.issues}` : ''}</span>
          <p hidden={!scan.scanning}>{scan.scanning ? `Hold still... ${scan.progress < 1 ? `${Math.ceil(3 * (1 - scan.progress))} seconds` : 'Finishing your analysis'}` : ''}</p>
        </div>
        {stream.header?.quality && !stream.header.quality.ok && <QualityBanner quality={stream.header.quality} />}
        {ready && <p>You're ready. Hold still for a short scan.</p>}
        {scan.scanning ? <div>
          <progress aria-label="Scan progress" max={1} value={scan.progress} /><Button data-scan-action variant="secondary" onClick={scan.cancel}>Cancel scan</Button></div>
          : <Button data-scan-action size="lg" disabled={!ready && !hasScanned.current} aria-disabled={!ready || undefined} onClick={() => { if (ready) { hasScanned.current = true; scan.start(); } }}>Analyze my skin</Button>}
        <p role="alert" aria-atomic="true">{announcedError}</p>
        <p><a href="#settings">Change camera in Settings</a></p>
      </Card></div></div>;
}
