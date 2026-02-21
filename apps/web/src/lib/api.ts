const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail.detail ?? `API error ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// --- Types ---

export interface Household {
  id: string;
  name: string;
  timezone: string;
  created_at: string;
  updated_at: string;
}

export interface Person {
  id: string;
  household_id: string;
  name: string;
  role: string;
  age_band: string | null;
  gender: string | null;
  date_of_birth: string | null;
  ethnicity: string | null;
  activity_level: string | null;
  created_at: string;
  updated_at: string;
}

export interface Allergy {
  id: string;
  person_id: string;
  allergen: string;
  severity: "mild" | "moderate" | "severe";
  notes: string | null;
  created_at: string;
}

export interface DietaryRule {
  id: string;
  household_id: string | null;
  person_id: string | null;
  rule: string;
  notes: string | null;
  created_at: string;
}

export interface FoodPreference {
  id: string;
  household_id: string | null;
  person_id: string | null;
  item: string;
  preference: "like" | "dislike" | "avoid" | "favorite";
  notes: string | null;
  created_at: string;
}

export interface NutritionGoal {
  id: string;
  household_id: string | null;
  person_id: string | null;
  calories_min: number | null;
  calories_max: number | null;
  protein_g: number | null;
  carbs_g: number | null;
  fat_g: number | null;
  fiber_g: number | null;
  sodium_mg: number | null;
  cholesterol_mg: number | null;
  sugar_g: number | null;
  saturated_fat_g: number | null;
  potassium_mg: number | null;
  created_at: string;
  updated_at: string;
}

export interface Biometric {
  id: string;
  person_id: string;
  height_cm: number | null;
  weight_kg: number | null;
  bmi: number | null;
  waist_cm: number | null;
  created_at: string;
  updated_at: string;
}

export interface HealthCondition {
  id: string;
  person_id: string;
  condition: string;
  severity: string | null;
  notes: string | null;
  created_at: string;
}

// --- API ---

export const householdApi = {
  get: () => apiFetch<Household>("/household"),
  update: (id: string, data: { name?: string; timezone?: string }) =>
    apiFetch<Household>(`/household/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  listPeople: () => apiFetch<Person[]>("/household/people"),
  createPerson: (data: {
    name: string;
    role: string;
    age_band?: string;
    gender?: string;
    date_of_birth?: string;
    ethnicity?: string;
    activity_level?: string;
  }) =>
    apiFetch<Person>("/household/people", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updatePerson: (id: string, data: {
    name?: string;
    role?: string;
    age_band?: string | null;
    gender?: string | null;
    date_of_birth?: string | null;
    ethnicity?: string | null;
    activity_level?: string | null;
  }) =>
    apiFetch<Person>(`/household/people/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  deletePerson: (id: string) =>
    apiFetch<void>(`/household/people/${id}`, { method: "DELETE" }),

  listAllergies: () => apiFetch<Allergy[]>("/household/allergies"),
  createAllergy: (data: {
    person_id: string;
    allergen: string;
    severity: string;
    notes?: string;
  }) =>
    apiFetch<Allergy>("/household/allergies", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  deleteAllergy: (id: string) =>
    apiFetch<void>(`/household/allergies/${id}`, { method: "DELETE" }),

  listDietaryRules: () => apiFetch<DietaryRule[]>("/household/dietary-rules"),
  createDietaryRule: (data: {
    household_id?: string;
    person_id?: string;
    rule: string;
    notes?: string;
  }) =>
    apiFetch<DietaryRule>("/household/dietary-rules", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  deleteDietaryRule: (id: string) =>
    apiFetch<void>(`/household/dietary-rules/${id}`, { method: "DELETE" }),

  listPreferences: () => apiFetch<FoodPreference[]>("/household/preferences"),
  createPreference: (data: {
    household_id?: string;
    person_id?: string;
    item: string;
    preference: string;
    notes?: string;
  }) =>
    apiFetch<FoodPreference>("/household/preferences", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  deletePreference: (id: string) =>
    apiFetch<void>(`/household/preferences/${id}`, { method: "DELETE" }),

  listGoals: () => apiFetch<NutritionGoal[]>("/household/goals"),
  createGoal: (data: {
    household_id?: string;
    person_id?: string;
    calories_min?: number;
    calories_max?: number;
    protein_g?: number;
    carbs_g?: number;
    fat_g?: number;
    fiber_g?: number;
    sodium_mg?: number;
    cholesterol_mg?: number;
    sugar_g?: number;
    saturated_fat_g?: number;
    potassium_mg?: number;
  }) =>
    apiFetch<NutritionGoal>("/household/goals", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  deleteGoal: (id: string) =>
    apiFetch<void>(`/household/goals/${id}`, { method: "DELETE" }),

  // Biometrics
  getBiometric: (personId: string) =>
    apiFetch<Biometric | null>(`/household/people/${personId}/biometrics`),
  upsertBiometric: (personId: string, data: {
    height_cm?: number;
    weight_kg?: number;
    waist_cm?: number;
  }) =>
    apiFetch<Biometric>(`/household/people/${personId}/biometrics`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Health Conditions
  listHealthConditions: () =>
    apiFetch<HealthCondition[]>("/household/health-conditions"),
  createHealthCondition: (data: {
    person_id: string;
    condition: string;
    severity?: string;
    notes?: string;
  }) =>
    apiFetch<HealthCondition>("/household/health-conditions", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  deleteHealthCondition: (id: string) =>
    apiFetch<void>(`/household/health-conditions/${id}`, { method: "DELETE" }),
};

// --- Plan Types ---

export interface MealResponse {
  id: string;
  date: string;
  meal_type: string;
  title: string;
  recipe_source_url: string | null;
  cook_time_min: number | null;
  servings: number | null;
  ingredients_json: Record<string, unknown>[] | null;
  nutrition_json: Record<string, unknown> | null;
  flags_json: Record<string, unknown> | null;
}

export interface ShoppingListResponse {
  id: string;
  items_json: { name: string; quantity: number; unit: string; category: string }[] | null;
  exports_json: Record<string, unknown> | null;
}

export interface WeeklyPlanResponse {
  id: string;
  household_id: string;
  week_start_date: string;
  status: "draft" | "confirmed" | "published" | "archived";
  plan_json: Record<string, unknown> | null;
  summary_md: string | null;
  model_info_json: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface WeeklyPlanDetailResponse extends WeeklyPlanResponse {
  meals: MealResponse[];
  shopping_list: ShoppingListResponse | null;
}

export interface PlanGenerateResponse {
  plan: WeeklyPlanDetailResponse;
  warnings: string[];
  errors: string[];
}

export interface PlanPublishResponse {
  plan_id: string;
  status: string;
  calendar_events_created: number;
  calendar_event_ids: string[];
}

export interface ShoppingItemWithLinks {
  name: string;
  quantity: number;
  unit: string;
  category: string;
  checked: boolean;
  retailer_links: { walmart: string; instacart: string; google: string };
}

export interface ShoppingListDetailResponse {
  id: string;
  items: ShoppingItemWithLinks[];
  checked_indices: number[];
}

// --- Plan API ---

export const planApi = {
  generate: (data: {
    week_start_date: string;
    overrides?: { constraint_type: string; description: string; acknowledged_at: string }[];
    max_cook_time_min?: number;
    notes?: string;
  }) =>
    apiFetch<PlanGenerateResponse>("/plan/generate", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  list: (limit = 20, offset = 0) =>
    apiFetch<WeeklyPlanResponse[]>(`/plan?limit=${limit}&offset=${offset}`),

  get: (id: string) => apiFetch<WeeklyPlanDetailResponse>(`/plan/${id}`),

  getShoppingList: (planId: string) =>
    apiFetch<ShoppingListResponse>(`/plan/${planId}/shopping-list`),

  publish: (planId: string, calendarId = "primary") =>
    apiFetch<PlanPublishResponse>("/plan/publish", {
      method: "POST",
      body: JSON.stringify({ plan_id: planId, calendar_id: calendarId }),
    }),

  delete: (id: string) => apiFetch<void>(`/plan/${id}`, { method: "DELETE" }),

  getShoppingDetail: (planId: string) =>
    apiFetch<ShoppingListDetailResponse>(`/plan/${planId}/shopping-list/detail`),

  updateChecklist: (planId: string, checkedIndices: number[]) =>
    apiFetch<{ checked_indices: number[] }>(`/plan/${planId}/shopping-list/checklist`, {
      method: "PATCH",
      body: JSON.stringify({ checked_indices: checkedIndices }),
    }),

  exportCsv: (planId: string) =>
    fetch(`${API_BASE}/plan/${planId}/shopping-list/export/csv`).then((res) => {
      if (!res.ok) throw new Error("Export failed");
      return res.blob();
    }),
};

// --- Auth Types ---

export interface GoogleAuthStartResponse {
  authorization_url: string;
}

export interface GoogleAuthStatusResponse {
  connected: boolean;
  scopes: string[] | null;
  token_expiry: string | null;
}

export interface GoogleDisconnectResponse {
  disconnected: boolean;
}

// --- Auth API ---

export const authApi = {
  googleStart: () =>
    apiFetch<GoogleAuthStartResponse>("/auth/google/start"),

  googleStatus: () =>
    apiFetch<GoogleAuthStatusResponse>("/auth/google/status"),

  googleDisconnect: () =>
    apiFetch<GoogleDisconnectResponse>("/auth/google/disconnect", {
      method: "POST",
    }),
};

// --- Chat Types ---

export interface PlanMeta {
  type: "plan_preview";
  week_start: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  planMeta?: PlanMeta;
}

// --- Chat API ---

export const chatApi = {
  /**
   * Sends a chat message and streams the response via SSE.
   * Returns an AbortController so the caller can cancel the stream.
   */
  streamChat(
    message: string,
    history: ChatMessage[],
    onToken: (token: string) => void,
    onDone: () => void,
    onError: (error: Error) => void,
    onPlanMeta?: (meta: PlanMeta) => void,
  ): AbortController {
    const controller = new AbortController();

    fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        history: history.map((m) => ({ role: m.role, content: m.content })),
      }),
      signal: controller.signal,
    })
      .then(async (res) => {
        if (!res.ok) {
          const detail = await res.json().catch(() => ({ detail: res.statusText }));
          throw new Error(detail.detail ?? `API error ${res.status}`);
        }
        const reader = res.body?.getReader();
        if (!reader) throw new Error("No response body");

        const decoder = new TextDecoder();
        let buffer = "";

        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed || trimmed.startsWith(":")) continue;
            if (trimmed.startsWith("data: ")) {
              const jsonStr = trimmed.slice(6);
              if (jsonStr === "[DONE]") continue;
              try {
                const parsed = JSON.parse(jsonStr);
                if (parsed.type === "plan_preview" && onPlanMeta) {
                  onPlanMeta(parsed as PlanMeta);
                } else if (parsed.content) {
                  onToken(parsed.content);
                }
              } catch {
                // skip malformed chunks
              }
            }
          }
        }
        onDone();
      })
      .catch((err) => {
        if (err.name !== "AbortError") {
          onError(err instanceof Error ? err : new Error(String(err)));
        }
      });

    return controller;
  },
};

// --- Voice API ---

export const voiceApi = {
  stt: async (audioBlob: Blob): Promise<{ text: string; language: string | null }> => {
    const form = new FormData();
    form.append("file", audioBlob, "recording.webm");
    const res = await fetch(`${API_BASE}/voice/stt`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) {
      const detail = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(detail.detail ?? "Transcription failed");
    }
    return res.json();
  },

  tts: async (text: string, voice = "nova", speed = 1.0): Promise<Blob> => {
    const res = await fetch(`${API_BASE}/voice/tts`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, voice, speed }),
    });
    if (!res.ok) {
      const detail = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(detail.detail ?? "Speech synthesis failed");
    }
    return res.blob();
  },
};

// --- Search Types ---

export interface RecipeSearchResult {
  title: string;
  url: string;
  snippet: string;
  source: string;
  score: number;
}

export interface RecipeSearchResponse {
  results: RecipeSearchResult[];
  query: string;
  provider: string;
}

// --- Search API ---

export const searchApi = {
  recipes: (query: string, maxResults = 5) =>
    apiFetch<RecipeSearchResponse>(
      `/search/recipes?q=${encodeURIComponent(query)}&max_results=${maxResults}`,
    ),
};
