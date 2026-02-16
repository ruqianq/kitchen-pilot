export default function Home() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-50 font-sans dark:bg-black">
      <main className="flex flex-col items-center gap-8 text-center">
        <h1 className="text-5xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
          Kitchen Pilot
        </h1>
        <p className="max-w-md text-lg text-zinc-600 dark:text-zinc-400">
          Your agentic weekly meal planner and nutrition coach.
          Chat to plan meals, get nutrition insights, and generate grocery lists.
        </p>
        <div className="flex flex-wrap justify-center gap-4">
          <a
            href="/onboarding"
            className="rounded-full bg-zinc-900 px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-zinc-700 dark:bg-zinc-50 dark:text-zinc-900 dark:hover:bg-zinc-200"
          >
            Get Started
          </a>
          <a
            href="/plans"
            className="rounded-full border border-zinc-300 px-6 py-3 text-sm font-medium text-zinc-700 transition-colors hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
          >
            Meal Plans
          </a>
          <a
            href="/profile"
            className="rounded-full border border-zinc-300 px-6 py-3 text-sm font-medium text-zinc-700 transition-colors hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
          >
            Household Profile
          </a>
        </div>
      </main>
    </div>
  );
}
