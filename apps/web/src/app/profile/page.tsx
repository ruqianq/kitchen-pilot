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

const SEVERITIES = [
  { value: "mild", label: "Mild" },
  { value: "moderate", label: "Moderate" },
  { value: "severe", label: "Severe" },
];

const PREFERENCE_LEVELS = [
  { value: "like", label: "Like" },
  { value: "dislike", label: "Dislike" },
  { value: "avoid", label: "Avoid" },
  { value: "favorite", label: "Favorite" },
];

function parseScope(scope: string) {
  const [type, id] = scope.split(":");
  return type === "h" ? { household_id: id } : { person_id: id };
}

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

  // Add Person form
  const [showAddPerson, setShowAddPerson] = useState(false);
  const [newPersonName, setNewPersonName] = useState("");
  const [newPersonRole, setNewPersonRole] = useState("adult");
  const [newPersonAgeBand, setNewPersonAgeBand] = useState("");

  // Add Allergy form
  const [showAddAllergy, setShowAddAllergy] = useState(false);
  const [allergyPerson, setAllergyPerson] = useState("");
  const [allergyAllergen, setAllergyAllergen] = useState("");
  const [allergySeverity, setAllergySeverity] = useState("moderate");

  // Add Dietary Rule form
  const [showAddRule, setShowAddRule] = useState(false);
  const [ruleScope, setRuleScope] = useState("");
  const [ruleText, setRuleText] = useState("");

  // Add Food Preference form
  const [showAddPref, setShowAddPref] = useState(false);
  const [prefScope, setPrefScope] = useState("");
  const [prefItem, setPrefItem] = useState("");
  const [prefLevel, setPrefLevel] = useState("like");

  // Add Nutrition Goal form
  const [showAddGoal, setShowAddGoal] = useState(false);
  const [goalScope, setGoalScope] = useState("");
  const [goalCalMin, setGoalCalMin] = useState("");
  const [goalCalMax, setGoalCalMax] = useState("");

  const scopeOptions = household
    ? [
        { value: `h:${household.id}`, label: "Household" },
        ...people.map((p) => ({ value: `p:${p.id}`, label: p.name })),
      ]
    : [];

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

  // --- Delete handlers ---

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

  // --- Add handlers ---

  async function addPerson(e: React.FormEvent) {
    e.preventDefault();
    if (!newPersonName.trim()) return;
    try {
      const person = await householdApi.createPerson({
        name: newPersonName.trim(),
        role: newPersonRole,
        age_band: newPersonAgeBand || undefined,
      });
      setPeople([...people, person]);
      setNewPersonName("");
      setNewPersonRole("adult");
      setNewPersonAgeBand("");
      setShowAddPerson(false);
    } catch {
      // ignore
    }
  }

  async function addAllergy(e: React.FormEvent) {
    e.preventDefault();
    if (!allergyAllergen.trim() || !allergyPerson) return;
    try {
      const allergy = await householdApi.createAllergy({
        person_id: allergyPerson,
        allergen: allergyAllergen.trim(),
        severity: allergySeverity,
      });
      setAllergies([...allergies, allergy]);
      setAllergyAllergen("");
      setShowAddAllergy(false);
    } catch {
      // ignore
    }
  }

  async function addRule(e: React.FormEvent) {
    e.preventDefault();
    if (!ruleText.trim() || !ruleScope) return;
    try {
      const rule = await householdApi.createDietaryRule({
        ...parseScope(ruleScope),
        rule: ruleText.trim(),
      });
      setDietaryRules([...dietaryRules, rule]);
      setRuleText("");
      setShowAddRule(false);
    } catch {
      // ignore
    }
  }

  async function addPref(e: React.FormEvent) {
    e.preventDefault();
    if (!prefItem.trim() || !prefScope) return;
    try {
      const pref = await householdApi.createPreference({
        ...parseScope(prefScope),
        item: prefItem.trim(),
        preference: prefLevel,
      });
      setPreferences([...preferences, pref]);
      setPrefItem("");
      setShowAddPref(false);
    } catch {
      // ignore
    }
  }

  async function addGoal(e: React.FormEvent) {
    e.preventDefault();
    if (!goalScope) return;
    try {
      const goal = await householdApi.createGoal({
        ...parseScope(goalScope),
        calories_min: goalCalMin ? parseInt(goalCalMin) : undefined,
        calories_max: goalCalMax ? parseInt(goalCalMax) : undefined,
      });
      setGoals([...goals, goal]);
      setGoalCalMin("");
      setGoalCalMax("");
      setShowAddGoal(false);
    } catch {
      // ignore
    }
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
        <h1 className="mb-8 text-3xl font-bold text-zinc-900 dark:text-zinc-50">
          Household Profile
        </h1>

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
            <Button
              variant="secondary"
              className="px-3 py-1 text-xs"
              onClick={() => setShowAddPerson(!showAddPerson)}
            >
              {showAddPerson ? "Cancel" : "Add"}
            </Button>
          </div>
          <div className="flex flex-col gap-3">
            {people.map((p) => (
              <PersonCard key={p.id} person={p} onDelete={deletePerson} />
            ))}
          </div>
          {showAddPerson && (
            <form
              onSubmit={addPerson}
              className="mt-4 rounded-lg border border-dashed border-zinc-300 p-4 dark:border-zinc-700"
            >
              <div className="flex flex-col gap-3">
                <Input
                  label="Name"
                  placeholder="e.g. Alice"
                  value={newPersonName}
                  onChange={(e) => setNewPersonName(e.target.value)}
                />
                <div className="grid grid-cols-2 gap-3">
                  <Select
                    label="Role"
                    options={ROLES}
                    value={newPersonRole}
                    onChange={(e) => setNewPersonRole(e.target.value)}
                  />
                  <Select
                    label="Age Band"
                    options={AGE_BANDS}
                    value={newPersonAgeBand}
                    onChange={(e) => setNewPersonAgeBand(e.target.value)}
                  />
                </div>
                <Button type="submit" disabled={!newPersonName.trim()}>
                  Add Person
                </Button>
              </div>
            </form>
          )}
        </section>

        {/* Allergies */}
        <section className="mb-8 rounded-lg border border-zinc-200 p-6 dark:border-zinc-800">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
              Allergies
            </h2>
            <Button
              variant="secondary"
              className="px-3 py-1 text-xs"
              onClick={() => {
                setShowAddAllergy(!showAddAllergy);
                if (!showAddAllergy && people.length > 0) setAllergyPerson(people[0].id);
              }}
              disabled={people.length === 0}
            >
              {showAddAllergy ? "Cancel" : "Add"}
            </Button>
          </div>
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
          {showAddAllergy && (
            <form
              onSubmit={addAllergy}
              className="mt-4 rounded-lg border border-dashed border-zinc-300 p-4 dark:border-zinc-700"
            >
              <div className="flex flex-col gap-3">
                <Select
                  label="Person"
                  options={people.map((p) => ({ value: p.id, label: p.name }))}
                  value={allergyPerson}
                  onChange={(e) => setAllergyPerson(e.target.value)}
                />
                <div className="grid grid-cols-2 gap-3">
                  <Input
                    label="Allergen"
                    placeholder="e.g. Peanuts"
                    value={allergyAllergen}
                    onChange={(e) => setAllergyAllergen(e.target.value)}
                  />
                  <Select
                    label="Severity"
                    options={SEVERITIES}
                    value={allergySeverity}
                    onChange={(e) => setAllergySeverity(e.target.value)}
                  />
                </div>
                <Button type="submit" disabled={!allergyAllergen.trim()}>
                  Add Allergy
                </Button>
              </div>
            </form>
          )}
        </section>

        {/* Dietary Rules */}
        <section className="mb-8 rounded-lg border border-zinc-200 p-6 dark:border-zinc-800">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
              Dietary Rules
            </h2>
            <Button
              variant="secondary"
              className="px-3 py-1 text-xs"
              onClick={() => {
                setShowAddRule(!showAddRule);
                if (!showAddRule && scopeOptions.length > 0) setRuleScope(scopeOptions[0].value);
              }}
            >
              {showAddRule ? "Cancel" : "Add"}
            </Button>
          </div>
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
          {showAddRule && (
            <form
              onSubmit={addRule}
              className="mt-4 rounded-lg border border-dashed border-zinc-300 p-4 dark:border-zinc-700"
            >
              <div className="flex flex-col gap-3">
                <Select
                  label="Applies to"
                  options={scopeOptions}
                  value={ruleScope}
                  onChange={(e) => setRuleScope(e.target.value)}
                />
                <Input
                  label="Rule"
                  placeholder="e.g. No red meat"
                  value={ruleText}
                  onChange={(e) => setRuleText(e.target.value)}
                />
                <Button type="submit" disabled={!ruleText.trim()}>
                  Add Rule
                </Button>
              </div>
            </form>
          )}
        </section>

        {/* Food Preferences */}
        <section className="mb-8 rounded-lg border border-zinc-200 p-6 dark:border-zinc-800">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
              Food Preferences
            </h2>
            <Button
              variant="secondary"
              className="px-3 py-1 text-xs"
              onClick={() => {
                setShowAddPref(!showAddPref);
                if (!showAddPref && scopeOptions.length > 0) setPrefScope(scopeOptions[0].value);
              }}
            >
              {showAddPref ? "Cancel" : "Add"}
            </Button>
          </div>
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
          {showAddPref && (
            <form
              onSubmit={addPref}
              className="mt-4 rounded-lg border border-dashed border-zinc-300 p-4 dark:border-zinc-700"
            >
              <div className="flex flex-col gap-3">
                <Select
                  label="Applies to"
                  options={scopeOptions}
                  value={prefScope}
                  onChange={(e) => setPrefScope(e.target.value)}
                />
                <div className="grid grid-cols-2 gap-3">
                  <Input
                    label="Food item"
                    placeholder="e.g. Broccoli"
                    value={prefItem}
                    onChange={(e) => setPrefItem(e.target.value)}
                  />
                  <Select
                    label="Preference"
                    options={PREFERENCE_LEVELS}
                    value={prefLevel}
                    onChange={(e) => setPrefLevel(e.target.value)}
                  />
                </div>
                <Button type="submit" disabled={!prefItem.trim()}>
                  Add Preference
                </Button>
              </div>
            </form>
          )}
        </section>

        {/* Nutrition Goals */}
        <section className="mb-8 rounded-lg border border-zinc-200 p-6 dark:border-zinc-800">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
              Nutrition Goals
            </h2>
            <Button
              variant="secondary"
              className="px-3 py-1 text-xs"
              onClick={() => {
                setShowAddGoal(!showAddGoal);
                if (!showAddGoal && scopeOptions.length > 0) setGoalScope(scopeOptions[0].value);
              }}
            >
              {showAddGoal ? "Cancel" : "Add"}
            </Button>
          </div>
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
          {showAddGoal && (
            <form
              onSubmit={addGoal}
              className="mt-4 rounded-lg border border-dashed border-zinc-300 p-4 dark:border-zinc-700"
            >
              <div className="flex flex-col gap-3">
                <Select
                  label="Applies to"
                  options={scopeOptions}
                  value={goalScope}
                  onChange={(e) => setGoalScope(e.target.value)}
                />
                <div className="grid grid-cols-2 gap-3">
                  <Input
                    label="Min calories"
                    type="number"
                    placeholder="e.g. 1800"
                    value={goalCalMin}
                    onChange={(e) => setGoalCalMin(e.target.value)}
                  />
                  <Input
                    label="Max calories"
                    type="number"
                    placeholder="e.g. 2200"
                    value={goalCalMax}
                    onChange={(e) => setGoalCalMax(e.target.value)}
                  />
                </div>
                <Button type="submit">Add Goal</Button>
              </div>
            </form>
          )}
        </section>
      </div>
    </div>
  );
}
