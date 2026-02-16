"use client";

import type { Person } from "@/lib/api";
import Button from "./Button";

interface PersonCardProps {
  person: Person;
  onDelete?: (id: string) => void;
}

export default function PersonCard({ person, onDelete }: PersonCardProps) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
      <div>
        <p className="font-medium text-zinc-900 dark:text-zinc-100">
          {person.name}
        </p>
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
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
