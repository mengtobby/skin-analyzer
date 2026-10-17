import { Button, Card, ShieldIcon, SunIcon, CameraIcon, ScanFaceIcon } from "../ui";
export function StartPage({ onStart }: { onStart: () => void }) {
  return <div className="start-page">
    <section className="start-hero"><ScanFaceIcon className="hero-icon" /><h1>Let's take a look at your skin</h1>
      <p>A few quiet moments for a closer look and personalized cosmetic guidance.</p>
      <Button size="lg" onClick={onStart}>Start analyzing</Button></section>
    <div className="capture-tips">
      <Card><SunIcon /><h2>Find your light</h2><p>Use even, front-facing light. A window is a good place to start.</p></Card>
      <Card><CameraIcon /><h2>Get comfortable</h2><p>Sit about an arm's length away and face the camera.</p></Card>
      <Card><ScanFaceIcon /><h2>A clear view</h2><p>Keep hair off your forehead and remove makeup if possible.</p></Card>
    </div>
    <p className="privacy-note"><ShieldIcon />Your camera image stays on this device and is never saved</p>
    <p className="flow-disclaimer">Cosmetic guidance only - not a medical diagnosis. Seek professional advice for persistent, painful or changing skin concerns.</p>
  </div>;
}
