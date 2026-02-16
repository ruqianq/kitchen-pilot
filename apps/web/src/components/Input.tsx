"use client";

import { InputHTMLAttributes } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
}

export default function Input({ label, error, className = "", ...props }: InputProps) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
        {label}
      </label>
      <input
        className={`rounded-lg border px-3 py-2 text-sm outline-none transition-colors
          ${error
            ? "border-red-500 focus:border-red-500"
            : "border-zinc-300 focus:border-zinc-900 dark:border-zinc-700 dark:focus:border-zinc-400"
          }
          bg-white dark:bg-zinc-900 dark:text-zinc-100 ${className}`}
        {...props}
      />
      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  );
}
