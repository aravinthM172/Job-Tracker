import { useState, type FormEvent } from "react";
import { Loader2, LogIn, Radio } from "lucide-react";
import { ApiError } from "../lib/api";
import { useAuth } from "../hooks/useAuth";

export function LoginPage() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(username.trim(), password);
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) {
        setError("Too many attempts. Wait a few minutes and try again.");
      } else if (err instanceof ApiError && err.status === 401) {
        setError("Wrong username or password.");
      } else {
        setError("Could not reach the server. Try again.");
      }
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 dark:bg-slate-950">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900">
            <Radio className="h-5 w-5" />
          </div>
          <span className="text-base font-semibold text-slate-900 dark:text-slate-100">
            Job Tracker
          </span>
        </div>

        <form
          onSubmit={onSubmit}
          className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900"
        >
          <h1 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            Sign in
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Enter the credentials you were given to see Live Jobs.
          </p>

          <label className="mt-5 block text-xs font-medium text-slate-600 dark:text-slate-400">
            Username
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              autoFocus
              required
              className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-slate-400 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100 dark:focus:border-slate-500"
            />
          </label>

          <label className="mt-3 block text-xs font-medium text-slate-600 dark:text-slate-400">
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
              className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-slate-400 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100 dark:focus:border-slate-500"
            />
          </label>

          {error && (
            <p className="mt-3 rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-700 dark:bg-rose-950/40 dark:text-rose-300">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={busy}
            className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-slate-900 px-3 py-2.5 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-60 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-300"
          >
            {busy ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <LogIn className="h-4 w-4" />
            )}
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
