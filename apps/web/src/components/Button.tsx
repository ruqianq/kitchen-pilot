"use client";

import { ButtonHTMLAttributes } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger";
}

export default function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonProps) {
  const base =
    "rounded-full px-6 py-3 text-sm font-medium transition-colors disabled:opacity-50";
  const variants = {
    primary:
      "bg-orange-700 text-white shadow-sm hover:bg-orange-800 dark:bg-orange-600 dark:hover:bg-orange-500",
    secondary:
      "border border-stone-300 text-stone-700 hover:bg-orange-50 dark:border-stone-600 dark:text-stone-300 dark:hover:bg-stone-800",
    danger:
      "bg-red-600 text-white hover:bg-red-700 dark:bg-red-500 dark:hover:bg-red-600",
  };
  return (
    <button className={`${base} ${variants[variant]} ${className}`} {...props} />
  );
}
