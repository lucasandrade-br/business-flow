export function extractApiError(err, fallback) {
  const raw = String(err?.message || "").trim();
  if (!raw) return fallback;

  try {
    const parsed = JSON.parse(raw);
    const first = Array.isArray(parsed) ? parsed[0] : Object.values(parsed)[0];
    const message = Array.isArray(first) ? first[0] : first;
    return message ? String(message) : fallback;
  } catch {
    return raw.startsWith("<") ? fallback : raw;
  }
}
