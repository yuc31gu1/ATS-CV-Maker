import { useEffect, useState } from "react";
import { fetchHealth, type HealthResponse } from "../api/health";

type LoadState =
  | { phase: "loading" }
  | { phase: "ok"; health: HealthResponse }
  | { phase: "error"; message: string };

export function ConnectivityPage() {
  const [state, setState] = useState<LoadState>({ phase: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    fetchHealth(controller.signal)
      .then((health) => setState({ phase: "ok", health }))
      .catch((err: unknown) =>
        setState({
          phase: "error",
          message: err instanceof Error ? err.message : String(err),
        }),
      );
    return () => controller.abort();
  }, []);

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50">
      <div className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-xl font-semibold text-slate-900">ATS CV Maker</h1>
        {state.phase === "loading" && <p className="mt-3 text-slate-500">Checking backend…</p>}
        {state.phase === "ok" && (
          <div className="mt-3 space-y-1 text-sm">
            <p className="text-green-700">Backend connected</p>
            <p className="text-slate-600">Service: {state.health.service}</p>
            <p className="text-slate-600">
              Database: <span className="font-medium">{state.health.database.status}</span>
            </p>
          </div>
        )}
        {state.phase === "error" && (
          <p className="mt-3 text-red-600">Backend unreachable: {state.message}</p>
        )}
      </div>
    </main>
  );
}