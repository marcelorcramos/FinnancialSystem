/**
 * Per-browser UI preferences (language, theme). Storage can be unavailable
 * (private mode, blocked site data), so every access is guarded.
 */
export function readPreference(key: string): string | null {
  try {
    return globalThis.localStorage?.getItem(key) ?? null;
  } catch {
    return null;
  }
}

export function writePreference(key: string, value: string | null): void {
  try {
    if (value === null) {
      globalThis.localStorage?.removeItem(key);
    } else {
      globalThis.localStorage?.setItem(key, value);
    }
  } catch {
    // Preferences are a convenience; ignore storage failures.
  }
}
