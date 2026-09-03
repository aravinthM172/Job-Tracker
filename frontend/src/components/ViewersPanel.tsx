import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Loader2, Trash2, UserPlus } from "lucide-react";
import { ApiError, api, type ManagedUser } from "../lib/api";

export function ViewersPanel() {
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setUsers(await api.auth.listUsers());
    } catch {
      setError("Could not load the user list.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function addViewer(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.auth.createUser(username.trim(), password);
      setUsername("");
      setPassword("");
      await load();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError("That username is already taken.");
      } else if (err instanceof ApiError && err.status === 422) {
        setError("Username needs 2+ characters, password 8+.");
      } else {
        setError("Could not create that account.");
      }
    } finally {
      setBusy(false);
    }
  }

  async function remove(user: ManagedUser) {
    setError(null);
    try {
      await api.auth.deleteUser(user.id);
      await load();
    } catch {
      setError(`Could not remove ${user.username}.`);
    }
  }

  const viewers = users.filter((u) => u.role === "viewer");

  return (
    <div>
      <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
        People with access
      </h2>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
        Viewer accounts can open the Live Jobs page and nothing else — your
        synced email is never reachable from their session. Passwords are hashed
        and cannot be shown again, so note one down before you share it.
      </p>

      <form
        onSubmit={addViewer}
        className="mt-4 flex flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
      >
        <label className="flex-1 text-xs font-medium text-slate-600 dark:text-slate-400">
          Username
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            minLength={2}
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-slate-400 dark:border-slate-700 dark:bg-slate-800 dark:focus:border-slate-500"
          />
        </label>
        <label className="flex-1 text-xs font-medium text-slate-600 dark:text-slate-400">
          Password
          <input
            type="text"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            placeholder="at least 8 characters"
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-slate-400 dark:border-slate-700 dark:bg-slate-800 dark:focus:border-slate-500"
          />
        </label>
        <button
          type="submit"
          disabled={busy}
          className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-3 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-60 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-300"
        >
          {busy ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <UserPlus className="h-4 w-4" />
          )}
          Add viewer
        </button>
      </form>

      {error && (
        <p className="mt-3 rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-700 dark:bg-rose-950/40 dark:text-rose-300">
          {error}
        </p>
      )}

      <div className="mt-4 overflow-hidden rounded-xl border border-slate-200 dark:border-slate-800">
        {loading ? (
          <div className="flex justify-center p-6 text-slate-400">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : viewers.length === 0 ? (
          <p className="p-4 text-sm text-slate-400 dark:text-slate-500">
            No viewer accounts yet.
          </p>
        ) : (
          <ul className="divide-y divide-slate-100 dark:divide-slate-800">
            {viewers.map((user) => (
              <li
                key={user.id}
                className="flex items-center justify-between gap-3 bg-white px-4 py-3 text-sm dark:bg-slate-900"
              >
                <div>
                  <span className="font-medium text-slate-800 dark:text-slate-200">
                    {user.username}
                  </span>
                  <span className="ml-2 text-xs text-slate-400 dark:text-slate-500">
                    added {new Date(user.created_at).toLocaleDateString()}
                  </span>
                </div>
                <button
                  onClick={() => remove(user)}
                  className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-2 py-1 text-xs font-medium text-slate-500 hover:border-rose-300 hover:bg-rose-50 hover:text-rose-600 dark:border-slate-700 dark:hover:border-rose-800 dark:hover:bg-rose-950/40"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  Remove
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
