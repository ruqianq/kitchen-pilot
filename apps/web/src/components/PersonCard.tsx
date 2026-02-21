"use client";

import type { Person } from "@/lib/api";
import Button from "./Button";

interface PersonCardProps {
  person: Person;
  onDelete?: (id: string) => void;
}

export default function PersonCard({ person, onDelete }: PersonCardProps) {
  return (
    <div className="flex items-center justify-between rounded-xl border border-stone-200 p-4 shadow-sm dark:border-stone-700">
      <div>
        <p className="font-medium text-stone-900 dark:text-stone-100">
          {person.name}
        </p>
        <p className="text-sm text-stone-500 dark:text-stone-400">
          {person.role}
          {person.age_band ? ` \u00B7 ${person.age_band}` : ""}
        </p>
      </div>
      {onDelete && (
        <Button variant="danger" onClick={() => onDelete(person.id)} className="px-3 py-1 text-xs">
          Remove
        </Button>
      )}
    </div>
  );
}
