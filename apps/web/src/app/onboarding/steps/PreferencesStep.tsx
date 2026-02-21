"use client";

import { useEffect, useState } from "react";
import Button from "@/components/Button";
import Input from "@/components/Input";
import Select from "@/components/Select";
import type { DietaryRule, FoodPreference, Household, NutritionGoal, Person } from "@/lib/api";
import { householdApi } from "@/lib/api";

const PREFERENCE_LEVELS = [
  { value: "like", label: "Like" },
  { value: "dislike", label: "Dislike" },
  { value: "avoid", label: "Avoid" },
  { value: "favorite", label: "Favorite" },
];

interface PreferencesStepProps {
  household: Household;
  people: Person[];
  onFinish: () => void;
  onBack: () => void;
}

export default function PreferencesStep({
  household,
  people,
  onFinish,
  onBack,
}: PreferencesStepProps) {
  const [dietaryRules, setDietaryRules] = useState<DietaryRule[]>([]);
  const [preferences, setPreferences] = useState<FoodPreference[]>([]);
  const [goals, setGoals] = useState<NutritionGoal[]>([]);
  const [error, setError] = useState("");

  const scopeOptions = [
    { value: `h:${household.id}`, label: "Household" },
    ...people.map((p) => ({ value: `p:${p.id}`, label: p.name })),
  ];

  useEffect(() => {
    householdApi.listDietaryRules().then(setDietaryRules).catch(() => {});
    householdApi.listPreferences().then(setPreferences).catch(() => {});
    householdApi.listGoals().then(setGoals).catch(() => {});
  }, []);

  function parseScope(scope: string) {
    const [type, id] = scope.split(":");
    return type === "h" ? { household_id: id } : { person_id: id };
  }

  // --- Dietary Rules ---
  const [ruleScope, setRuleScope] = useState(scopeOptions[0]?.value ?? "");
  const [ruleText, setRuleText] = useState("");

  async function addRule(e: React.FormEvent) {
    e.preventDefault();
    if (!ruleText.trim()) return;
    try {
      const rule = await householdApi.createDietaryRule({
        ...parseScope(ruleScope),
        rule: ruleText.trim(),
      });
      setDietaryRules([...dietaryRules, rule]);
      setRuleText("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add rule");
    }
  }

  // --- Food Preferences ---
  const [prefScope, setPrefScope] = useState(scopeOptions[0]?.value ?? "");
  const [prefItem, setPrefItem] = useState("");
  const [prefLevel, setPrefLevel] = useState("like");

  async function addPreference(e: React.FormEvent) {
    e.preventDefault();
    if (!prefItem.trim()) return;
    try {
      const pref = await householdApi.createPreference({
        ...parseScope(prefScope),
        item: prefItem.trim(),
        preference: prefLevel,
      });
      setPreferences([...preferences, pref]);
      setPrefItem("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add preference");
    }
  }

  // --- Nutrition Goals ---
  const [goalScope, setGoalScope] = useState(scopeOptions[0]?.value ?? "");
  const [caloriesMin, setCaloriesMin] = useState("");
  const [caloriesMax, setCaloriesMax] = useState("");

  async function addGoal(e: React.FormEvent) {
    e.preventDefault();
    try {
      const goal = await householdApi.createGoal({
        ...parseScope(goalScope),
        calories_min: caloriesMin ? Number(caloriesMin) : undefined,
        calories_max: caloriesMax ? Number(caloriesMax) : undefined,
      });
      setGoals([...goals, goal]);
      setCaloriesMin("");
      setCaloriesMax("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add goal");
    }
  }

  return (
    <div className="mt-6 flex flex-col gap-8">
      {error && <p className="text-sm text-red-500">{error}</p>}

      {/* Dietary Rules */}
      <section>
        <h3 className="mb-3 text-lg font-medium text-stone-800 dark:text-stone-100">
          Dietary Rules
        </h3>
        <div className="mb-3 flex flex-wrap gap-2">
          {dietaryRules.map((r) => (
            <span
              key={r.id}
              className="inline-flex items-center gap-1 rounded-full bg-stone-100 px-3 py-1 text-xs dark:bg-stone-800"
            >
              {r.rule}
              <button
                onClick={async () => {
                  await householdApi.deleteDietaryRule(r.id);
                  setDietaryRules(dietaryRules.filter((x) => x.id !== r.id));
                }}
                className="ml-1 text-stone-400 hover:text-stone-600"
              >
                &times;
              </button>
            </span>
          ))}
        </div>
        <form onSubmit={addRule} className="flex items-end gap-3">
          <Select label="Scope" options={scopeOptions} value={ruleScope} onChange={(e) => setRuleScope(e.target.value)} />
          <Input label="Rule" placeholder="e.g. vegetarian" value={ruleText} onChange={(e) => setRuleText(e.target.value)} />
          <Button type="submit" variant="secondary" className="whitespace-nowrap">Add</Button>
        </form>
      </section>

      {/* Food Preferences */}
      <section>
        <h3 className="mb-3 text-lg font-medium text-stone-800 dark:text-stone-100">
          Food Preferences
        </h3>
        <div className="mb-3 flex flex-wrap gap-2">
          {preferences.map((p) => (
            <span
              key={p.id}
              className="inline-flex items-center gap-1 rounded-full bg-stone-100 px-3 py-1 text-xs dark:bg-stone-800"
            >
              {p.item} ({p.preference})
              <button
                onClick={async () => {
                  await householdApi.deletePreference(p.id);
                  setPreferences(preferences.filter((x) => x.id !== p.id));
                }}
                className="ml-1 text-stone-400 hover:text-stone-600"
              >
                &times;
              </button>
            </span>
          ))}
        </div>
        <form onSubmit={addPreference} className="flex items-end gap-3">
          <Select label="Scope" options={scopeOptions} value={prefScope} onChange={(e) => setPrefScope(e.target.value)} />
          <Input label="Food Item" placeholder="e.g. sushi" value={prefItem} onChange={(e) => setPrefItem(e.target.value)} />
          <Select label="Level" options={PREFERENCE_LEVELS} value={prefLevel} onChange={(e) => setPrefLevel(e.target.value)} />
          <Button type="submit" variant="secondary" className="whitespace-nowrap">Add</Button>
        </form>
      </section>

      {/* Nutrition Goals */}
      <section>
        <h3 className="mb-3 text-lg font-medium text-stone-800 dark:text-stone-100">
          Nutrition Goals
        </h3>
        <div className="mb-3 flex flex-col gap-2">
          {goals.map((g) => (
            <div
              key={g.id}
              className="flex items-center justify-between rounded-lg border border-stone-200 px-3 py-2 text-sm dark:border-stone-800"
            >
              <span>
                {g.calories_min && `${g.calories_min}–`}
                {g.calories_max && `${g.calories_max} cal`}
                {g.protein_g && ` · ${g.protein_g}g protein`}
              </span>
              <button
                onClick={async () => {
                  await householdApi.deleteGoal(g.id);
                  setGoals(goals.filter((x) => x.id !== g.id));
                }}
                className="text-stone-400 hover:text-red-500"
              >
                &times;
              </button>
            </div>
          ))}
        </div>
        <form onSubmit={addGoal} className="flex items-end gap-3">
          <Select label="Scope" options={scopeOptions} value={goalScope} onChange={(e) => setGoalScope(e.target.value)} />
          <Input label="Min Calories" type="number" placeholder="1800" value={caloriesMin} onChange={(e) => setCaloriesMin(e.target.value)} />
          <Input label="Max Calories" type="number" placeholder="2200" value={caloriesMax} onChange={(e) => setCaloriesMax(e.target.value)} />
          <Button type="submit" variant="secondary" className="whitespace-nowrap">Add</Button>
        </form>
      </section>

      <div className="flex justify-between">
        <Button variant="secondary" onClick={onBack}>Back</Button>
        <Button onClick={onFinish}>Finish Setup</Button>
      </div>
    </div>
  );
}
