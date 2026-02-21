"use client";

import { SelectHTMLAttributes } from "react";

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  options: { value: string; label: string }[];
}

export default function Select({ label, options, className = "", ...props }: SelectProps) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-sm font-medium text-stone-700 dark:text-stone-300">
        {label}
      </label>
      <select
        className={`rounded-xl border border-stone-300 bg-white px-3 py-2 text-sm outline-none
          transition-colors focus:border-amber-600
          dark:border-stone-600 dark:bg-stone-900 dark:text-stone-100 dark:focus:border-amber-400
          ${className}`}
        {...props}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}
