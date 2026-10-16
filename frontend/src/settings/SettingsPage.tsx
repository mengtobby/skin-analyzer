import { CameraInputSection } from "./CameraInputSection";

const sections = [{ id: "camera-input", title: "Camera input", component: CameraInputSection }];

export function SettingsPage() {
  return <div className="settings-page">{sections.map(({ id, title, component: Component }) =>
    <section className="panel" key={id} aria-labelledby={`${id}-heading`}>
      <h2 id={`${id}-heading`}>{title}</h2>
      <Component />
    </section>)}</div>;
}
