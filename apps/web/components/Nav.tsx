"use client";

import Link from "next/link";
import ThemeToggle from "@/components/ThemeToggle";

export default function Nav() {
  return (
    <aside className="sidebar">
      <div className="sidebar-top">
        <Link href="/" className="brand">
          NGO Report Studio
        </Link>
      </div>

      <div className="sidebar-bottom">
        <ThemeToggle />
        <button className="sidebar-icon user-icon" title="Account" aria-label="Account">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
        </button>
      </div>
    </aside>
  );
}