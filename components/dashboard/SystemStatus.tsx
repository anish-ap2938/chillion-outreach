"use client";

import { useEffect, useState } from "react";
import { getLeadGenConfig, getLeadGenMetrics, type LeadGenConfig, type LeadGenMetrics } from "@/lib/api/agents";
import { Badge } from "@/components/ui/Badge";

export default function SystemStatus() {
  const [config, setConfig] = useState<LeadGenConfig | null>(null);
  const [metrics, setMetrics] = useState<LeadGenMetrics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [cfg, m] = await Promise.all([getLeadGenConfig(), getLeadGenMetrics()]);
        setConfig(cfg);
        setMetrics(m);
      } catch (e: any) {
        setError(e.message);
      }
    };
    load();
  }, []);

  const providerLabel =
    config?.search_provider === "serpapi"
      ? `SerpAPI (${config?.has_serpapi_key ? "key set" : "no key"})`
      : config?.search_provider === "google_cse"
        ? `Google CSE (${config?.has_google_cse ? "keys set" : "missing keys"})`
        : "Mock / fallback";

  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-5 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-white">System Status</h3>
        <Badge variant="info">Live</Badge>
      </div>

      {error && <p className="text-sm text-red-400">Failed to load status: {error}</p>}

      <div className="grid gap-3 text-sm text-zinc-300">
        <div className="flex items-center justify-between">
          <span className="text-zinc-400">Search provider</span>
          <span className="font-medium">{providerLabel}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-zinc-400">Deliverability stub</span>
          <span className="font-medium text-emerald-400">Ready (via Email Agent toggle)</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-zinc-400">Audit logging</span>
          <span className="font-medium text-blue-400">Enabled w/ PII masking</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-zinc-400">Latency (avg / p95)</span>
          <span className="font-medium">
            {metrics ? `${metrics.avg_latency_ms} ms / ${metrics.p95_latency_ms} ms` : "—"}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-zinc-400">High-intent ingested</span>
          <span className="font-medium">{metrics ? metrics.high_intent_count : "—"}</span>
        </div>
      </div>
    </div>
  );
}

