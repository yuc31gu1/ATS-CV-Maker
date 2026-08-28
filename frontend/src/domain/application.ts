import type { ApplicationSummary } from "../api/dashboard";

export function applicationLabel(application: ApplicationSummary): string {
  const parts = [application.company, application.role, application.location].filter(
    (part): part is string => Boolean(part),
  );
  return parts.length > 0 ? parts.join(" · ") : "Untitled application";
}