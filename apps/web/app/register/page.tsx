"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AUTH_ENABLED, api, setTokens } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [org, setOrg] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!AUTH_ENABLED) {
      router.replace("/");
    }
  }, [router]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await api("/api/auth/register", {
        method: "POST",
        body: { email, org_name: org, password },
      });
      const body = new URLSearchParams({ username: email, password });
      const res = await fetch(`/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
      });
      const token = await res.json();
      setTokens(token.access_token, token.refresh_token);
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="container auth-page" style={{ maxWidth: 420, marginTop: 60 }}>
      <div className="card auth-card">
        <h1>Create account</h1>
        <form onSubmit={submit}>
          <label>Email</label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
          />
          <label>Organization name</label>
          <input
            required
            value={org}
            onChange={(e) => setOrg(e.target.value)}
          />
          <label>Password (min 8 chars)</label>
          <input
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
          />
          {error && <p className="error">{error}</p>}
          <div className="row" style={{ marginTop: 16 }}>
            <button disabled={busy} type="submit">
              {busy ? "Creating…" : "Create account"}
            </button>
            <span className="muted">
              Already registered? <Link href="/login">Sign in</Link>
            </span>
          </div>
        </form>
      </div>
    </div>
  );
}