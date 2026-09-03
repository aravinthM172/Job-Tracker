import { useCallback, useEffect, useState } from "react";

// Per-browser bookmarking for Live Jobs. The backend's live_jobs table
// is a rolling 48h feed with no per-user state, so "saved" and "added
// to my applications" live in localStorage - they only need to matter
// on the machine the person browses from.

const SAVED_KEY = "livejobs-saved";
const ADDED_KEY = "livejobs-added";

function read(key: string): Set<string> {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return new Set();
    const parsed = JSON.parse(raw);
    return new Set(Array.isArray(parsed) ? parsed : []);
  } catch {
    return new Set();
  }
}

function write(key: string, value: Set<string>) {
  try {
    localStorage.setItem(key, JSON.stringify([...value]));
  } catch {
    /* private mode / quota - the toggle just won't persist */
  }
}

export function useSavedJobs() {
  const [saved, setSaved] = useState<Set<string>>(() => read(SAVED_KEY));
  const [added, setAdded] = useState<Set<string>>(() => read(ADDED_KEY));

  useEffect(() => write(SAVED_KEY, saved), [saved]);
  useEffect(() => write(ADDED_KEY, added), [added]);

  const toggleSaved = useCallback((key: string) => {
    setSaved((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  const markAdded = useCallback((key: string) => {
    setAdded((prev) => new Set(prev).add(key));
  }, []);

  return {
    saved,
    added,
    isSaved: (key: string) => saved.has(key),
    isAdded: (key: string) => added.has(key),
    toggleSaved,
    markAdded,
    savedCount: saved.size,
  };
}
