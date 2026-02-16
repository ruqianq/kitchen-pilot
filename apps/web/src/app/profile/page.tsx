"use client";

import { useEffect, useState } from "react";
import AllergyTag from "@/components/AllergyTag";
import Button from "@/components/Button";
import Input from "@/components/Input";
import PersonCard from "@/components/PersonCard";
import Select from "@/components/Select";
import type {
  Allergy,
  DietaryRule,
  FoodPreference,
  Household,
  NutritionGoal,
  Person,
} from "@/lib/api";
import { householdApi } from "@/lib/api";

export default function ProfilePage() {
  const [household, setHousehold] = useState<Household | null>(null);
  const [people, setPeople] = useState<Person[]>([]);
  const [allergies, setAllergies] = useState<Allergy[]>([]);
  const [dietaryRules, setDietaryRules] = useState<DietaryRule[]>([]);
  const [preferences, setPreferences] = useState<FoodPreference[]>([]);
  const [goals, setGoals] = useState<NutritionGoal[]>([]);
  const [loading, setLoading] = useState(true);

  // Editing state for household name
  const [editingName, setEditingName] = useState(false);
  const [nameInput, setNameInput] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const [h, p, a, dr, fp, ng] = await Promise.all([
          householdApi.get(),
          householdApi.listPeople(),
          householdApi.listAllergies(),
          householdApi.listDietaryRules(),
          householdApi.listPreferences(),
          householdApi.listGoals(),
        ]);
        setHousehold(h);
        setPeople(p);
        setAllergies(a);
        setDietaryRules(dr);
        setPreferences(fp);
        setGoals(ng);
      } catch {
        // Not set up yet
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  async function saveName() {
    if (!household || !nameInput.trim()) return;
    const updated = await householdApi.update(household.id, { name: nameInput.trim() });
    setHousehold(updated);
    setEditingName(false);
  }

  async function deletePerson(id: string) {
    await householdApi.deletePerson(id);
    setPeople(people.filter((p) => p.id !== id));
    setAllergies(allergies.filter((a) => a.person_id !== id));
  }

  async function deleteAllergy(id: string) {
    await householdApi.deleteAllergy(id);
    setAllergies(allergies.filter((a) => a.id !== id));
  }

  async function deleteRule(id: string) {
    await householdApi.deleteDietaryRule(id);
    setDietaryRules(dietaryRules.filter((r) => r.id !== id));
  }

  async function deletePref(id: string) {
    await householdApi.deletePreference(id);
    setPreferences(preferences.filter((p) => p.id !== id));
  }

  async function deleteGoal(id: string) {
    await householdApi.deleteGoal(id);
    setGoals(goals.filter((g) => g.id !== id));
  }

  function scopeLabel(hid: string | null, pid: string | null) {
    if (pid) {
      const person = people.find((p) => p.id === pid);
      return person?.name ?? "Unknown";
    }
    return "Household";
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-50 dark:bg-black">
        <p className="text-zinc-500">Loading...</p>
      </div>
    );
  }

  if (!household) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-zinc-50 dark:bg-black">
        <p className="text-zinc-500">No household set up yet.</p>
        <a href="/onboarding">
          <Button>Get Started</Button>
        </a>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-50 p-8 dark:bg-black">
      <div className="mx-auto max-w-3xl">
        <div className="mb-8 flex items-center justify-between">
          <h1 className="text-3xl font-bold text-zinc-900 dark:text-zinc-50">
            Household Profile
          </h1>
          <a href="/">
            <Button variant="secondary">Home</Button>
          </a>
        </div>

        {/* Household Info */}
        <section className="mb-8 rounded-lg border border-zinc-200 p-6 dark:border-zinc-800">
          <h2 className="mb-4 text-xl font-semibold text-zinc-900 dark:text-zinc-100">
            Household
          </h2>
          {editingName ? (
            <div className="flex items-end gap-3">
              <Input
                label="Name"
                value={nameInput}
                onChange={(e) => setNameInput(e.target.value)}
              />
              <Button onClick={saveName}>Save</Button>
              <Button variant="secondary" onClick={() => setEditingName(false)}>Cancel</Button>
            </div>
          ) : (
            <div className="flex items-center gap-4">
              <div>
                <p className="text-lg font-medium text-zinc-900 dark:text-zinc-100">
                  {household.name}
                </p>
                <p className="text-sm text-zinc-500">{household.timezone}</p>
              </div>
              <Button
                variant="secondary"
                className="px-3 py-1 text-xs"
                onClick={() => {
                  setNameInput(household.name);
                  setEditingName(true);
                }}
              >
                Edit
              </Button>
            </div>
          )}
        </section>

        {/* People */}
        <section className="mb-8 rounded-lg border border-zinc-200 p-6 dark:border-zinc-800">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
              Family Members ({people.length})
            </h2>
            <a href="/onboarding">
              <Button variant="secondary" className="px-3 py-1 text-xs">Add</Button>
            </a>
          </div>
          <div className="flex flex-col gap-3">
            {people.map((p) => (
              <PersonCard key={p.id} person={p} onDelete={deletePerson} />
            ))}
          </div>
        </section>

        {/* Allergies */}
        <section className="mb-8 rounded-lg border border-zinc-200 p-6 dark:border-zinc-800">
          <h2 className="mb-4 text-xl font-semibold text-zinc-900 dark:text-zinc-100">
            Allergies
          </h2>
          <div className="flex flex-wrap gap-2">
            {allergies.map((a) => (
              <AllergyTag
                key={a.id}
                allergen={`${people.find((p) => p.id === a.person_id)?.name}: ${a.allergen}`}
                severity={a.severity}
                onDelete={() => deleteAllergy(a.id)}
              />
            ))}
            {allergies.length === 0 && (
              <p className="text-sm text-zinc-400">No allergies recorded.</p>
            )}
          </div>
        </section>

        {/* Dietary Rules */}
        <section className="mb-8 rounded-lg border border-zinc-200 p-6 dark:border-zinc-800">
          <h2 className="mb-4 text-xl font-semibold text-zinc-900 dark:text-zinc-100">
            Dietary Rules
          </h2>
          <div className="flex flex-col gap-2">
            {dietaryRules.map((r) => (
              <div
                key={r.id}
                className="flex items-center justify-between rounded-lg bg-zinc-50 px-4 py-2 dark:bg-zinc-900"
              >
                <span className="text-sm">
                  <span className="text-zinc-500">{scopeLabel(r.household_id, r.person_id)}:</span>{" "}
                  {r.rule}
                </span>
                <button
                  onClick={() => deleteRule(r.id)}
                  className="text-zinc-400 hover:text-red-500"
                >
                  &times;
                </button>
              </div>
            ))}
            {dietaryRules.length === 0 && (
              <p className="text-sm text-zinc-400">No dietary rules.</p>
            )}
          </div>
        </section>

        {/* Food Preferences */}
        <section className="mb-8 rounded-lg border border-zinc-200 p-6 dark:border-zinc-800">
          <h2 className="mb-4 text-xl font-semibold text-zinc-900 dark:text-zinc-100">
            Food Preferences
          </h2>
          <div className="flex flex-col gap-2">
            {preferences.map((p) => (
              <div
                key={p.id}
                className="flex items-center justify-between rounded-lg bg-zinc-50 px-4 py-2 dark:bg-zinc-900"
              >
                <span className="text-sm">
                  <span className="text-zinc-500">{scopeLabel(p.household_id, p.person_id)}:</span>{" "}
                  {p.item}{" "}
                  <span className="text-zinc-400">({p.preference})</span>
                </span>
                <button
                  onClick={() => deletePref(p.id)}
                  className="text-zinc-400 hover:text-red-500"
                >
                  &times;
                </button>
              </div>
            ))}
            {preferences.length === 0 && (
              <p className="text-sm text-zinc-400">No food preferences.</p>
            )}
          </div>
        </section>

        {/* Nutrition Goals */}
        <section className="mb-8 rounded-lg border border-zinc-200 p-6 dark:border-zinc-800">
          <h2 className="mb-4 text-xl font-semibold text-zinc-900 dark:text-zinc-100">
            Nutrition Goals
          </h2>
          <div className="flex flex-col gap-2">
            {goals.map((g) => (
              <div
                key={g.id}
                className="flex items-center justify-between rounded-lg bg-zinc-50 px-4 py-2 dark:bg-zinc-900"
              >
                <span className="text-sm">
                  <span className="text-zinc-500">{scopeLabel(g.household_id, g.person_id)}:</span>{" "}
                  {g.calories_min != null && `${g.calories_min}–`}
                  {g.calories_max != null && `${g.calories_max} cal`}
                  {g.protein_g != null && ` · ${g.protein_g}g protein`}
                  {g.carbs_g != null && ` · ${g.carbs_g}g carbs`}
                  {g.fat_g != null && ` · ${g.fat_g}g fat`}
                </span>
                <button
                  onClick={() => deleteGoal(g.id)}
                  className="text-zinc-400 hover:text-red-500"
                >
                  &times;
                </button>
              </div>
            ))}
            {goals.length === 0 && (
              <p className="text-sm text-zinc-400">No nutrition goals.</p>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
