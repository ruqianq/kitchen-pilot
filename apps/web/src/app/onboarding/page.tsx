"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import StepIndicator from "@/components/StepIndicator";
import type { Household, Person } from "@/lib/api";
import { householdApi } from "@/lib/api";
import HouseholdStep from "./steps/HouseholdStep";
import PeopleStep from "./steps/PeopleStep";
import AllergiesStep from "./steps/AllergiesStep";
import PreferencesStep from "./steps/PreferencesStep";

const STEPS = ["Household", "People", "Allergies", "Preferences"];

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [household, setHousehold] = useState<Household | null>(null);
  const [people, setPeople] = useState<Person[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const h = await householdApi.get();
        setHousehold(h);
        const p = await householdApi.listPeople();
        setPeople(p);
      } catch {
        // First visit — no household yet
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-stone-500">Loading...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-8">
      <div className="mx-auto max-w-2xl">
        <h1 className="mb-2 text-3xl font-bold text-orange-800 dark:text-orange-400">
          Set Up Your Household
        </h1>
        <p className="mb-6 text-stone-500 dark:text-stone-400">
          Tell us about your family so we can plan meals tailored to everyone.
        </p>

        <StepIndicator steps={STEPS} currentStep={step} />

        {step === 0 && (
          <HouseholdStep
            household={household}
            onComplete={(h) => {
              setHousehold(h);
              setStep(1);
            }}
          />
        )}
        {step === 1 && (
          <PeopleStep
            people={people}
            onPeopleChange={setPeople}
            onNext={() => setStep(2)}
            onBack={() => setStep(0)}
          />
        )}
        {step === 2 && (
          <AllergiesStep
            people={people}
            onNext={() => setStep(3)}
            onBack={() => setStep(1)}
          />
        )}
        {step === 3 && household && (
          <PreferencesStep
            household={household}
            people={people}
            onFinish={() => router.push("/profile")}
            onBack={() => setStep(2)}
          />
        )}
      </div>
    </div>
  );
}
