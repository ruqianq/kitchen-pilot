"use client";

interface StepIndicatorProps {
  steps: string[];
  currentStep: number;
}

export default function StepIndicator({ steps, currentStep }: StepIndicatorProps) {
  return (
    <div className="mb-8 flex items-center justify-between">
      {steps.map((step, i) => (
        <div key={step} className="flex items-center">
          <div className="flex flex-col items-center">
            <div
              className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium
                ${i < currentStep
                  ? "bg-lime-600 text-white dark:bg-lime-500"
                  : i === currentStep
                    ? "bg-orange-700 text-white dark:bg-orange-600"
                    : "bg-stone-200 text-stone-500 dark:bg-stone-800 dark:text-stone-500"
                }`}
            >
              {i + 1}
            </div>
            <span
              className={`mt-1 text-xs ${
                i <= currentStep
                  ? "text-stone-800 dark:text-stone-100"
                  : "text-stone-400 dark:text-stone-600"
              }`}
            >
              {step}
            </span>
          </div>
          {i < steps.length - 1 && (
            <div
              className={`mx-2 h-0.5 w-12 sm:w-20 ${
                i < currentStep
                  ? "bg-lime-600 dark:bg-lime-500"
                  : "bg-stone-200 dark:bg-stone-800"
              }`}
            />
          )}
        </div>
      ))}
    </div>
  );
}
