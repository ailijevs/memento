/**
 * Sanitize ?next= targets so we never router.push to an external URL.
 */
export function safeNextPath(
  raw: string | null | undefined,
  fallback: string,
): string {
  if (raw == null || raw === "") {
    return fallback;
  }
  const trimmed = raw.trim();
  if (!trimmed.startsWith("/") || trimmed.startsWith("//")) {
    return fallback;
  }
  if (trimmed.includes("://") || trimmed.includes("\\")) {
    return fallback;
  }
  return trimmed;
}
