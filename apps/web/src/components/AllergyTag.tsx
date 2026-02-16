"use client";

interface AllergyTagProps {
  allergen: string;
  severity: "mild" | "moderate" | "severe";
  onDelete?: () => void;
}

const severityColors = {
  mild: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  moderate: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
  severe: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
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
