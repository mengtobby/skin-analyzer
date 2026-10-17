import "./Stepper.css";

export type StepperProps = {
  steps: { id: string; label: string }[];
  current: number;
  currentProgress?: number;
  onSelect?: (index: number) => void;
};

export function Stepper({ steps, current, currentProgress = 0.35, onSelect }: StepperProps) {
  const active = Number.isFinite(current) ? Math.max(0, Math.min(steps.length - 1, Math.trunc(current))) : 0;
  const progress = Number.isFinite(currentProgress) ? Math.max(0, Math.min(1, currentProgress)) : 0.35;
  return <nav className="ui-stepper" aria-label="Analysis progress">
    <ol>{steps.map((step, index) => <li key={step.id} aria-current={index === active ? "step" : undefined}>
      {index < active && onSelect
        ? <button type="button" className="ui-stepper__label" onClick={() => onSelect(index)} title={step.label}>{step.label}</button>
        : <span className="ui-stepper__label" title={step.label}>{step.label}</span>}
      <span className="sr-only">Step {index + 1} of {steps.length}</span>
      <span className="ui-stepper__marker" aria-hidden="true">{index === active && <span />}</span>
      <span className="ui-stepper__segment" aria-hidden="true"><span style={{ width: `${index < active ? 100 : index === active ? progress * 100 : 0}%` }} /></span>
    </li>)}</ol>
  </nav>;
}
