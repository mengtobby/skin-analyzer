import type { ReactNode, SVGProps } from "react";

export type IconProps = SVGProps<SVGSVGElement> & { title?: string };
function Icon({ title, children, ...props }: IconProps & { children: ReactNode }) {
  return <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden={title ? undefined : true} role={title ? "img" : undefined} {...props}>
    {title && <title>{title}</title>}{children}
  </svg>;
}
export function HomeIcon(props: IconProps) {
  return <Icon {...props}><path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1Z" /></Icon>;
}
export function ScanFaceIcon(props: IconProps) {
  return <Icon {...props}><path d="M8 3H4a1 1 0 0 0-1 1v4m13-5h4a1 1 0 0 1 1 1v4M3 16v4a1 1 0 0 0 1 1h4m8 0h4a1 1 0 0 0 1-1v-4M8 8v3m8-3v3m-7 5c2 2 4 2 6 0m-3-6v3h-1" /></Icon>;
}
export function CameraIcon(props: IconProps) {
  return <Icon {...props}><path d="M8 6 10 3h4l2 3h4a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1Z" /><circle cx="12" cy="13" r="4" /></Icon>;
}
export function SparklesIcon(props: IconProps) {
  return <Icon {...props}><path d="m12 4 2.2 5.8L20 12l-5.8 2.2L12 20l-2.2-5.8L4 12l5.8-2.2ZM20 2v4m-2-2h4M4 18v4m-2-2h4" /></Icon>;
}
export function SettingsIcon(props: IconProps) {
  return <Icon {...props}><path d="m9 3-.7 2.5-2.5 1L3.5 6l-2 3.5L3.3 11v2l-1.8 1.5 2 3.5 2.3-.5 2.5 1L9 21h6l.7-2.5 2.5-1 2.3.5 2-3.5-1.8-1.5v-2l1.8-1.5-2-3.5-2.3.5-2.5-1L15 3Z" /><circle cx="12" cy="12" r="3" /></Icon>;
}
export function ChevronRightIcon(props: IconProps) {
  return <Icon {...props}><path d="m9 5 7 7-7 7" /></Icon>;
}
export function ArrowLeftIcon(props: IconProps) {
  return <Icon {...props}><path d="M20 12H4m7-7-7 7 7 7" /></Icon>;
}
export function InfoIcon(props: IconProps) {
  return <Icon {...props}><circle cx="12" cy="12" r="9" /><path d="M12 11v6m0-10v.1" /></Icon>;
}
export function CheckIcon(props: IconProps) {
  return <Icon {...props}><path d="m5 12 4 4L19 6" /></Icon>;
}
export function ShieldIcon(props: IconProps) {
  return <Icon {...props}><path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6Z" /><path d="m8 12 3 3 5-6" /></Icon>;
}
export function SunIcon(props: IconProps) {
  return <Icon {...props}><circle cx="12" cy="12" r="4" /><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5" /></Icon>;
}
export function MoonIcon(props: IconProps) {
  return <Icon {...props}><path d="M20.8 13.5A9 9 0 0 1 10.5 3.2a9 9 0 1 0 10.3 10.3Z" /></Icon>;
}
export function RefreshIcon(props: IconProps) {
  return <Icon {...props}><path d="M20 4v6h-6M4 20v-6h6M4.8 8a8 8 0 0 1 13-2L20 10M4 14l2.2 4a8 8 0 0 0 13-2" /></Icon>;
}
