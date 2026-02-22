"use client";

import { useEffect, useState } from "react";
import AllergyTag from "@/components/AllergyTag";
import Button from "@/components/Button";
import Input from "@/components/Input";
import Select from "@/components/Select";
import type { Allergy, Person } from "@/lib/api";
import { householdApi } from "@/lib/api";

const SEVERITIES = [
  { value: "mild", label: "Mild" },
  { value: "moderate", label: "Moderate" },
  { value: "severe", label: "Severe" },
];

interface AllergiesStepProps {
  people: Person[];
  onNext: () => void;
  onBack: () => void;
}

export default function AllergiesStep({ people, onNext, onBack }: AllergiesStepProps) {
  const [allergies, setAllergies] = useState<Allergy[]>([]);
  const [selectedPerson, setSelectedPerson] = useState(people[0]?.id ?? "");
  const [allergen, setAllergen] = useState("");
  const [severity, setSeverity] = useState("moderate");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    householdApi.listAllergies().then(setAllergies).catch(() => {});
  }, []);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!allergen.trim() || !selectedPerson) return;
    setLoading(true);
    setError("");
    try {
      const allergy = await householdApi.createAllergy({
        person_id: selectedPerson,
        allergen: allergen.trim(),
        severity,
      });
      setAllergies([...allergies, allergy]);
      setAllergen("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add");
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(id: string) {
    try {
      await householdApi.deleteAllergy(id);
      setAllergies(allergies.filter((a) => a.id !== id));
    } catch {
      setError("Failed to remove allergy");
    }
  }

  return (
    <div className="mt-6 flex flex-col gap-6">
      {people.map((person) => {
        const personAllergies = allergies.filter((a) => a.person_id === person.id);
        return (
          <div key={person.id} className="rounded-2xl border border-orange-100 bg-orange-50/40 p-4 shadow-sm dark:border-stone-800 dark:bg-stone-900">
            <h3 className="mb-2 font-medium text-stone-800 dark:text-stone-100">
              {person.name}
            </h3>
            <div className="flex flex-wrap gap-2">
              {personAllergies.map((a) => (
                <AllergyTag
                  key={a.id}
                  allergen={a.allergen}
                  severity={a.severity}
                  onDelete={() => handleDelete(a.id)}
                />
              ))}
              {personAllergies.length === 0 && (
                <p className="text-xs text-stone-400">No allergies</p>
              )}
            </div>
          </div>
        );
      })}

      <form onSubmit={handleAdd} className="rounded-2xl border border-dashed border-stone-300 bg-white/50 p-4 dark:border-stone-600 dark:bg-stone-900/50">
        <h3 className="mb-3 text-sm font-medium text-stone-700 dark:text-stone-300">
          Add Allergy
        </h3>
        <div className="flex flex-col gap-3">
          <Select
            label="Person"
            options={people.map((p) => ({ value: p.id, label: p.name }))}
            value={selectedPerson}
            onChange={(e) => setSelectedPerson(e.target.value)}
          />
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Allergen"
              placeholder="e.g. peanuts"
              value={allergen}
              onChange={(e) => setAllergen(e.target.value)}
            />
            <Select label="Severity" options={SEVERITIES} value={severity} onChange={(e) => setSeverity(e.target.value)} />
          </div>
          {error && <p className="text-xs text-red-500">{error}</p>}
          <Button type="submit" variant="secondary" disabled={loading || !allergen.trim()}>
            {loading ? "Adding..." : "Add Allergy"}
          </Button>
        </div>
      </form>

      <div className="flex justify-between">
        <Button variant="secondary" onClick={onBack}>Back</Button>
        <Button onClick={onNext}>Next</Button>
      </div>
    </div>
  );
}
