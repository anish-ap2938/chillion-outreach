"use client";

import { useState, useEffect, useMemo } from "react";
import { 
  searchSocialMedia, 
  getSocialLeads,
  getLeadGenStats,
  getLeadGenConfig,
  setSearchProvider,
  type SocialLead,
  type LeadGenStats,
  type LeadGenConfig
} from "@/lib/api/agents";
import { Table, TableHead, TableBody, TableRow, TableHeaderCell, TableCell } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { useToast } from "@/components/ui/Toaster";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

export default function IntentSignalsAgent() {
  const [activeTab, setActiveTab] = useState<"search" | "saved">("search");
  const [platforms, setPlatforms] = useState<string[]>(["twitter", "reddit"]);
  const [keywords, setKeywords] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SocialLead[]>([]);
  const [savedLeads, setSavedLeads] = useState<SocialLead[]>([]);
  const [stats, setStats] = useState<LeadGenStats | null>(null);
  const [config, setConfig] = useState<LeadGenConfig | null>(null);
  const [searchProvider, setSearchProviderState] = useState<"dummy" | "serpapi" | "google_cse">("dummy");
  const [error, setError] = useState<string | null>(null);
  const [intentFilter, setIntentFilter] = useState<number>(0);
  const [sinceDays, setSinceDays] = useState<number>(7);
  const [density, setDensity] = useState<"comfortable" | "compact">("comfortable");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 25;
  const toast = useToast();
  const [sortBy, setSortBy] = useState<"intent_score" | "discovered_at">("intent_score");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [savedViews, setSavedViews] = useState<
    { name: string; minIntent: number; sinceDays: number; sortBy: string; sortOrder: "asc" | "desc"; density: "comfortable" | "compact" }[]
  >(() => {
    if (typeof window === "undefined") return [];
    const raw = localStorage.getItem("intent-views");
    return raw ? JSON.parse(raw) : [];
  });

  useEffect(() => {
    loadConfig();
    loadStats();
    const savedDensity = typeof window !== "undefined" ? localStorage.getItem("intent-density") : null;
    if (savedDensity === "compact" || savedDensity === "comfortable") setDensity(savedDensity);
  }, []);

  const loadConfig = async () => {
    try {
      const cfg = await getLeadGenConfig();
      setConfig(cfg);
      if (cfg.search_provider) {
        setSearchProviderState(cfg.search_provider);
      }
      // Set default keywords from config
      if (!keywords && cfg.product_keywords.length > 0) {
        setKeywords(cfg.product_keywords.slice(0, 4).join(", "));
      }
    } catch (e) {
      console.error("Failed to load config:", e);
    }
  };

  const loadStats = async () => {
    try {
      const s = await getLeadGenStats();
      setStats(s);
    } catch (e) {
      console.error("Failed to load stats:", e);
    }
  };

  const getPlatformIcon = (platform: string) => {
    switch (platform) {
      case "twitter":
        return "𝕏";
      case "reddit":
        return "🔴";
      case "forum":
      case "quora":
        return "💬";
      default:
        return "🌐";
    }
  };

  const loadSavedLeads = async (targetPage?: number) => {
    const nextPage = targetPage ?? page;
    setLoading(true);
    try {
      const response = await getSocialLeads({ min_intent: intentFilter, since_days: sinceDays, limit: pageSize, offset: (nextPage - 1) * pageSize, sort_by: sortBy, sort_order: sortOrder });
      setSavedLeads(response.leads || []);
      setTotal(response.count || 0);
      setPage(nextPage);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    setLoading(true);
    setError(null);
    try {
      const keywordList = keywords.split(",").map(k => k.trim()).filter(Boolean);
      const response = await searchSocialMedia({
        platforms,
        keywords: keywordList.length > 0 ? keywordList : undefined,
        max_results: 100,
      });
      setResults(response.leads || []);
      loadStats(); // Refresh stats after search
      toast({ title: "Search complete", description: `${response.total_results} results`, variant: "success" });
    } catch (e: any) {
      setError(e.message);
      toast({ title: "Search failed", description: e.message, variant: "error" });
    } finally {
      setLoading(false);
    }
  };

  const exportResults = (leads: SocialLead[]) => {
    const csv = [
      "Platform,URL,Author,Company,Title,Text,Intent Score,Intent Level,Keywords",
      ...leads.map(l => 
        `"${l.platform}","${l.url}","${l.author_username || ''}","${l.author_company || ''}","${l.title?.replace(/"/g, '""') || ''}","${l.text?.slice(0, 200).replace(/"/g, '""') || ''}",${l.intent_score},"${l.intent_level}","${l.product_keywords_matched?.join('; ') || ''}"`
      )
    ].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const a = document.createElement("a"); 
    a.href = URL.createObjectURL(blob); 
    a.download = `intent-signals-${new Date().toISOString().split('T')[0]}.csv`; 
    a.click();
    toast({ title: "Exported", description: `${leads.length} rows`, variant: "success" });
  };

  const togglePlatform = (platform: string) => {
    setPlatforms(prev => 
      prev.includes(platform) 
        ? prev.filter(p => p !== platform)
        : [...prev, platform]
    );
  };

  const handleProviderChange = async (provider: "dummy" | "serpapi" | "google_cse") => {
    try {
      setSearchProviderState(provider);
      await setSearchProvider(provider);
      toast({
        title: "Search provider updated",
        description: provider === "dummy" ? "Using mock search fallback" : `Now using ${provider === "serpapi" ? "SerpAPI" : "Google CSE"}`,
        variant: "success",
      });
    } catch (e: any) {
      toast({ title: "Failed to update provider", description: e.message, variant: "error" });
    }
  };

  const pagedSaved = savedLeads;

  const saveView = () => {
    const view = {
      name: `View ${savedViews.length + 1}`,
      minIntent: intentFilter,
      sinceDays,
      sortBy,
      sortOrder,
      density,
    };
    const next = [...savedViews, view];
    setSavedViews(next);
    localStorage.setItem("intent-views", JSON.stringify(next));
    toast({ title: "View saved", variant: "success" });
  };

  const applyView = (v: typeof savedViews[number]) => {
    setIntentFilter(v.minIntent);
    setSinceDays(v.sinceDays);
    setSortBy(v.sortBy as any);
    setSortOrder(v.sortOrder);
    setDensity(v.density);
    localStorage.setItem("intent-density", v.density);
    loadSavedLeads();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">
            Intent Signals
          </h1>
          <p className="text-zinc-400 mt-1">Find prospects discussing IT, defense, and engineering requirements Chillion serves</p>
        </div>
        
        {/* Stats Cards */}
        {stats && (
          <div className="flex gap-3">
            <div className="px-4 py-2 rounded-xl bg-zinc-800/50 border border-zinc-700">
              <div className="text-2xl font-bold text-cyan-400">{stats.total_social_leads}</div>
              <div className="text-xs text-zinc-500">Total Leads</div>
            </div>
            <div className="px-4 py-2 rounded-xl bg-zinc-800/50 border border-zinc-700">
              <div className="text-2xl font-bold text-green-400">{stats.high_intent_leads}</div>
              <div className="text-xs text-zinc-500">High Intent</div>
            </div>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-zinc-800 pb-2">
        {[
          { key: "search", label: "🔍 Search Social Media" },
          { key: "saved", label: `💾 Saved Leads (${stats?.total_social_leads || 0})` },
        ].map((tab) => (
          <Button
            key={tab.key}
            variant={activeTab === tab.key ? "primary" : "secondary"}
            onClick={() => {
              setActiveTab(tab.key as any);
              if (tab.key === "saved") loadSavedLeads();
            }}
            className="px-4 py-2 rounded-t-lg text-sm"
          >
            {tab.label}
          </Button>
        ))}
      </div>

      {activeTab === "search" && (
        <>
          {/* Search Card */}
          <div className="rounded-2xl bg-gradient-to-br from-zinc-900 to-zinc-900/50 border border-zinc-800 p-6">
            <div className="space-y-4">
              {/* Platform Selection */}
              <div>
                <label className="text-sm font-medium text-zinc-400 mb-2 block">Platforms to Search</label>
                <div className="flex gap-2">
                  {["twitter", "reddit", "forums"].map(p => (
                    <button
                      key={p}
                      onClick={() => togglePlatform(p)}
                      className={`px-4 py-2 rounded-xl border transition ${
                        platforms.includes(p)
                          ? "bg-cyan-500/20 border-cyan-500/50 text-cyan-400"
                          : "bg-zinc-800/50 border-zinc-700 text-zinc-400 hover:border-zinc-600"
                      }`}
                    >
                      {getPlatformIcon(p)} {p.charAt(0).toUpperCase() + p.slice(1)}
                    </button>
                  ))}
                </div>
              </div>

              {/* Search Provider Selection */}
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-zinc-400 mb-2 block">Search Provider for Forums/Intent</label>
                  <div className="flex flex-wrap gap-2">
                    {[
                      { key: "dummy", label: "Mock (no key)" },
                      { key: "serpapi", label: "SerpAPI" },
                      { key: "google_cse", label: "Google CSE" },
                    ].map(opt => (
                      <Button
                        key={opt.key}
                        variant={searchProvider === opt.key ? "primary" : "secondary"}
                        size="sm"
                        onClick={() => handleProviderChange(opt.key as any)}
                      >
                        {opt.label}
                      </Button>
                    ))}
                  </div>
                  <p className="text-xs text-zinc-500 mt-2">
                    {config?.search_provider === "serpapi" && config?.has_serpapi_key
                      ? "SerpAPI key detected."
                      : config?.search_provider === "google_cse" && config?.has_google_cse
                        ? "Google CSE key detected."
                        : "Using mock search until a provider with keys is selected."}
                  </p>
                </div>
                <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-3 text-sm text-zinc-300">
                  <div className="flex items-center gap-2">
                    <Badge variant="info">Audit & Validation</Badge>
                    <span className="text-xs text-zinc-500">Live</span>
                  </div>
                  <ul className="list-disc list-inside mt-2 space-y-1 text-xs text-zinc-400">
                    <li>Draft audit logging with PII masking</li>
                    <li>Deliverability stub runs when "Validate before send" is enabled</li>
                    <li>Metrics include latency and high-intent counts</li>
                  </ul>
                </div>
              </div>

              {/* Keywords */}
              <div>
                <label className="text-sm font-medium text-zinc-400 mb-2 block">Search Keywords (optional)</label>
                <input
                  value={keywords}
                  onChange={(e) => setKeywords(e.target.value)}
                  className="w-full rounded-xl bg-zinc-800/50 border border-zinc-700 px-4 py-3 text-white placeholder-zinc-500 focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 focus:outline-none transition"
                  placeholder="Leave empty to use default Chillion solution keywords..."
                />
                {config && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {config.product_keywords.slice(0, 6).map(kw => (
                      <button
                        key={kw}
                        onClick={() => setKeywords(prev => prev ? `${prev}, ${kw}` : kw)}
                        className="px-2 py-1 text-xs rounded-full bg-zinc-800 text-zinc-400 hover:bg-zinc-700 transition"
                      >
                        + {kw}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Search Button */}
            <Button
              onClick={handleSearch}
              disabled={loading || platforms.length === 0}
              className="w-full bg-gradient-to-r from-cyan-500 to-blue-500 px-6 py-4 font-medium text-white shadow-lg shadow-cyan-500/25 hover:shadow-cyan-500/40 transition disabled:opacity-50"
            >
              {loading ? "🔍 Searching social media..." : `🔍 Search ${platforms.join(", ")}`}
            </Button>
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400">
              {error}
            </div>
          )}

          {/* Results */}
          {results.length > 0 && (
            <div className="rounded-2xl bg-gradient-to-br from-zinc-900 to-zinc-900/50 border border-zinc-800 overflow-hidden">
              <div className="p-4 border-b border-zinc-800 flex justify-between items-center">
                <div>
                  <span className="font-semibold text-white">{results.length} Results Found</span>
                  <span className="ml-4 text-sm text-green-400">
                    {results.filter(r => r.intent_level === 'high').length} high intent
                  </span>
                </div>
                <button 
                  onClick={() => exportResults(results)} 
                  className="px-4 py-2 bg-zinc-800 border border-zinc-700 rounded-xl text-sm hover:bg-zinc-700 transition"
                >
                  📥 Export CSV
                </button>
              </div>
              <div className="divide-y divide-zinc-800 max-h-[600px] overflow-y-auto">
                {results.map((lead, i) => (
                  <LeadCard key={i} lead={lead} />
                ))}
              </div>
            </div>
          )}

          {/* Empty State */}
          {!loading && results.length === 0 && (
            <div className="text-center py-16">
              <div className="text-6xl mb-4">🔍</div>
              <h3 className="text-xl font-semibold text-zinc-300">Search Social Media for Intent Signals</h3>
              <p className="text-zinc-500 mt-2">Select platforms and click search to find prospects discussing infrastructure, security, cloud, and engineering programs</p>
            </div>
          )}
        </>
      )}

      {activeTab === "saved" && (
        <>
          {/* Filter Bar */}
          <div className="flex flex-wrap gap-4 items-center">
            <label className="text-sm text-zinc-400">Min Intent Score:</label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={intentFilter}
              onChange={(e) => setIntentFilter(parseFloat(e.target.value))}
              className="w-32"
            />
            <span className="text-cyan-400 font-medium">{intentFilter.toFixed(1)}</span>
        <label className="text-sm text-zinc-400 ml-4">Seen in last:</label>
        <select
          value={sinceDays}
          onChange={(e) => setSinceDays(parseInt(e.target.value))}
          className="rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-white focus:border-cyan-500 focus:outline-none"
        >
          <option value={1}>24h</option>
          <option value={3}>3 days</option>
          <option value={7}>7 days</option>
          <option value={30}>30 days</option>
          <option value={90}>90 days</option>
        </select>
            <div className="flex items-center gap-2 ml-auto">
              <label className="text-sm text-zinc-400">Density</label>
              <select
                value={density}
                onChange={(e) => { const d = e.target.value as "comfortable" | "compact"; setDensity(d); localStorage.setItem("intent-density", d); }}
                className="rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-white focus:border-cyan-500 focus:outline-none"
              >
                <option value="comfortable">Comfortable</option>
                <option value="compact">Compact</option>
              </select>
            </div>
            <div className="flex gap-2 items-center">
              <label className="text-sm text-zinc-400">Sort</label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                className="rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-white focus:border-cyan-500 focus:outline-none"
              >
                <option value="intent_score">Intent Score</option>
                <option value="discovered_at">Newest</option>
              </select>
              <select
                value={sortOrder}
                onChange={(e) => setSortOrder(e.target.value as any)}
                className="rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-white focus:border-cyan-500 focus:outline-none"
              >
                <option value="desc">Desc</option>
                <option value="asc">Asc</option>
              </select>
            </div>
            <Button
              onClick={() => loadSavedLeads(1)}
              variant="secondary"
              className="px-4 py-2 rounded-xl text-sm"
            >
              Apply Filter
            </Button>
            {savedLeads.length > 0 && (
              <button 
                onClick={() => exportResults(savedLeads)} 
                className="px-4 py-2 bg-cyan-500/20 border border-cyan-500/30 rounded-xl text-sm text-cyan-400 hover:bg-cyan-500/30 transition ml-auto"
              >
                📥 Export All
              </button>
            )}
            <Button
              onClick={saveView}
              variant="secondary"
              className="px-3 py-2 rounded-xl text-sm"
            >
              Save View
            </Button>
            {savedViews.length > 0 && (
              <select
                onChange={(e) => {
                  const v = savedViews.find((x) => x.name === e.target.value);
                  if (v) applyView(v);
                }}
                className="rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-white focus:border-cyan-500 focus:outline-none"
                defaultValue=""
              >
                <option value="" disabled>Select view</option>
                {savedViews.map((v) => (
                  <option key={v.name} value={v.name}>{v.name}</option>
                ))}
              </select>
            )}
          </div>

          {/* Saved Leads */}
          {savedLeads.length > 0 ? (
            <div className="rounded-2xl bg-gradient-to-br from-zinc-900 to-zinc-900/50 border border-zinc-800 overflow-hidden">
              <div className="p-3 flex items-center justify-between text-sm text-zinc-400 border-b border-zinc-800">
                <span>{total} leads</span>
                <div className="flex gap-2 items-center">
                  <button
                    onClick={() => loadSavedLeads(Math.max(1, page - 1))}
                    disabled={page === 1}
                    className="px-3 py-1 rounded-lg bg-zinc-800 border border-zinc-700 text-xs disabled:opacity-50"
                  >
                    Prev
                  </button>
                  <span className="text-xs text-zinc-400">Page {page}</span>
                  <button
                    onClick={() => loadSavedLeads(page * pageSize < total ? page + 1 : page)}
                    disabled={page * pageSize >= total}
                    className="px-3 py-1 rounded-lg bg-zinc-800 border border-zinc-700 text-xs disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
              </div>
              <Table density={density}>
                <TableHead>
                  <TableRow>
                <TableHeaderCell>Platform</TableHeaderCell>
                <TableHeaderCell>Title / Snippet</TableHeaderCell>
                <TableHeaderCell>Intent</TableHeaderCell>
                <TableHeaderCell
                  className="cursor-pointer"
                  onClick={() => {
                    const nextOrder = sortBy === "intent_score" && sortOrder === "desc" ? "asc" : "desc";
                    setSortBy("intent_score");
                    setSortOrder(nextOrder);
                    loadSavedLeads(1);
                  }}
                >
                  Score {sortBy === "intent_score" ? (sortOrder === "desc" ? "▼" : "▲") : ""}
                </TableHeaderCell>
                <TableHeaderCell
                  className="cursor-pointer"
                  onClick={() => {
                    const nextOrder = sortBy === "discovered_at" && sortOrder === "desc" ? "asc" : "desc";
                    setSortBy("discovered_at");
                    setSortOrder(nextOrder);
                    loadSavedLeads(1);
                  }}
                >
                  Seen {sortBy === "discovered_at" ? (sortOrder === "desc" ? "▼" : "▲") : ""}
                </TableHeaderCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {pagedSaved.map((lead, i) => (
                    <TableRow key={i}>
                      <TableCell className="flex items-center gap-2">
                        <Badge variant="neutral">{lead.platform}</Badge>
                        {lead.author_username && <span className="text-xs text-zinc-400">@{lead.author_username}</span>}
                      </TableCell>
                      <TableCell>
                        <div className="font-medium text-white line-clamp-1">{lead.title || "—"}</div>
                        <div className="text-xs text-zinc-400 line-clamp-2">{lead.text_excerpt || lead.text}</div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={lead.intent_level === "high" ? "success" : lead.intent_level === "medium" ? "info" : "neutral"}>
                          {lead.intent_level}
                        </Badge>
                        {lead.reason_for_relevance && (
                          <div className="text-[11px] text-zinc-500 mt-1 line-clamp-2">{lead.reason_for_relevance}</div>
                        )}
                      </TableCell>
                      <TableCell>{(lead.intent_score * 100).toFixed(0)}%</TableCell>
                      <TableCell className="text-xs text-zinc-400">
                        {lead.discovered_at ? new Date(lead.discovered_at).toLocaleDateString() : "—"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <div className="text-center py-16">
              <div className="text-6xl mb-4">💾</div>
              <h3 className="text-xl font-semibold text-zinc-300">No Saved Leads</h3>
              <p className="text-zinc-500 mt-2">Search social media to discover and save leads</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function LeadCard({ lead }: { lead: SocialLead }) {
  const getIntentBadge = (level: string) => {
    switch (level) {
      case 'high': return 'bg-green-500/20 text-green-400 border-green-500/30';
      case 'medium': return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
      default: return 'bg-zinc-500/20 text-zinc-400 border-zinc-500/30';
    }
  };

  const getPlatformIcon = (platform: string) => {
    switch (platform) {
      case 'twitter': return '𝕏';
      case 'reddit': return '🔴';
      case 'forum': case 'quora': return '💬';
      default: return '🌐';
    }
  };

  return (
    <div className="p-4 hover:bg-zinc-800/50 transition">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          {lead.title && (
            <a 
              href={lead.url} 
              target="_blank" 
              rel="noopener noreferrer" 
              className="font-medium text-cyan-400 hover:text-cyan-300 transition line-clamp-1"
            >
              {lead.title}
            </a>
          )}
          <p className="text-sm text-zinc-300 mt-1 line-clamp-2">{lead.text_excerpt || lead.text}</p>
          
          {/* Author Info */}
          {lead.author_username && (
            <div className="flex items-center gap-2 mt-2 text-xs text-zinc-500">
              <span>@{lead.author_username}</span>
              {lead.author_company && <span>• {lead.author_company}</span>}
              {lead.author_title && <span>• {lead.author_title}</span>}
              {lead.author_followers && <span>• {lead.author_followers.toLocaleString()} followers</span>}
            </div>
          )}
          
          {/* Tags */}
          <div className="flex flex-wrap gap-2 mt-3">
            <span className="px-2 py-1 text-xs rounded-full bg-zinc-800 text-zinc-300 border border-zinc-700">
              {getPlatformIcon(lead.platform)} {lead.platform}
            </span>
            <span className={`px-2 py-1 text-xs rounded-full border ${getIntentBadge(lead.intent_level)}`}>
              {lead.intent_level} intent ({(lead.intent_score * 100).toFixed(0)}%)
            </span>
            {lead.intent_keywords_matched?.slice(0, 2).map(kw => (
              <span key={kw} className="px-2 py-1 text-xs rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/20">
                {kw}
              </span>
            ))}
            {lead.product_keywords_matched?.slice(0, 3).map(kw => (
              <span key={kw} className="px-2 py-1 text-xs rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                {kw}
              </span>
            ))}
          </div>
        </div>
        
        <a 
          href={lead.url} 
          target="_blank" 
          rel="noopener noreferrer" 
          className="px-3 py-1 text-xs rounded-lg bg-zinc-800 border border-zinc-700 text-zinc-300 hover:bg-zinc-700 transition"
        >
          View →
        </a>
      </div>
    </div>
  );
}
