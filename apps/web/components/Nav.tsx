"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AUTH_ENABLED, api, clearTokens, getToken, type User } from "@/lib/api";

export default function Nav() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    if (!AUTH_ENABLED) return;
    if (!getToken()) return;
    api<User>("/api/auth/me")
      .then(setUser)
      .catch(() => {
        clearTokens();
      });
  }, []);

  function logout() {
    clearTokens();
    router.push("/login");
  }

  return (
    <nav className="nav">
      <Link href="/projects" className="brand">
        NGO Report Studio
      </Link>
      {AUTH_ENABLED && user && (
        <>
          <span className="muted">
            {user.org_name} · {user.email}
          </span>
          <button className="secondary" onClick={logout}>
            Sign out
          </button>
        </>
      )}
    </nav>
  );
}