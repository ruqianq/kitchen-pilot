"use client";

import { InputHTMLAttributes } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
}

export default function Input({ label, error, className = "", ...props }: InputProps) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-sm font-medium text-stone-700 dark:text-stone-300">
        {label}
      </label>
      <input
        className={`rounded-xl border px-3 py-2 text-sm outline-none transition-colors
          ${error
            ? "border-red-500 focus:border-red-500"
            : "border-stone-300 focus:border-amber-600 dark:border-stone-600 dark:focus:border-amber-400"
          }
          bg-white dark:bg-stone-900 dark:text-stone-100 ${className}`}
        {...props}
      />
      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  );
}
