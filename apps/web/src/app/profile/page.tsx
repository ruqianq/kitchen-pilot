"use client";

import { useEffect, useState } from "react";
import AllergyTag from "@/components/AllergyTag";
import Button from "@/components/Button";
import Input from "@/components/Input";
import PersonCard from "@/components/PersonCard";
import Select from "@/components/Select";
import type {
  Allergy,
  Biometric,
  DietaryRule,
  FoodPreference,
  GoogleAuthStatusResponse,
  HealthCondition,
  Household,
  NutritionGoal,
  Person,
} from "@/lib/api";
import { authApi, householdApi } from "@/lib/api";

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

const GENDERS = [
  { value: "", label: "Not specified" },
  { value: "male", label: "Male" },
  { value: "female", label: "Female" },
  { value: "other", label: "Other" },
  { value: "prefer_not_to_say", label: "Prefer not to say" },
];

const ACTIVITY_LEVELS = [
  { value: "", label: "Not specified" },
  { value: "sedentary", label: "Sedentary" },
  { value: "lightly_active", label: "Lightly Active" },
  { value: "active", label: "Active" },
  { value: "very_active", label: "Very Active" },
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

const COMMON_CONDITIONS = [
  "hypertension",
  "type_2_diabetes",
  "heart_disease",
  "high_cholesterol",
  "kidney_disease",
  "celiac",
  "gerd",
  "ibs",
  "gout",
  "pcos",
];

function parseScope(scope: string) {
  const [type, id] = scope.split(":");
  return type === "h" ? { household_id: id } : { person_id: id };
}

function formatCondition(condition: string) {
  return condition
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function ProfilePage() {
  const [household, setHousehold] = useState<Household | null>(null);
  const [people, setPeople] = useState<Person[]>([]);
  const [allergies, setAllergies] = useState<Allergy[]>([]);
  const [dietaryRules, setDietaryRules] = useState<DietaryRule[]>([]);
  const [preferences, setPreferences] = useState<FoodPreference[]>([]);
  const [goals, setGoals] = useState<NutritionGoal[]>([]);
  const [healthConditions, setHealthConditions] = useState<HealthCondition[]>([]);
  const [biometrics, setBiometrics] = useState<Record<string, Biometric | null>>({});
  const [loading, setLoading] = useState(true);

  // Google Calendar connection
  const [googleStatus, setGoogleStatus] = useState<GoogleAuthStatusResponse | null>(null);
  const [connectingGoogle, setConnectingGoogle] = useState(false);

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

  // Health profile editing
  const [editingHealthPersonId, setEditingHealthPersonId] = useState<string | null>(null);
  const [healthForm, setHealthForm] = useState({
    gender: "",
    date_of_birth: "",
    ethnicity: "",
    activity_level: "",
    height_cm: "",
    weight_kg: "",
  });
  const [newCondition, setNewCondition] = useState("");

  const scopeOptions = household
    ? [
        { value: `h:${household.id}`, label: "Household" },
        ...people.map((p) => ({ value: `p:${p.id}`, label: p.name })),
      ]
    : [];

  useEffect(() => {
    async function load() {
      try {
        const [h, p, a, dr, fp, ng, hc] = await Promise.all([
          householdApi.get(),
          householdApi.listPeople(),
          householdApi.listAllergies(),
          householdApi.listDietaryRules(),
          householdApi.listPreferences(),
          householdApi.listGoals(),
          householdApi.listHealthConditions(),
        ]);
        setHousehold(h);
        setPeople(p);
        setAllergies(a);
        setDietaryRules(dr);
        setPreferences(fp);
        setGoals(ng);
        setHealthConditions(hc);

        // Load biometrics for each person
        const bioEntries = await Promise.all(
          p.map(async (person) => {
            try {
              const bio = await householdApi.getBiometric(person.id);
              return [person.id, bio] as const;
            } catch {
              return [person.id, null] as const;
            }
          }),
        );
        setBiometrics(Object.fromEntries(bioEntries));
      } catch {
        // Not set up yet
      } finally {
        setLoading(false);
      }
      // Load Google Calendar status (non-blocking)
      authApi.googleStatus().then(setGoogleStatus).catch(() => {});
    }
    load();
  }, []);

  // Handle redirect back from Google OAuth
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("google") === "connected") {
      authApi.googleStatus().then(setGoogleStatus).catch(() => {});
      window.history.replaceState({}, "", "/profile");
    }
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
    setHealthConditions(healthConditions.filter((hc) => hc.person_id !== id));
    const newBio = { ...biometrics };
    delete newBio[id];
    setBiometrics(newBio);
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

  async function deleteCondition(id: string) {
    await householdApi.deleteHealthCondition(id);
    setHealthConditions(healthConditions.filter((hc) => hc.id !== id));
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

  // --- Health Profile handlers ---

  function startEditingHealth(person: Person) {
    const bio = biometrics[person.id];
    setEditingHealthPersonId(person.id);
    setHealthForm({
      gender: person.gender ?? "",
      date_of_birth: person.date_of_birth ?? "",
      ethnicity: person.ethnicity ?? "",
      activity_level: person.activity_level ?? "",
      height_cm: bio?.height_cm?.toString() ?? "",
      weight_kg: bio?.weight_kg?.toString() ?? "",
    });
    setNewCondition("");
  }

  async function saveHealthProfile(personId: string) {
    try {
      // Update person fields
      const updated = await householdApi.updatePerson(personId, {
        gender: healthForm.gender || null,
        date_of_birth: healthForm.date_of_birth || null,
        ethnicity: healthForm.ethnicity || null,
        activity_level: healthForm.activity_level || null,
      });
      setPeople(people.map((p) => (p.id === personId ? updated : p)));

      // Update biometrics if provided
      if (healthForm.height_cm || healthForm.weight_kg) {
        const bio = await householdApi.upsertBiometric(personId, {
          height_cm: healthForm.height_cm ? parseFloat(healthForm.height_cm) : undefined,
          weight_kg: healthForm.weight_kg ? parseFloat(healthForm.weight_kg) : undefined,
        });
        setBiometrics({ ...biometrics, [personId]: bio });
      }

      setEditingHealthPersonId(null);
    } catch {
      // ignore
    }
  }

  async function addCondition(personId: string) {
    if (!newCondition.trim()) return;
    try {
      const condition = await householdApi.createHealthCondition({
        person_id: personId,
        condition: newCondition.trim(),
      });
      setHealthConditions([...healthConditions, condition]);
      setNewCondition("");
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

        {/* Google Calendar */}
        <section className="mb-8 rounded-lg border border-zinc-200 p-6 dark:border-zinc-800">
          <h2 className="mb-4 text-xl font-semibold text-zinc-900 dark:text-zinc-100">
            Google Calendar
          </h2>
          {googleStatus?.connected ? (
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-green-600 dark:text-green-400">
                  Connected
                </p>
                {googleStatus.token_expiry && (
                  <p className="text-xs text-zinc-400">
                    Token expires: {new Date(googleStatus.token_expiry).toLocaleString()}
                  </p>
                )}
              </div>
              <Button
                variant="secondary"
                className="px-3 py-1 text-xs"
                onClick={async () => {
                  await authApi.googleDisconnect();
                  setGoogleStatus({ connected: false, scopes: null, token_expiry: null });
                }}
              >
                Disconnect
              </Button>
            </div>
          ) : (
            <div>
              <p className="mb-3 text-sm text-zinc-500">
                Connect your Google Calendar to publish meal plans as calendar events.
              </p>
              <Button
                onClick={async () => {
                  setConnectingGoogle(true);
                  try {
                    const { authorization_url } = await authApi.googleStart();
                    window.location.href = authorization_url;
                  } catch {
                    setConnectingGoogle(false);
                  }
                }}
                disabled={connectingGoogle}
              >
                {connectingGoogle ? "Redirecting..." : "Connect Google Calendar"}
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

        {/* Health Profiles */}
        {people.length > 0 && (
          <section className="mb-8 rounded-lg border border-zinc-200 p-6 dark:border-zinc-800">
            <h2 className="mb-4 text-xl font-semibold text-zinc-900 dark:text-zinc-100">
              Health Profiles
            </h2>
            <p className="mb-4 text-sm text-zinc-500">
              Add health data per person for personalized nutrition recommendations.
            </p>
            <div className="flex flex-col gap-4">
              {people.map((person) => {
                const bio = biometrics[person.id];
                const conditions = healthConditions.filter((hc) => hc.person_id === person.id);
                const isEditing = editingHealthPersonId === person.id;

                return (
                  <div
                    key={person.id}
                    className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800"
                  >
                    <div className="mb-3 flex items-center justify-between">
                      <h3 className="font-medium text-zinc-900 dark:text-zinc-100">
                        {person.name}
                      </h3>
                      <Button
                        variant="secondary"
                        className="px-3 py-1 text-xs"
                        onClick={() => {
                          if (isEditing) {
                            setEditingHealthPersonId(null);
                          } else {
                            startEditingHealth(person);
                          }
                        }}
                      >
                        {isEditing ? "Cancel" : "Edit"}
                      </Button>
                    </div>

                    {isEditing ? (
                      <div className="flex flex-col gap-3">
                        <div className="grid grid-cols-2 gap-3">
                          <Select
                            label="Gender"
                            options={GENDERS}
                            value={healthForm.gender}
                            onChange={(e) =>
                              setHealthForm({ ...healthForm, gender: e.target.value })
                            }
                          />
                          <Input
                            label="Date of Birth"
                            type="date"
                            value={healthForm.date_of_birth}
                            onChange={(e) =>
                              setHealthForm({ ...healthForm, date_of_birth: e.target.value })
                            }
                          />
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                          <Input
                            label="Ethnicity"
                            placeholder="e.g. Asian, Hispanic"
                            value={healthForm.ethnicity}
                            onChange={(e) =>
                              setHealthForm({ ...healthForm, ethnicity: e.target.value })
                            }
                          />
                          <Select
                            label="Activity Level"
                            options={ACTIVITY_LEVELS}
                            value={healthForm.activity_level}
                            onChange={(e) =>
                              setHealthForm({ ...healthForm, activity_level: e.target.value })
                            }
                          />
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                          <Input
                            label="Height (cm)"
                            type="number"
                            placeholder="e.g. 170"
                            value={healthForm.height_cm}
                            onChange={(e) =>
                              setHealthForm({ ...healthForm, height_cm: e.target.value })
                            }
                          />
                          <Input
                            label="Weight (kg)"
                            type="number"
                            placeholder="e.g. 70"
                            value={healthForm.weight_kg}
                            onChange={(e) =>
                              setHealthForm({ ...healthForm, weight_kg: e.target.value })
                            }
                          />
                        </div>

                        {/* Health Conditions */}
                        <div>
                          <label className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                            Health Conditions
                          </label>
                          <div className="mb-2 flex flex-wrap gap-2">
                            {conditions.map((hc) => (
                              <span
                                key={hc.id}
                                className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-800 dark:bg-amber-900/30 dark:text-amber-300"
                              >
                                {formatCondition(hc.condition)}
                                <button
                                  onClick={() => deleteCondition(hc.id)}
                                  className="ml-1 text-amber-600 hover:text-red-500 dark:text-amber-400"
                                >
                                  &times;
                                </button>
                              </span>
                            ))}
                          </div>
                          <div className="flex gap-2">
                            <select
                              className="flex-1 rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100"
                              value={newCondition}
                              onChange={(e) => setNewCondition(e.target.value)}
                            >
                              <option value="">Select condition...</option>
                              {COMMON_CONDITIONS.filter(
                                (c) => !conditions.some((hc) => hc.condition === c),
                              ).map((c) => (
                                <option key={c} value={c}>
                                  {formatCondition(c)}
                                </option>
                              ))}
                              <option value="__custom">Other (custom)...</option>
                            </select>
                            <Button
                              variant="secondary"
                              className="px-3 py-1 text-xs"
                              onClick={() => addCondition(person.id)}
                              disabled={!newCondition || newCondition === "__custom"}
                            >
                              Add
                            </Button>
                          </div>
                          {newCondition === "__custom" && (
                            <Input
                              label=""
                              placeholder="Enter condition name"
                              className="mt-2"
                              value=""
                              onChange={(e) => setNewCondition(e.target.value)}
                            />
                          )}
                        </div>

                        <Button onClick={() => saveHealthProfile(person.id)}>
                          Save Health Profile
                        </Button>
                      </div>
                    ) : (
                      <div className="text-sm text-zinc-600 dark:text-zinc-400">
                        <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                          {person.gender && (
                            <>
                              <span className="text-zinc-500">Gender:</span>
                              <span>{formatCondition(person.gender)}</span>
                            </>
                          )}
                          {person.date_of_birth && (
                            <>
                              <span className="text-zinc-500">DOB:</span>
                              <span>{person.date_of_birth}</span>
                            </>
                          )}
                          {person.activity_level && (
                            <>
                              <span className="text-zinc-500">Activity:</span>
                              <span>{formatCondition(person.activity_level)}</span>
                            </>
                          )}
                          {bio?.height_cm && (
                            <>
                              <span className="text-zinc-500">Height:</span>
                              <span>{bio.height_cm} cm</span>
                            </>
                          )}
                          {bio?.weight_kg && (
                            <>
                              <span className="text-zinc-500">Weight:</span>
                              <span>{bio.weight_kg} kg</span>
                            </>
                          )}
                          {bio?.bmi && (
                            <>
                              <span className="text-zinc-500">BMI:</span>
                              <span>{bio.bmi.toFixed(1)}</span>
                            </>
                          )}
                        </div>
                        {conditions.length > 0 && (
                          <div className="mt-2 flex flex-wrap gap-1">
                            {conditions.map((hc) => (
                              <span
                                key={hc.id}
                                className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-800 dark:bg-amber-900/30 dark:text-amber-300"
                              >
                                {formatCondition(hc.condition)}
                              </span>
                            ))}
                          </div>
                        )}
                        {!person.gender &&
                          !person.date_of_birth &&
                          !bio?.height_cm &&
                          conditions.length === 0 && (
                            <p className="text-zinc-400">
                              No health data yet. Click Edit to add.
                            </p>
                          )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        )}

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
                  {g.calories_min != null && `${g.calories_min}\u2013`}
                  {g.calories_max != null && `${g.calories_max} cal`}
                  {g.protein_g != null && ` \u00B7 ${g.protein_g}g protein`}
                  {g.carbs_g != null && ` \u00B7 ${g.carbs_g}g carbs`}
                  {g.fat_g != null && ` \u00B7 ${g.fat_g}g fat`}
                  {g.sodium_mg != null && ` \u00B7 ${g.sodium_mg}mg sodium`}
                  {g.sugar_g != null && ` \u00B7 ${g.sugar_g}g sugar`}
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
