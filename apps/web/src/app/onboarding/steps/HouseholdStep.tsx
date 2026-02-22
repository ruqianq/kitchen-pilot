"use client";

import { useState } from "react";
import Button from "@/components/Button";
import Input from "@/components/Input";
import Select from "@/components/Select";
import type { Household } from "@/lib/api";
import { householdApi } from "@/lib/api";

const TIMEZONES = [
  { value: "UTC", label: "UTC" },
  { value: "America/New_York", label: "Eastern (US)" },
  { value: "America/Chicago", label: "Central (US)" },
  { value: "America/Denver", label: "Mountain (US)" },
  { value: "America/Los_Angeles", label: "Pacific (US)" },
  { value: "Europe/London", label: "London" },
  { value: "Europe/Berlin", label: "Berlin" },
  { value: "Asia/Tokyo", label: "Tokyo" },
  { value: "Asia/Shanghai", label: "Shanghai" },
  { value: "Australia/Sydney", label: "Sydney" },
];

interface HouseholdStepProps {
  household: Household | null;
  onComplete: (h: Household) => void;
}

export default function HouseholdStep({ household, onComplete }: HouseholdStepProps) {
  const [name, setName] = useState(household?.name ?? "");
  const [timezone, setTimezone] = useState(household?.timezone ?? "UTC");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      setError("Household name is required");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const h = await householdApi.get();
      const updated = await householdApi.update(h.id, { name: name.trim(), timezone });
      onComplete(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-6 rounded-2xl border border-orange-100 bg-orange-50/40 p-6 shadow-sm dark:border-stone-800 dark:bg-stone-900">
      <Input
        label="Household Name"
        placeholder="e.g. The Smith Family"
        value={name}
        onChange={(e) => setName(e.target.value)}
        error={error}
      />
      <Select
        label="Timezone"
        options={TIMEZONES}
        value={timezone}
        onChange={(e) => setTimezone(e.target.value)}
      />
      <div className="flex justify-end">
        <Button type="submit" disabled={loading}>
          {loading ? "Saving..." : "Next"}
        </Button>
      </div>
    </form>
  );
}
