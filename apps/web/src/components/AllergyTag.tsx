"use client";

interface AllergyTagProps {
  allergen: string;
  severity: "mild" | "moderate" | "severe";
  onDelete?: () => void;
}

const severityColors = {
  mild: "bg-lime-100/80 text-lime-800 dark:bg-lime-900/60 dark:text-lime-200",
  moderate: "bg-amber-100/80 text-amber-800 dark:bg-amber-900/60 dark:text-amber-200",
  severe: "bg-red-100/80 text-red-800 dark:bg-red-900/60 dark:text-red-200",
};

export default function AllergyTag({ allergen, severity, onDelete }: AllergyTagProps) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium ${severityColors[severity]}`}
    >
      {allergen}
      <span className="opacity-60">({severity})</span>
      {onDelete && (
        <button
          onClick={onDelete}
          className="ml-1 hover:opacity-70"
          aria-label={`Remove ${allergen}`}
        >
          &times;
        </button>
      )}
    </span>
  );
}
