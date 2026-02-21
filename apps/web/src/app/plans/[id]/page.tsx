"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Button from "@/components/Button";
import type { WeeklyPlanDetailResponse, MealResponse, ShoppingItemWithLinks } from "@/lib/api";
import { planApi } from "@/lib/api";

const MEAL_ORDER: Record<string, number> = {
  breakfast: 0,
  lunch: 1,
  dinner: 2,
  snack: 3,
};

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-stone-100 text-stone-600 dark:bg-stone-800 dark:text-stone-400",
  confirmed: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  published: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  archived: "bg-stone-200 text-stone-500 dark:bg-stone-700 dark:text-stone-400",
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
  const [shoppingItems, setShoppingItems] = useState<ShoppingItemWithLinks[]>([]);
  const [checkedSet, setCheckedSet] = useState<Set<number>>(new Set());

  useEffect(() => {
    planApi
      .get(planId)
      .then((p) => {
        setPlan(p);
        return planApi.getShoppingDetail(planId);
      })
      .then((detail) => {
        setShoppingItems(detail.items);
        setCheckedSet(new Set(detail.checked_indices));
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [planId]);

  const handleCheckToggle = useCallback(
    (index: number) => {
      setCheckedSet((prev) => {
        const next = new Set(prev);
        if (next.has(index)) next.delete(index);
        else next.add(index);
        planApi.updateChecklist(planId, [...next]).catch(() => {});
        return next;
      });
    },
    [planId]
  );

  async function handleExportCsv() {
    try {
      const blob = await planApi.exportCsv(planId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `shopping-list-${plan?.week_start_date ?? "plan"}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // ignore
    }
  }

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
      <div className="flex min-h-screen items-center justify-center bg-stone-50 dark:bg-stone-950">
        <p className="text-stone-500">Loading...</p>
      </div>
    );
  }

  if (!plan) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-stone-50 dark:bg-stone-950">
        <p className="text-stone-500">Plan not found.</p>
      </div>
    );
  }

  const mealsByDate = groupByDate(plan.meals);
  const sortedDates = Object.keys(mealsByDate).sort();

  return (
    <div className="min-h-screen bg-stone-50 p-8 dark:bg-stone-950">
      <div className="mx-auto max-w-5xl">
        {/* Header */}
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-stone-800 dark:text-stone-50">
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
              className="rounded-xl border border-stone-200 p-4 shadow-sm dark:border-stone-800"
            >
              <h3 className="mb-3 text-sm font-semibold text-stone-500">
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
                      protein_g?: number;
                      carbs_g?: number;
                      fat_g?: number;
                      fiber_g?: number;
                      source?: string;
                      confidence?: string;
                    } | null;
                    const isUsda = nutrition?.source === "usda";
                    return (
                      <div
                        key={meal.id}
                        className="rounded bg-white p-3 shadow-sm dark:bg-stone-900"
                      >
                        <div className="flex items-center justify-between">
                          <p className="text-xs font-medium uppercase text-stone-400">
                            {meal.meal_type}
                          </p>
                          {nutrition?.source && (
                            <span
                              className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium ${
                                isUsda
                                  ? "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
                                  : "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300"
                              }`}
                            >
                              {isUsda ? "USDA" : "Est."}
                            </span>
                          )}
                        </div>
                        <p className="font-medium text-stone-800 dark:text-stone-100">
                          {meal.title}
                        </p>
                        <div className="mt-1 flex gap-2 text-xs text-stone-500">
                          {meal.cook_time_min != null && (
                            <span>{meal.cook_time_min} min</span>
                          )}
                          {meal.servings != null && (
                            <span>{meal.servings} servings</span>
                          )}
                        </div>
                        {nutrition?.calories != null && (
                          <div className="mt-2 grid grid-cols-5 gap-1 text-center text-[10px]">
                            <div>
                              <p className="font-semibold text-stone-800 dark:text-stone-100">
                                {nutrition.calories}
                              </p>
                              <p className="text-stone-400">cal</p>
                            </div>
                            <div>
                              <p className="font-semibold text-stone-800 dark:text-stone-100">
                                {nutrition.protein_g ?? 0}g
                              </p>
                              <p className="text-stone-400">protein</p>
                            </div>
                            <div>
                              <p className="font-semibold text-stone-800 dark:text-stone-100">
                                {nutrition.carbs_g ?? 0}g
                              </p>
                              <p className="text-stone-400">carbs</p>
                            </div>
                            <div>
                              <p className="font-semibold text-stone-800 dark:text-stone-100">
                                {nutrition.fat_g ?? 0}g
                              </p>
                              <p className="text-stone-400">fat</p>
                            </div>
                            <div>
                              <p className="font-semibold text-stone-800 dark:text-stone-100">
                                {nutrition.fiber_g ?? 0}g
                              </p>
                              <p className="text-stone-400">fiber</p>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
              </div>
              {/* Day totals */}
              {(() => {
                const dayMeals = mealsByDate[dateStr];
                const dayCal = dayMeals.reduce((s, m) => s + ((m.nutrition_json as Record<string, number> | null)?.calories ?? 0), 0);
                const dayPro = dayMeals.reduce((s, m) => s + ((m.nutrition_json as Record<string, number> | null)?.protein_g ?? 0), 0);
                const dayCarb = dayMeals.reduce((s, m) => s + ((m.nutrition_json as Record<string, number> | null)?.carbs_g ?? 0), 0);
                const dayFat = dayMeals.reduce((s, m) => s + ((m.nutrition_json as Record<string, number> | null)?.fat_g ?? 0), 0);
                if (dayCal === 0) return null;
                return (
                  <div className="mt-3 border-t border-stone-200 pt-2 dark:border-stone-700">
                    <p className="text-[10px] font-medium uppercase text-stone-400">Day Total</p>
                    <p className="text-xs font-semibold text-stone-700 dark:text-stone-300">
                      {dayCal} cal &middot; {Math.round(dayPro)}g P &middot; {Math.round(dayCarb)}g C &middot; {Math.round(dayFat)}g F
                    </p>
                  </div>
                );
              })()}
            </div>
          ))}
        </div>

        {/* Shopping List */}
        {shoppingItems.length > 0 && (
          <section className="mt-8 rounded-xl border border-stone-200 p-6 shadow-sm dark:border-stone-800">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold text-stone-800 dark:text-stone-100">
                  Shopping List
                </h2>
                <p className="text-xs text-stone-400">
                  {checkedSet.size}/{shoppingItems.length} items checked
                </p>
              </div>
              <Button variant="secondary" onClick={handleExportCsv}>
                Download CSV
              </Button>
            </div>
            {(() => {
              const byCategory: Record<string, { item: ShoppingItemWithLinks; idx: number }[]> = {};
              shoppingItems.forEach((item, idx) => {
                const cat = item.category || "Other";
                if (!byCategory[cat]) byCategory[cat] = [];
                byCategory[cat].push({ item, idx });
              });
              const sortedCats = Object.keys(byCategory).sort();
              return sortedCats.map((cat) => (
                <div key={cat} className="mb-4">
                  <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-stone-400">
                    {cat}
                  </h3>
                  <div className="grid grid-cols-1 gap-1 md:grid-cols-2">
                    {byCategory[cat].map(({ item, idx }) => (
                      <label
                        key={idx}
                        className={`flex items-center gap-2 rounded px-2 py-1 text-sm transition-colors ${
                          checkedSet.has(idx)
                            ? "text-stone-400 line-through"
                            : "text-stone-700 dark:text-stone-300"
                        }`}
                      >
                        <input
                          type="checkbox"
                          className="rounded"
                          checked={checkedSet.has(idx)}
                          onChange={() => handleCheckToggle(idx)}
                        />
                        <span>
                          {item.quantity} {item.unit} {item.name}
                        </span>
                        <span className="ml-auto flex gap-1 text-[10px]">
                          <a
                            href={item.retailer_links.walmart}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="rounded bg-blue-100 px-1 text-blue-700 hover:bg-blue-200 dark:bg-blue-900 dark:text-blue-300"
                          >
                            W
                          </a>
                          <a
                            href={item.retailer_links.instacart}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="rounded bg-green-100 px-1 text-green-700 hover:bg-green-200 dark:bg-green-900 dark:text-green-300"
                          >
                            I
                          </a>
                          <a
                            href={item.retailer_links.google}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="rounded bg-amber-100 px-1 text-amber-700 hover:bg-amber-200 dark:bg-amber-900 dark:text-amber-300"
                          >
                            G
                          </a>
                        </span>
                      </label>
                    ))}
                  </div>
                </div>
              ));
            })()}
          </section>
        )}

        {/* Summary */}
        {plan.summary_md && (
          <section className="mt-8 rounded-xl border border-stone-200 p-6 shadow-sm dark:border-stone-800">
            <h2 className="mb-4 text-xl font-semibold text-stone-800 dark:text-stone-100">
              Summary
            </h2>
            <pre className="whitespace-pre-wrap text-sm text-stone-600 dark:text-stone-400">
              {plan.summary_md}
            </pre>
          </section>
        )}
      </div>
    </div>
  );
}
