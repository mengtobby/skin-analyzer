import { Button, ShieldIcon, SunIcon, CameraIcon, ScanFaceIcon } from "../ui";
import { MeshFaceIllustration } from "./MeshFaceIllustration";
export function StartPage({ onStart }: { onStart: () => void }) {
  return <div className="start-page">
    <section className="start-hero"><div className="start-intro"><h1>Let's take a look <span className="scan-pill" aria-hidden="true"><ScanFaceIcon /></span>at your skin</h1>
      <p>A few quiet moments for a closer look and personalized cosmetic guidance.</p>
      <Button variant="cta" size="lg" onClick={onStart}>Start analyzing</Button></div><MeshFaceIllustration /></section>
    <div className="capture-tips">
      <div className="capture-tip"><SunIcon /><h2>Find your light</h2><p>Use even, front-facing light. A window is a good place to start.</p></div>
      <div className="capture-tip"><CameraIcon /><h2>Get comfortable</h2><p>Sit about an arm's length away and face the camera.</p></div>
      <div className="capture-tip"><ScanFaceIcon /><h2>A clear view</h2><p>Keep hair off your forehead and remove makeup if possible.</p></div>
    </div>
    <p className="privacy-note"><ShieldIcon />Your camera image stays on this device and is never saved</p>
    <p className="flow-disclaimer">Cosmetic guidance only - not a medical diagnosis. Seek professional advice for persistent, painful or changing skin concerns.</p>
  </div>;
}
