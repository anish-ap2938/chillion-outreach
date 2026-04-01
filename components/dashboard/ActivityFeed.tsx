"use client";

import { useEffect, useState } from "react";
import { getSocialLeads, getDiscoveredCompanies, getDiscoveredContacts, type SocialLead, type DiscoveredCompany, type DiscoveredContact } from "@/lib/api/agents";
import { Badge } from "@/components/ui/Badge";

type ActivityItem =
  | { type: "lead"; title: string; time: string; meta: string }
  | { type: "company"; title: string; time: string; meta: string }
  | { type: "contact"; title: string; time: string; meta: string };

export default function ActivityFeed() {
  const [items, setItems] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    load();
  }, []);

  const load = async () => {
    setLoading(true);
    try {
      const [leadsResp, companiesResp, contactsResp] = await Promise.all([
        getSocialLeads({ sort_by: "discovered_at", sort_order: "desc", limit: 10, offset: 0 }),
        getDiscoveredCompanies({ sort_by: "target_score", sort_order: "desc", limit: 10, offset: 0 }),
        getDiscoveredContacts({ sort_by: "relevance_score", sort_order: "desc", limit: 10, offset: 0 }),
      ]);

      const mapped: ActivityItem[] = [];
      (leadsResp.leads || []).forEach((l: SocialLead) => {
        mapped.push({
          type: "lead",
          title: l.title || l.text_excerpt || l.text || "New lead",
          time: l.discovered_at || "",
          meta: `${l.platform} • intent ${(l.intent_score * 100).toFixed(0)}%`,
        });
      });
      (companiesResp.companies || []).forEach((c: DiscoveredCompany) => {
        mapped.push({
          type: "company",
          title: c.name,
          time: c.discovered_at || "",
          meta: `${c.industry || "—"} • ${(c.target_score * 100).toFixed(0)}% ICP`,
        });
      });
      (contactsResp.contacts || []).forEach((c: DiscoveredContact) => {
        mapped.push({
          type: "contact",
          title: `${c.full_name} @ ${c.company_name}`,
          time: c.discovered_at || "",
          meta: c.title || "Contact",
        });
      });

      // Sort by time desc (fallback to original order)
      mapped.sort((a, b) => (b.time || "").localeCompare(a.time || ""));
      setItems(mapped.slice(0, 20));
    } finally {
      setLoading(false);
    }
  };

  if (loading && items.length === 0) {
    return <div className="p-4 text-sm text-zinc-400">Loading activity…</div>;
  }

  if (!items.length) {
    return <div className="p-4 text-sm text-zinc-500">No recent activity yet.</div>;
  }

  return (
    <div className="space-y-3">
      {items.map((item, idx) => (
        <div key={idx} className="flex items-start gap-3 rounded-lg border border-zinc-800 bg-zinc-900/60 p-3">
          <Badge variant={item.type === "lead" ? "info" : item.type === "company" ? "neutral" : "success"}>
            {item.type}
          </Badge>
          <div className="flex-1">
            <div className="text-sm text-white line-clamp-2">{item.title}</div>
            <div className="text-xs text-zinc-500 mt-1 flex gap-2">
              <span>{item.meta}</span>
              {item.time && <span>• {new Date(item.time).toLocaleString()}</span>}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

