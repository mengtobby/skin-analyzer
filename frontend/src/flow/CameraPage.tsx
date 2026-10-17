import { useEffect } from "react";
import { LiveView } from "../components/LiveView";
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
  return <div className="camera-page"><header><h1>A moment for your skin</h1><p>Face the camera and settle into even light.</p></header>
    <div className="camera-layout"><LiveView {...stream} headerRef={stream.displayHeaderRef} />
      <Card title="Let's get a clear view">
        <Badge tone={stream.connection === 'connected' ? 'success' : 'neutral'}>{stream.connection === 'connected' ? 'Camera connected' : 'Reconnecting'}{stream.header ? ` - ${Math.round(stream.header.perf.fps)} fps` : ''}</Badge>
        <p>{stream.header?.face ? 'Face found. Keep looking straight ahead.' : 'No face detected - centre your face in the camera.'}</p>
        {stream.header?.quality && !stream.header.quality.ok && <QualityBanner quality={stream.header.quality} />}
        {ready && <p>You're ready. Hold still for a short scan.</p>}
        {scan.scanning ? <div role="status"><p>Hold still... {scan.progress < 1 ? `${Math.ceil(3 * (1 - scan.progress))} seconds` : 'Finishing your analysis'}</p>
          <progress aria-label="Scan progress" max={1} value={scan.progress} /><Button variant="secondary" onClick={scan.cancel}>Cancel scan</Button></div>
          : <Button size="lg" disabled={!ready} onClick={scan.start}>Analyze my skin</Button>}
        {(scan.error || stream.error) && <p role="alert">{scan.error || stream.error}</p>}
        <p><a href="#settings">Change camera in Settings</a></p>
      </Card></div></div>;
}
