"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Button from "@/components/Button";
import type { WeeklyPlanDetailResponse, MealResponse } from "@/lib/api";
import { planApi } from "@/lib/api";

const MEAL_ORDER: Record<string, number> = {
  breakfast: 0,
  lunch: 1,
  dinner: 2,
  snack: 3,
};

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400",
  confirmed: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  published: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  archived: "bg-zinc-200 text-zinc-500 dark:bg-zinc-700 dark:text-zinc-400",
};

function groupByDate(meals: MealResponse[]) {
  const grouped: Record<string, MealResponse[]> = {};
  for (const meal of meals) {
    if (!grouped[meal.date]) grouped[meal.date] = [];
    grouped[meal.date].push(meal);
  }
  return grouped;
}

export default function PlanDetailPage() {
  const params = useParams();
  const planId = params.id as string;
  const [plan, setPlan] = useState<WeeklyPlanDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [publishing, setPublishing] = useState(false);
  const [publishResult, setPublishResult] = useState<string | null>(null);

  useEffect(() => {
    planApi
      .get(planId)
      .then(setPlan)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [planId]);

  async function handlePublish() {
    setPublishing(true);
    setPublishResult(null);
    try {
      const res = await planApi.publish(planId);
      setPublishResult(
        `Published ${res.calendar_events_created} events to Google Calendar!`
      );
      const updated = await planApi.get(planId);
      setPlan(updated);
    } catch (e: unknown) {
      setPublishResult(e instanceof Error ? e.message : "Publish failed");
    } finally {
      setPublishing(false);
    }
  }

  async function handleDelete() {
    if (!confirm("Delete this plan?")) return;
    await planApi.delete(planId);
    window.location.href = "/plans";
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-50 dark:bg-black">
        <p className="text-zinc-500">Loading...</p>
      </div>
    );
  }

  if (!plan) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-50 dark:bg-black">
        <p className="text-zinc-500">Plan not found.</p>
      </div>
    );
  }

  const mealsByDate = groupByDate(plan.meals);
  const sortedDates = Object.keys(mealsByDate).sort();

  return (
    <div className="min-h-screen bg-zinc-50 p-8 dark:bg-black">
      <div className="mx-auto max-w-5xl">
        {/* Header */}
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-zinc-900 dark:text-zinc-50">
              Week of {plan.week_start_date}
            </h1>
            <span
              className={`mt-1 inline-block rounded-full px-3 py-1 text-xs font-medium ${STATUS_COLORS[plan.status] ?? ""}`}
            >
              {plan.status}
            </span>
          </div>
          <div className="flex gap-3">
            <a href="/plans">
              <Button variant="secondary">Back</Button>
            </a>
            <Button onClick={handlePublish} disabled={publishing}>
              {publishing ? "Publishing..." : "Publish to Calendar"}
            </Button>
            <Button variant="danger" onClick={handleDelete}>
              Delete
            </Button>
          </div>
        </div>

        {publishResult && (
          <p className="mb-4 text-sm text-green-600 dark:text-green-400">
            {publishResult}
          </p>
        )}

        {/* 7-Day Grid */}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {sortedDates.map((dateStr) => (
            <div
              key={dateStr}
              className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800"
            >
              <h3 className="mb-3 text-sm font-semibold text-zinc-500">
                {new Date(dateStr + "T00:00:00").toLocaleDateString("en-US", {
                  weekday: "long",
                  month: "short",
                  day: "numeric",
                })}
              </h3>
              <div className="flex flex-col gap-3">
                {mealsByDate[dateStr]
                  .sort(
                    (a, b) =>
                      (MEAL_ORDER[a.meal_type] ?? 4) -
                      (MEAL_ORDER[b.meal_type] ?? 4)
                  )
                  .map((meal) => {
                    const nutrition = meal.nutrition_json as {
                      calories?: number;
                    } | null;
                    return (
                      <div
                        key={meal.id}
                        className="rounded bg-white p-3 shadow-sm dark:bg-zinc-900"
                      >
                        <p className="text-xs font-medium uppercase text-zinc-400">
                          {meal.meal_type}
                        </p>
                        <p className="font-medium text-zinc-900 dark:text-zinc-100">
                          {meal.title}
                        </p>
                        <div className="mt-1 flex gap-2 text-xs text-zinc-500">
                          {meal.cook_time_min != null && (
                            <span>{meal.cook_time_min} min</span>
                          )}
                          {meal.servings != null && (
                            <span>{meal.servings} servings</span>
                          )}
                          {nutrition?.calories != null && (
                            <span>{nutrition.calories} cal</span>
                          )}
                        </div>
                      </div>
                    );
                  })}
              </div>
            </div>
          ))}
        </div>

        {/* Shopping List */}
        {plan.shopping_list?.items_json && (
          <section className="mt-8 rounded-lg border border-zinc-200 p-6 dark:border-zinc-800">
            <h2 className="mb-4 text-xl font-semibold text-zinc-900 dark:text-zinc-100">
              Shopping List
            </h2>
            <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
              {(
                plan.shopping_list.items_json as {
                  name: string;
                  quantity: number;
                  unit: string;
                  category: string;
                }[]
              ).map((item, i) => (
                <label
                  key={i}
                  className="flex items-center gap-2 text-sm text-zinc-700 dark:text-zinc-300"
                >
                  <input type="checkbox" className="rounded" />
                  <span>
                    {item.quantity} {item.unit} {item.name}
                  </span>
                  <span className="text-xs text-zinc-400">({item.category})</span>
                </label>
              ))}
            </div>
          </section>
        )}

        {/* Summary */}
        {plan.summary_md && (
          <section className="mt-8 rounded-lg border border-zinc-200 p-6 dark:border-zinc-800">
            <h2 className="mb-4 text-xl font-semibold text-zinc-900 dark:text-zinc-100">
              Summary
            </h2>
            <pre className="whitespace-pre-wrap text-sm text-zinc-600 dark:text-zinc-400">
              {plan.summary_md}
            </pre>
          </section>
        )}
      </div>
    </div>
  );
}
