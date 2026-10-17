import type { ButtonHTMLAttributes, ReactNode } from "react";
import "./Button.css";

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost";
  size?: "md" | "lg";
  icon?: ReactNode;
};

export function Button({ variant = "primary", size = "md", icon, className = "", children, type = "button", ...props }: ButtonProps) {
  return <button {...props} type={type} className={`ui-button ui-button--${variant} ui-button--${size} ${className}`}>
    {icon && <span className="ui-button__icon" aria-hidden="true">{icon}</span>}{children}
  </button>;
}
