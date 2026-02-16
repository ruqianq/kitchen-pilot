"use client";

import { useEffect, useState } from "react";
import Button from "@/components/Button";
import Input from "@/components/Input";
import type { WeeklyPlanResponse, PlanGenerateResponse } from "@/lib/api";
import { planApi } from "@/lib/api";

function getNextMonday(): string {
  const now = new Date();
  const day = now.getDay();
  const diff = day === 0 ? 1 : 8 - day;
  const monday = new Date(now);
  monday.setDate(now.getDate() + diff);
  return monday.toISOString().slice(0, 10);
}

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400",
  confirmed: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  published: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  archived: "bg-zinc-200 text-zinc-500 dark:bg-zinc-700 dark:text-zinc-400",
};

export default function PlansPage() {
  const [plans, setPlans] = useState<WeeklyPlanResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [weekStart, setWeekStart] = useState(getNextMonday());
  const [notes, setNotes] = useState("");
  const [maxCookTime, setMaxCookTime] = useState("");
  const [result, setResult] = useState<PlanGenerateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    planApi
      .list()
      .then(setPlans)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  async function handleGenerate() {
    setGenerating(true);
    setError(null);
    setResult(null);
    try {
      const res = await planApi.generate({
        week_start_date: weekStart,
        notes: notes || undefined,
        max_cook_time_min: maxCookTime ? parseInt(maxCookTime) : undefined,
      });
      setResult(res);
      const updated = await planApi.list();
      setPlans(updated);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div className="min-h-screen bg-zinc-50 p-8 dark:bg-black">
      <div className="mx-auto max-w-4xl">
        <div className="mb-8 flex items-center justify-between">
          <h1 className="text-3xl font-bold text-zinc-900 dark:text-zinc-50">
            Meal Plans
          </h1>
          <a href="/">
            <Button variant="secondary">Home</Button>
          </a>
        </div>

        {/* Generator */}
        <section className="mb-8 rounded-lg border border-zinc-200 p-6 dark:border-zinc-800">
          <h2 className="mb-4 text-xl font-semibold text-zinc-900 dark:text-zinc-100">
            Generate New Plan
          </h2>
          <div className="flex flex-col gap-4">
            <Input
              label="Week starting (Monday)"
              type="date"
              value={weekStart}
              onChange={(e) => setWeekStart(e.target.value)}
            />
            <Input
              label="Max cook time per meal (minutes, optional)"
              type="number"
              value={maxCookTime}
              onChange={(e) => setMaxCookTime(e.target.value)}
              placeholder="e.g. 30"
            />
            <Input
              label="Notes (optional)"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. high protein dinners, kid-friendly"
            />
            <Button onClick={handleGenerate} disabled={generating}>
              {generating
                ? "Generating... (this takes a few minutes)"
                : "Generate Plan"}
            </Button>
          </div>

          {error && <p className="mt-4 text-sm text-red-500">{error}</p>}

          {result && result.warnings.length > 0 && (
            <div className="mt-4">
              {result.warnings.map((w, i) => (
                <p key={i} className="text-sm text-amber-500">
                  {w}
                </p>
              ))}
            </div>
          )}

          {result && (
            <p className="mt-4 text-sm text-green-600">
              Plan generated!{" "}
              <a href={`/plans/${result.plan.id}`} className="underline">
                View plan
              </a>
            </p>
          )}
        </section>

        {/* Plan List */}
        <section className="rounded-lg border border-zinc-200 p-6 dark:border-zinc-800">
          <h2 className="mb-4 text-xl font-semibold text-zinc-900 dark:text-zinc-100">
            Existing Plans
          </h2>
          {loading ? (
            <p className="text-zinc-500">Loading...</p>
          ) : plans.length === 0 ? (
            <p className="text-sm text-zinc-400">
              No plans yet. Generate your first one above!
            </p>
          ) : (
            <div className="flex flex-col gap-3">
              {plans.map((p) => (
                <a
                  key={p.id}
                  href={`/plans/${p.id}`}
                  className="flex items-center justify-between rounded-lg border border-zinc-100 px-4 py-3 transition-colors hover:bg-zinc-100 dark:border-zinc-800 dark:hover:bg-zinc-900"
                >
                  <div>
                    <p className="font-medium text-zinc-900 dark:text-zinc-100">
                      Week of {p.week_start_date}
                    </p>
                    <span
                      className={`mt-1 inline-block rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[p.status] ?? ""}`}
                    >
                      {p.status}
                    </span>
                  </div>
                  <span className="text-xs text-zinc-400">
                    {new Date(p.created_at).toLocaleDateString()}
                  </span>
                </a>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
