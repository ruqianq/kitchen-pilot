"use client";

import { useState } from "react";
import Button from "@/components/Button";
import Input from "@/components/Input";
import PersonCard from "@/components/PersonCard";
import Select from "@/components/Select";
import type { Person } from "@/lib/api";
import { householdApi } from "@/lib/api";

const ROLES = [
  { value: "adult", label: "Adult" },
  { value: "child", label: "Child" },
  { value: "partner", label: "Partner" },
  { value: "other", label: "Other" },
];

const AGE_BANDS = [
  { value: "", label: "Not specified" },
  { value: "toddler", label: "Toddler (1-3)" },
  { value: "child", label: "Child (4-12)" },
  { value: "teen", label: "Teen (13-17)" },
  { value: "adult", label: "Adult (18-64)" },
  { value: "senior", label: "Senior (65+)" },
];

interface PeopleStepProps {
  people: Person[];
  onPeopleChange: (people: Person[]) => void;
  onNext: () => void;
  onBack: () => void;
}

export default function PeopleStep({
  people,
  onPeopleChange,
  onNext,
  onBack,
}: PeopleStepProps) {
  const [name, setName] = useState("");
  const [role, setRole] = useState("adult");
  const [ageBand, setAgeBand] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      setError("Name is required");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const person = await householdApi.createPerson({
        name: name.trim(),
        role,
        age_band: ageBand || undefined,
      });
      onPeopleChange([...people, person]);
      setName("");
      setRole("adult");
      setAgeBand("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add person");
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(id: string) {
    try {
      await householdApi.deletePerson(id);
      onPeopleChange(people.filter((p) => p.id !== id));
    } catch {
      setError("Failed to remove person");
    }
  }

  return (
    <div className="mt-6 flex flex-col gap-6">
      <div className="flex flex-col gap-3">
        {people.map((p) => (
          <PersonCard key={p.id} person={p} onDelete={handleDelete} />
        ))}
        {people.length === 0 && (
          <p className="text-sm text-stone-500 dark:text-stone-400">
            No family members added yet.
          </p>
        )}
      </div>

      <form onSubmit={handleAdd} className="rounded-xl border border-stone-200 p-4 dark:border-stone-800">
        <h3 className="mb-3 text-sm font-medium text-stone-700 dark:text-stone-300">
          Add Family Member
        </h3>
        <div className="flex flex-col gap-3">
          <Input
            label="Name"
            placeholder="e.g. Alice"
            value={name}
            onChange={(e) => setName(e.target.value)}
            error={error}
          />
          <div className="grid grid-cols-2 gap-3">
            <Select label="Role" options={ROLES} value={role} onChange={(e) => setRole(e.target.value)} />
            <Select label="Age Band" options={AGE_BANDS} value={ageBand} onChange={(e) => setAgeBand(e.target.value)} />
          </div>
          <Button type="submit" variant="secondary" disabled={loading}>
            {loading ? "Adding..." : "Add Person"}
          </Button>
        </div>
      </form>

      <div className="flex justify-between">
        <Button variant="secondary" onClick={onBack}>Back</Button>
        <Button onClick={onNext} disabled={people.length === 0}>Next</Button>
      </div>
    </div>
  );
}
