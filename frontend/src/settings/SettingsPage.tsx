import type { ComponentType } from "react";
import { CameraInputSection } from "./CameraInputSection";

/** Props every settings section receives; add callbacks here as sections need them. */
export interface SettingsSectionProps {
  onInputChanged?: () => void;
}

const sections: { id: string; title: string; component: ComponentType<SettingsSectionProps> }[] = [{ id: "camera-input", title: "Camera input", component: CameraInputSection }];

export function SettingsPage(props: SettingsSectionProps) {
  return <div className="settings-page">{sections.map(({ id, title, component: Component }) =>
    <section className="panel" key={id} aria-labelledby={`${id}-heading`}>
      <h2 id={`${id}-heading`}>{title}</h2>
      <Component {...props} />
    </section>)}</div>;
}
