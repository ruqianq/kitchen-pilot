"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";

const NAV_LINKS = [
  { href: "/", label: "Home" },
  { href: "/chat", label: "Chat" },
  { href: "/plans", label: "Plans" },
  { href: "/profile", label: "Profile" },
];

export default function NavBar() {
  const pathname = usePathname();

  return (
    <nav className="border-b border-stone-200 bg-stone-50 px-6 py-3 dark:border-stone-800 dark:bg-stone-950">
      <div className="mx-auto flex max-w-4xl items-center justify-between">
        <Link
          href="/"
          className="text-lg font-bold text-stone-900 dark:text-stone-50"
        >
          Kitchen Pilot
        </Link>
        <div className="flex gap-1">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`rounded-full px-4 py-2 text-sm font-medium transition-colors ${
                pathname === link.href
                  ? "bg-amber-700 text-white dark:bg-amber-500 dark:text-stone-950"
                  : "text-stone-600 hover:bg-stone-100 dark:text-stone-400 dark:hover:bg-stone-800"
              }`}
            >
              {link.label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
}
