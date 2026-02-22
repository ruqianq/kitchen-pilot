export default function Home() {
  return (
    <div className="flex min-h-screen items-center justify-center font-sans">
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-orange-50/80 via-transparent to-amber-50/60 dark:from-orange-950/20 dark:to-amber-950/10" />
      <main className="relative flex flex-col items-center gap-8 text-center">
        <div className="flex items-center gap-3">
          <svg className="h-12 w-12 text-orange-700 dark:text-orange-500" viewBox="0 0 24 24" fill="currentColor">
            <path d="M8.1 13.34l2.83-2.83L3.91 3.5a4.008 4.008 0 000 5.66l4.19 4.18zm6.78-1.81c1.53.71 3.68.21 5.27-1.38 1.91-1.91 2.28-4.65.81-6.12-1.46-1.46-4.2-1.1-6.12.81-1.59 1.59-2.09 3.74-1.38 5.27L3.7 19.87l1.41 1.41L12 14.41l6.88 6.88 1.41-1.41L13.41 13l1.47-1.47z" />
          </svg>
          <h1 className="text-5xl font-bold tracking-tight text-orange-800 dark:text-orange-400">
            Kitchen Pilot
          </h1>
        </div>
        <p className="max-w-md text-lg text-stone-600 dark:text-stone-400">
          Your family&apos;s weekly meal planner and nutrition coach.
          Chat to plan meals, get nutrition insights, and generate grocery lists.
        </p>
        <div className="flex flex-wrap justify-center gap-4">
          <a
            href="/onboarding"
            className="rounded-full bg-orange-700 px-6 py-3 text-sm font-medium text-white shadow-sm transition-colors hover:bg-orange-800 dark:bg-orange-600 dark:hover:bg-orange-500"
          >
            Get Started
          </a>
          <a
            href="/plans"
            className="rounded-full border border-amber-300 px-6 py-3 text-sm font-medium text-amber-800 transition-colors hover:bg-amber-50 dark:border-amber-700 dark:text-amber-300 dark:hover:bg-stone-800"
          >
            Meal Plans
          </a>
          <a
            href="/profile"
            className="rounded-full border border-stone-300 px-6 py-3 text-sm font-medium text-stone-700 transition-colors hover:bg-orange-50 dark:border-stone-700 dark:text-stone-300 dark:hover:bg-stone-800"
          >
            Household Profile
          </a>
        </div>
      </main>
    </div>
  );
}
