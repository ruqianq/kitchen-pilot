export default function Home() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-stone-50 font-sans dark:bg-stone-950">
      <main className="flex flex-col items-center gap-8 text-center">
        <h1 className="text-5xl font-bold tracking-tight text-stone-800 dark:text-stone-50">
          Kitchen Pilot
        </h1>
        <p className="max-w-md text-lg text-stone-600 dark:text-stone-400">
          Your agentic weekly meal planner and nutrition coach.
          Chat to plan meals, get nutrition insights, and generate grocery lists.
        </p>
        <div className="flex flex-wrap justify-center gap-4">
          <a
            href="/onboarding"
            className="rounded-full bg-amber-700 px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-amber-800 dark:bg-amber-500 dark:text-stone-950 dark:hover:bg-amber-400"
          >
            Get Started
          </a>
          <a
            href="/plans"
            className="rounded-full border border-stone-300 px-6 py-3 text-sm font-medium text-stone-700 transition-colors hover:bg-stone-100 dark:border-stone-700 dark:text-stone-300 dark:hover:bg-stone-800"
          >
            Meal Plans
          </a>
          <a
            href="/profile"
            className="rounded-full border border-stone-300 px-6 py-3 text-sm font-medium text-stone-700 transition-colors hover:bg-stone-100 dark:border-stone-700 dark:text-stone-300 dark:hover:bg-stone-800"
          >
            Household Profile
          </a>
        </div>
      </main>
    </div>
  );
}
