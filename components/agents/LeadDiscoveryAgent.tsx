"use client";

import { useState, useEffect } from "react";
import {
  discoverCompanies,
  discoverContacts,
  generateEmailCandidates,
  getDiscoveredCompanies,
  getDiscoveredContacts,
  getLeadGenStats,
  type DiscoveredCompany,
  type DiscoveredContact,
  type EmailCandidate,
  type LeadGenStats,
} from "@/lib/api/agents";
import { Table, TableHead, TableBody, TableRow, TableHeaderCell, TableCell } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { useToast } from "@/components/ui/Toaster";
import { Button } from "@/components/ui/Button";

function parseTargetTitles(raw: string): string[] {
  const parts = raw.split(/[\n,]+/).map((part) => part.trim()).filter(Boolean);
  const seen = new Set<string>();
  const titles: string[] = [];
  for (const part of parts) {
    const key = part.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    titles.push(part);
  }
  return titles;
}

function formatEmailStatus(contact: DiscoveredContact): { label: string; variant: "neutral" | "info" | "warning" | "success" } {
  const status = (contact.email_status || "").toLowerCase();
  if (status === "pattern_guess") {
    return { label: "Pattern Guess", variant: "warning" };
  }
  if (status === "verified" && contact.email) {
    return { label: "Verified", variant: "success" };
  }
  if (status === "likely" && contact.email) {
    return { label: "Likely", variant: "info" };
  }
  if (!contact.email || status === "not_found") {
    return { label: "Not Found", variant: "neutral" };
  }
  return { label: "Unverified", variant: "info" };
}

function formatContactSource(contact: DiscoveredContact): string {
  const raw = (contact.provider || contact.source || "").toLowerCase();
  if (raw === "prospeo") {
    return "Prospeo";
  }
  if (raw === "company_website" || raw === "website") {
    return "Company Website";
  }
  if (raw === "linkedin") {
    return (contact.provider || "").toLowerCase() === "prospeo" ? "Prospeo" : "Company Website";
  }
  if (!raw) {
    return "Company Website";
  }
  return contact.provider || contact.source || "Company Website";
}

export default function LeadDiscoveryAgent() {
  const [activeTab, setActiveTab] = useState<"companies" | "contacts" | "email">("companies");
  const [stats, setStats] = useState<LeadGenStats | null>(null);
  const [density, setDensity] = useState<"comfortable" | "compact">("comfortable");
  const toast = useToast();
  
  useEffect(() => {
    loadStats();
    const savedDensity = typeof window !== "undefined" ? localStorage.getItem("lead-density") : null;
    if (savedDensity === "compact" || savedDensity === "comfortable") setDensity(savedDensity);
  }, []);

  const loadStats = async () => {
    try {
      const s = await getLeadGenStats();
      setStats(s);
    } catch (e) {
      console.error("Failed to load stats:", e);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
            Lead Discovery
          </h1>
          <p className="text-zinc-400 mt-1">Discover companies and IT / engineering decision makers</p>
        </div>
        
        {/* Stats Cards */}
        {stats && (
          <div className="flex gap-3">
            <div className="px-4 py-2 rounded-xl bg-zinc-800/50 border border-zinc-700">
              <div className="text-2xl font-bold text-purple-400">{stats.total_companies}</div>
              <div className="text-xs text-zinc-500">Companies</div>
            </div>
            <div className="px-4 py-2 rounded-xl bg-zinc-800/50 border border-zinc-700">
              <div className="text-2xl font-bold text-pink-400">{stats.total_contacts}</div>
              <div className="text-xs text-zinc-500">Contacts</div>
            </div>
            <div className="px-4 py-2 rounded-xl bg-zinc-800/50 border border-zinc-700">
              <div className="text-2xl font-bold text-green-400">{stats.contacts_with_email}</div>
              <div className="text-xs text-zinc-500">With Email</div>
            </div>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-zinc-800 pb-2">
        {[
          { key: "companies", label: "🏢 Companies" },
          { key: "contacts", label: "👤 Contacts" },
          { key: "email", label: "✉️ Email Finder" },
        ].map((tab) => (
          <Button
            key={tab.key}
            variant={activeTab === tab.key ? "primary" : "ghost"}
            onClick={() => setActiveTab(tab.key as any)}
            className={`px-4 py-2 rounded-t-lg ${activeTab === tab.key ? "bg-purple-500/20 text-purple-100" : "text-zinc-300"}`}
          >
            {tab.label}
          </Button>
        ))}
      </div>

      {activeTab === "companies" && <CompaniesTab onRefresh={loadStats} density={density} setDensity={setDensity} toast={toast} />}
      {activeTab === "contacts" && <ContactsTab onRefresh={loadStats} density={density} setDensity={setDensity} toast={toast} />}
      {activeTab === "email" && <EmailFinderTab />}
    </div>
  );
}

function CompaniesTab({
  onRefresh,
  density,
  setDensity,
  toast,
}: {
  onRefresh: () => void;
  density: "comfortable" | "compact";
  setDensity: (d: "comfortable" | "compact") => void;
  toast: ReturnType<typeof useToast>;
}) {
  const [companyNames, setCompanyNames] = useState("");
  const [discoverWebsites, setDiscoverWebsites] = useState(true);
  const [enrich, setEnrich] = useState(true);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<DiscoveredCompany[]>([]);
  const [savedCompanies, setSavedCompanies] = useState<DiscoveredCompany[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showSaved, setShowSaved] = useState(false);
  const [industryFilter, setIndustryFilter] = useState<string>("");
  const [targetOnly, setTargetOnly] = useState<boolean>(false);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 20;
  const [savedViews, setSavedViews] = useState<{ name: string; industry?: string; targetOnly?: boolean }[]>(() => {
    if (typeof window === "undefined") return [];
    const raw = localStorage.getItem("company-views");
    return raw ? JSON.parse(raw) : [];
  });

  const loadSavedCompanies = async (targetPage?: number) => {
    const nextPage = targetPage ?? page;
    setLoading(true);
    try {
      const response = await getDiscoveredCompanies({ 
        limit: pageSize, 
        offset: (nextPage - 1) * pageSize,
        industry: industryFilter || undefined, 
        is_target: targetOnly ? true : undefined 
      });
      setSavedCompanies(response.companies || []);
      setTotal(response.count || 0);
      setPage(nextPage);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDiscover = async () => {
    setLoading(true);
    setError(null);
    try {
      const names = companyNames.split("\n").map(n => n.trim()).filter(Boolean);
      if (names.length === 0) {
        setError("Please enter at least one company name");
        return;
      }
      const response = await discoverCompanies({
        company_names: names,
        discover_websites: discoverWebsites,
        enrich,
      });
      setResults(response.companies || []);
      onRefresh();
      toast({ title: "Discovery complete", description: `${response.companies?.length || 0} companies`, variant: "success" });
    } catch (e: any) {
      setError(e.message);
      toast({ title: "Discovery failed", description: e.message, variant: "error" });
    } finally {
      setLoading(false);
    }
  };

  const exportCompanies = (companies: DiscoveredCompany[]) => {
    const csv = [
      "Name,Domain,Industry,Employees,Revenue,Location,LinkedIn,Target Score",
      ...companies.map(c => 
        `"${c.name}","${c.domain || ''}","${c.industry || ''}","${c.employee_range || c.employee_count || ''}","${c.revenue_range || c.revenue_usd || ''}","${[c.headquarters_city, c.headquarters_state, c.headquarters_country].filter(Boolean).join(', ')}","${c.linkedin_url || ''}",${c.target_score?.toFixed(2) || 0}`
      )
    ].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `companies-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    toast({ title: "Exported", description: `${companies.length} rows`, variant: "success" });
  };

  const paged = savedCompanies;

  const saveView = () => {
    const view = { name: `View ${savedViews.length + 1}`, industry: industryFilter || undefined, targetOnly };
    const next = [...savedViews, view];
    setSavedViews(next);
    localStorage.setItem("company-views", JSON.stringify(next));
    toast({ title: "View saved", variant: "success" });
  };

  const applyView = (v: { name: string; industry?: string; targetOnly?: boolean }) => {
    setIndustryFilter(v.industry || "");
    setTargetOnly(!!v.targetOnly);
    loadSavedCompanies();
  };

  return (
    <div className="space-y-6">
      {/* Toggle */}
      <div className="flex gap-2">
        <Button
          onClick={() => setShowSaved(false)}
          variant={!showSaved ? "primary" : "secondary"}
          className="px-4 py-2 rounded-xl text-sm"
        >
          🔍 Discover New
        </Button>
        <Button
          onClick={() => { setShowSaved(true); loadSavedCompanies(); }}
          variant={showSaved ? "primary" : "secondary"}
          className="px-4 py-2 rounded-xl text-sm"
        >
          💾 Saved Companies
        </Button>
      </div>

      {!showSaved && (
        <>
          {/* Discovery Form */}
          <div className="rounded-2xl bg-gradient-to-br from-zinc-900 to-zinc-900/50 border border-zinc-800 p-6">
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-zinc-400 mb-2 block">Company Names (one per line)</label>
                <textarea
                  value={companyNames}
                  onChange={(e) => setCompanyNames(e.target.value)}
                  rows={5}
                  className="w-full rounded-xl bg-zinc-800/50 border border-zinc-700 px-4 py-3 text-white placeholder-zinc-500 focus:border-purple-500 focus:outline-none transition"
                  placeholder="Walmart&#10;Target Corporation&#10;Best Buy&#10;..."
                />
              </div>
              
              <div className="flex gap-4">
                <label className="flex items-center gap-2 text-sm text-zinc-400">
                  <input
                    type="checkbox"
                    checked={discoverWebsites}
                    onChange={(e) => setDiscoverWebsites(e.target.checked)}
                    className="rounded border-zinc-600"
                  />
                  Discover websites
                </label>
                <label className="flex items-center gap-2 text-sm text-zinc-400">
                  <input
                    type="checkbox"
                    checked={enrich}
                    onChange={(e) => setEnrich(e.target.checked)}
                    className="rounded border-zinc-600"
                  />
                  Enrich company data
                </label>
              </div>

                <Button
                  onClick={handleDiscover}
                  disabled={loading}
                  className="w-full bg-gradient-to-r from-purple-500 to-pink-500 px-6 py-4 font-medium text-white shadow-lg shadow-purple-500/25 hover:shadow-purple-500/40 transition disabled:opacity-50"
                >
                  {loading ? "🔍 Discovering..." : "🏢 Discover Companies"}
                </Button>
            </div>
          </div>

          {error && (
            <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400">{error}</div>
          )}

          {results.length > 0 && (
            <CompanyResultsTable
              companies={results}
              total={results.length}
              page={1}
              pageSize={results.length}
              onPageChange={() => {}}
              density={density}
              onExport={() => exportCompanies(results)}
            />
          )}
        </>
      )}

      {showSaved && (
        <>
          <div className="flex flex-wrap gap-3 items-center mb-3">
            <input
              value={industryFilter}
              onChange={(e) => setIndustryFilter(e.target.value)}
              placeholder="Filter by industry (e.g., Retail)"
              className="rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-white placeholder-zinc-500 focus:border-purple-500 focus:outline-none"
            />
            <label className="flex items-center gap-2 text-sm text-zinc-400">
              <input
                type="checkbox"
                checked={targetOnly}
                onChange={(e) => setTargetOnly(e.target.checked)}
                className="rounded border-zinc-600"
              />
              Target matches only
            </label>
            <Button
              onClick={() => loadSavedCompanies(1)}
              variant="secondary"
              className="px-4 py-2 rounded-lg text-sm"
            >
              Apply Filters
            </Button>
            <Button
              onClick={saveView}
              variant="secondary"
              className="px-4 py-2 rounded-lg text-sm"
            >
              Save View
            </Button>
            {savedViews.length > 0 && (
              <select
                onChange={(e) => {
                  const v = savedViews.find((x) => x.name === e.target.value);
                  if (v) applyView(v);
                }}
                className="rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-white focus:border-purple-500 focus:outline-none"
                defaultValue=""
              >
                <option value="" disabled>Select saved view</option>
                {savedViews.map((v) => (
                  <option key={v.name} value={v.name}>{v.name}</option>
                ))}
              </select>
            )}
            <div className="ml-auto flex items-center gap-2">
              <label className="text-sm text-zinc-400">Density</label>
              <select
                value={density}
                onChange={(e) => { const d = e.target.value as "comfortable" | "compact"; setDensity(d); localStorage.setItem("lead-density", d); }}
                className="rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-white focus:border-purple-500 focus:outline-none"
              >
                <option value="comfortable">Comfortable</option>
                <option value="compact">Compact</option>
              </select>
            </div>
          </div>

          {savedCompanies.length > 0 ? (
            <CompanyResultsTable
              companies={paged}
              total={total}
              page={page}
              pageSize={pageSize}
              onPageChange={(p) => loadSavedCompanies(p)}
              density={density}
              onExport={() => exportCompanies(savedCompanies)}
            />
          ) : (
            <div className="text-center py-16">
              <div className="text-6xl mb-4">🏢</div>
              <h3 className="text-xl font-semibold text-zinc-300">No Saved Companies</h3>
              <p className="text-zinc-500 mt-2">Discover companies to build your prospect database</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function CompanyResultsTable({
  companies,
  total,
  page,
  pageSize,
  onPageChange,
  density,
  onExport,
}: {
  companies: DiscoveredCompany[];
  total: number;
  page: number;
  pageSize: number;
  onPageChange: (p: number) => void;
  density: "comfortable" | "compact";
  onExport: () => void;
}) {
  return (
    <div className="rounded-2xl bg-gradient-to-br from-zinc-900 to-zinc-900/50 border border-zinc-800 overflow-hidden">
      <div className="p-4 border-b border-zinc-800 flex justify-between items-center">
        <div>
          <span className="font-semibold text-white">{total} Companies</span>
          <span className="ml-4 text-sm text-green-400">
            {companies.filter(c => c.is_target_profile).length} match target profile (page)
          </span>
        </div>
        <div className="flex gap-2">
          <button onClick={onExport} className="px-4 py-2 bg-zinc-800 border border-zinc-700 rounded-xl text-sm hover:bg-zinc-700 transition">
            📥 Export CSV
          </button>
        </div>
      </div>
      <Table density={density}>
        <TableHead>
          <TableRow>
            <TableHeaderCell>Company</TableHeaderCell>
            <TableHeaderCell>Industry</TableHeaderCell>
            <TableHeaderCell>Size</TableHeaderCell>
            <TableHeaderCell>Location</TableHeaderCell>
            <TableHeaderCell className="cursor-pointer">
              Target
            </TableHeaderCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {companies.map((c, i) => (
            <TableRow key={i}>
              <TableCell>
                <div className="font-medium text-white">{c.name}</div>
                {c.domain && <div className="text-xs text-cyan-400">{c.domain}</div>}
              </TableCell>
              <TableCell className="text-zinc-300">{c.industry || "-"}</TableCell>
              <TableCell className="text-zinc-300">{c.employee_range || c.employee_count || "-"}</TableCell>
              <TableCell className="text-zinc-400 text-xs">{[c.headquarters_city, c.headquarters_state].filter(Boolean).join(", ") || "-"}</TableCell>
              <TableCell>
                <Badge variant={c.is_target_profile ? "success" : "neutral"}>
                  {(c.target_score * 100).toFixed(0)}%
                </Badge>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <div className="p-3 flex items-center justify-between text-sm text-zinc-400 border-t border-zinc-800">
        <div>Page {page}</div>
        <div className="flex gap-2 items-center">
          <button
            onClick={() => onPageChange(Math.max(1, page - 1))}
            disabled={page === 1}
            className="px-3 py-1 rounded-lg bg-zinc-800 border border-zinc-700 text-xs disabled:opacity-50"
          >
            Prev
          </button>
          <button
            onClick={() => onPageChange(page * pageSize < total ? page + 1 : page)}
            disabled={page * pageSize >= total}
            className="px-3 py-1 rounded-lg bg-zinc-800 border border-zinc-700 text-xs disabled:opacity-50"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}

function ContactsTab({
  onRefresh,
  density,
  setDensity,
  toast,
}: {
  onRefresh: () => void;
  density: "comfortable" | "compact";
  setDensity: (d: "comfortable" | "compact") => void;
  toast: ReturnType<typeof useToast>;
}) {
  const [companyName, setCompanyName] = useState("");
  const [companyDomain, setCompanyDomain] = useState("");
  const [targetTitles, setTargetTitles] = useState("");
  const [maxResults, setMaxResults] = useState(10);
  const [findEmails, setFindEmails] = useState(true);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<DiscoveredContact[]>([]);
  const [savedContacts, setSavedContacts] = useState<DiscoveredContact[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [showSaved, setShowSaved] = useState(false);
  const [hasEmailFilter, setHasEmailFilter] = useState<string>("any");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 25;
  type ContactView = { name: string; hasEmail: string; density: "comfortable" | "compact" };
  const [savedViews, setSavedViews] = useState<ContactView[]>(() => {
    if (typeof window === "undefined") return [];
    const raw = localStorage.getItem("contact-views");
    return raw ? JSON.parse(raw) : [];
  });

  const loadSavedContacts = async (targetPage?: number) => {
    const nextPage = targetPage ?? page;
    setLoading(true);
    try {
      const response = await getDiscoveredContacts({ 
        limit: pageSize, 
        offset: (nextPage - 1) * pageSize,
        has_email: hasEmailFilter === "yes" ? true : hasEmailFilter === "no" ? false : undefined 
      });
      setSavedContacts(response.contacts || []);
      setTotal(response.count || 0);
      setPage(nextPage);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDiscover = async () => {
    setError(null);
    setWarnings([]);
    const name = companyName.trim();
    if (!name) {
      setError("Please enter a company name");
      return;
    }
    const titles = parseTargetTitles(targetTitles);
    if (titles.length === 0) {
      setError("Please enter at least one target job title");
      return;
    }
    if (!Number.isInteger(maxResults) || maxResults < 1 || maxResults > 50) {
      setError("Max results must be a number between 1 and 50");
      return;
    }
    setLoading(true);
    try {
      const response = await discoverContacts({
        company_name: name,
        company_domain: companyDomain.trim() || undefined,
        target_titles: titles,
        max_results: maxResults,
        find_emails: findEmails,
      });
      setResults(response.contacts || []);
      setWarnings(response.warnings || []);
      onRefresh();
      toast({ title: "Contacts found", description: `${response.contacts?.length || 0} contacts`, variant: "success" });
    } catch (e: any) {
      setError(e.message);
      toast({ title: "Discovery failed", description: e.message, variant: "error" });
    } finally {
      setLoading(false);
    }
  };

  const exportContacts = (contacts: DiscoveredContact[]) => {
    const csv = [
      "Name,Title,Company,Email,Email Status,LinkedIn,Source,Seniority",
      ...contacts.map(c => 
        `"${c.full_name}","${c.title}","${c.company_name}","${c.email || ''}","${formatEmailStatus(c).label}","${c.linkedin_url || ''}","${formatContactSource(c)}","${c.seniority_level || ''}"`
      )
    ].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `contacts-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    toast({ title: "Exported", description: `${contacts.length} rows`, variant: "success" });
  };

  const paged = savedContacts;

  const saveView = () => {
    const view: ContactView = { name: `View ${savedViews.length + 1}`, hasEmail: hasEmailFilter, density };
    const next = [...savedViews, view];
    setSavedViews(next);
    localStorage.setItem("contact-views", JSON.stringify(next));
    toast({ title: "View saved", variant: "success" });
  };

  const applyView = (v: ContactView) => {
    setHasEmailFilter(v.hasEmail);
    setDensity(v.density);
    localStorage.setItem("lead-density", v.density);
    loadSavedContacts(1);
  };

  return (
    <div className="space-y-6">
      <div className="flex gap-2">
        <Button
          onClick={() => setShowSaved(false)}
          variant={!showSaved ? "primary" : "secondary"}
          className="px-4 py-2 rounded-xl text-sm"
        >
          🔍 Discover New
        </Button>
        <Button
          onClick={() => { setShowSaved(true); loadSavedContacts(); }}
          variant={showSaved ? "primary" : "secondary"}
          className="px-4 py-2 rounded-xl text-sm"
        >
          💾 Saved Contacts
        </Button>
      </div>

      {!showSaved && (
        <>
          <div className="rounded-2xl bg-gradient-to-br from-zinc-900 to-zinc-900/50 border border-zinc-800 p-6">
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-zinc-400 mb-2 block">Company Name *</label>
                  <input
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    className="w-full rounded-xl bg-zinc-800/50 border border-zinc-700 px-4 py-3 text-white placeholder-zinc-500 focus:border-purple-500 focus:outline-none transition"
                    placeholder="Microsoft"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-zinc-400 mb-2 block">Company Domain</label>
                  <input
                    value={companyDomain}
                    onChange={(e) => setCompanyDomain(e.target.value)}
                    className="w-full rounded-xl bg-zinc-800/50 border border-zinc-700 px-4 py-3 text-white placeholder-zinc-500 focus:border-purple-500 focus:outline-none transition"
                    placeholder="microsoft.com"
                  />
                </div>
              </div>

              <div>
                <label className="text-sm font-medium text-zinc-400 mb-2 block">Target Job Titles *</label>
                <textarea
                  value={targetTitles}
                  onChange={(e) => setTargetTitles(e.target.value)}
                  rows={4}
                  className="w-full rounded-xl bg-zinc-800/50 border border-zinc-700 px-4 py-3 text-white placeholder-zinc-500 focus:border-purple-500 focus:outline-none transition"
                  placeholder={"Head of IT\nIT Director\nVP Infrastructure\nSecurity Director"}
                />
                <p className="text-xs text-zinc-500 mt-2">One per line, or comma-separated.</p>
              </div>

              <div className="grid grid-cols-2 gap-4 items-end">
                <div>
                  <label className="text-sm font-medium text-zinc-400 mb-2 block">Max Results</label>
                  <input
                    type="number"
                    min={1}
                    max={50}
                    value={maxResults}
                    onChange={(e) => setMaxResults(Number(e.target.value))}
                    className="w-full rounded-xl bg-zinc-800/50 border border-zinc-700 px-4 py-3 text-white placeholder-zinc-500 focus:border-purple-500 focus:outline-none transition"
                  />
                </div>
                <label className="flex items-center gap-2 text-sm text-zinc-400 pb-3">
                  <input
                    type="checkbox"
                    checked={findEmails}
                    onChange={(e) => setFindEmails(e.target.checked)}
                    className="rounded border-zinc-600"
                  />
                  Find Work Emails
                </label>
              </div>

            <Button
              onClick={handleDiscover}
              disabled={loading}
              className="w-full bg-gradient-to-r from-purple-500 to-pink-500 px-6 py-4 font-medium text-white shadow-lg shadow-purple-500/25 hover:shadow-purple-500/40 transition disabled:opacity-50"
            >
              {loading ? "🔍 Searching..." : "Find Contacts"}
            </Button>
            </div>
          </div>

          {error && (
            <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400">{error}</div>
          )}

          {warnings.length > 0 && (
            <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl text-amber-200 text-sm space-y-1">
              {warnings.map((warning) => (
                <div key={warning}>{warning}</div>
              ))}
            </div>
          )}

          {results.length > 0 && (
            <ContactResultsTable
              contacts={results}
              total={results.length}
              page={1}
              pageSize={results.length}
              onPageChange={() => {}}
              density={density}
              onExport={() => exportContacts(results)}
            />
          )}

          {!loading && results.length === 0 && !error && (
            <div className="text-center py-16">
              <div className="text-6xl mb-4">👤</div>
              <h3 className="text-xl font-semibold text-zinc-300">Find Target Contacts</h3>
              <p className="text-zinc-500 mt-2">Enter a company and job titles to discover matching decision makers</p>
            </div>
          )}
        </>
      )}

      {showSaved && (
        <>
          <div className="flex flex-wrap gap-3 items-center mb-3">
            <label className="text-sm text-zinc-400">Has Email:</label>
            <select
              value={hasEmailFilter}
              onChange={(e) => setHasEmailFilter(e.target.value)}
              className="rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-white focus:border-purple-500 focus:outline-none"
            >
              <option value="any">Any</option>
              <option value="yes">Yes</option>
              <option value="no">No</option>
            </select>
            <Button
              onClick={() => loadSavedContacts(1)}
              variant="secondary"
              className="px-4 py-2 rounded-lg text-sm"
            >
              Apply Filters
            </Button>
            <Button
              onClick={saveView}
              variant="secondary"
              className="px-4 py-2 rounded-lg text-sm"
            >
              Save View
            </Button>
            {savedViews.length > 0 && (
              <select
                onChange={(e) => {
                  const v = savedViews.find((x) => x.name === e.target.value);
                  if (v) applyView(v);
                }}
                className="rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-white focus:border-purple-500 focus:outline-none"
                defaultValue=""
              >
                <option value="" disabled>Select view</option>
                {savedViews.map((v) => (
                  <option key={v.name} value={v.name}>{v.name}</option>
                ))}
              </select>
            )}
            <div className="ml-auto flex items-center gap-2">
              <label className="text-sm text-zinc-400">Density</label>
              <select
                value={density}
                onChange={(e) => { const d = e.target.value as "comfortable" | "compact"; setDensity(d); localStorage.setItem("lead-density", d); }}
                className="rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-white focus:border-purple-500 focus:outline-none"
              >
                <option value="comfortable">Comfortable</option>
                <option value="compact">Compact</option>
              </select>
            </div>
          </div>

          {savedContacts.length > 0 ? (
            <ContactResultsTable
              contacts={paged}
              total={total}
              page={page}
              pageSize={pageSize}
              onPageChange={(p) => loadSavedContacts(p)}
              density={density}
              onExport={() => exportContacts(savedContacts)}
            />
          ) : (
            <div className="text-center py-16">
              <div className="text-6xl mb-4">👤</div>
              <h3 className="text-xl font-semibold text-zinc-300">No Saved Contacts</h3>
              <p className="text-zinc-500 mt-2">Discover contacts to build your prospect database</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function ContactResultsTable({
  contacts,
  total,
  page,
  pageSize,
  onPageChange,
  density,
  onExport,
}: {
  contacts: DiscoveredContact[];
  total: number;
  page: number;
  pageSize: number;
  onPageChange: (p: number) => void;
  density: "comfortable" | "compact";
  onExport: () => void;
}) {
  return (
    <div className="rounded-2xl bg-gradient-to-br from-zinc-900 to-zinc-900/50 border border-zinc-800 overflow-hidden">
      <div className="p-4 border-b border-zinc-800 flex justify-between items-center">
        <div>
          <span className="font-semibold text-white">{total} Contacts</span>
          <span className="ml-4 text-sm text-green-400">
            {contacts.filter(c => c.email).length} with email (page)
          </span>
        </div>
        <button onClick={onExport} className="px-4 py-2 bg-zinc-800 border border-zinc-700 rounded-xl text-sm hover:bg-zinc-700 transition">
          📥 Export CSV
        </button>
      </div>
      <Table density={density}>
        <TableHead>
          <TableRow>
            <TableHeaderCell>Name</TableHeaderCell>
            <TableHeaderCell>Title</TableHeaderCell>
            <TableHeaderCell>Company</TableHeaderCell>
            <TableHeaderCell>Email</TableHeaderCell>
            <TableHeaderCell>Email Status</TableHeaderCell>
            <TableHeaderCell>LinkedIn</TableHeaderCell>
            <TableHeaderCell>Source</TableHeaderCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {contacts.map((c, i) => (
            <TableRow key={i}>
              <TableCell className="font-medium text-white">{c.full_name}</TableCell>
              <TableCell>
                <div className="text-zinc-300">{c.title}</div>
                {c.seniority_level && (
                  <Badge variant="info">{c.seniority_level}</Badge>
                )}
              </TableCell>
              <TableCell className="text-zinc-300">{c.company_name}</TableCell>
              <TableCell>
                {c.email ? (
                  <span className="text-cyan-400">{c.email}</span>
                ) : (
                  <span className="text-zinc-500">-</span>
                )}
              </TableCell>
              <TableCell>
                {(() => {
                  const status = formatEmailStatus(c);
                  return <Badge variant={status.variant}>{status.label}</Badge>;
                })()}
              </TableCell>
              <TableCell>
                {c.linkedin_url ? (
                  <a href={c.linkedin_url} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">
                    View
                  </a>
                ) : "-"}
              </TableCell>
              <TableCell className="text-zinc-400 text-xs">{formatContactSource(c)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <div className="p-3 flex items-center justify-between text-sm text-zinc-400 border-t border-zinc-800">
        <div>Page {page}</div>
        <div className="flex gap-2 items-center">
          <button
            onClick={() => onPageChange(Math.max(1, page - 1))}
            disabled={page === 1}
            className="px-3 py-1 rounded-lg bg-zinc-800 border border-zinc-700 text-xs disabled:opacity-50"
          >
            Prev
          </button>
          <button
            onClick={() => onPageChange(page * pageSize < total ? page + 1 : page)}
            disabled={page * pageSize >= total}
            className="px-3 py-1 rounded-lg bg-zinc-800 border border-zinc-700 text-xs disabled:opacity-50"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}

function EmailFinderTab() {
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [domain, setDomain] = useState("");
  const [loading, setLoading] = useState(false);
  const [candidates, setCandidates] = useState<EmailCandidate[]>([]);
  const [bestGuess, setBestGuess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    try {
      if (!firstName.trim() || !lastName.trim() || !domain.trim()) {
        setError("Please fill in all fields");
        return;
      }
      const response = await generateEmailCandidates({
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        company_domain: domain.trim(),
        num_patterns: 8,
      });
      setCandidates(response.candidates || []);
      setBestGuess(response.best_guess || null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const copyEmail = (email: string) => {
    navigator.clipboard.writeText(email);
  };

  return (
    <div className="space-y-6">
      <div className="rounded-2xl bg-gradient-to-br from-zinc-900 to-zinc-900/50 border border-zinc-800 p-6">
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="text-sm font-medium text-zinc-400 mb-2 block">First Name</label>
              <input
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                className="w-full rounded-xl bg-zinc-800/50 border border-zinc-700 px-4 py-3 text-white placeholder-zinc-500 focus:border-purple-500 focus:outline-none transition"
                placeholder="John"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-zinc-400 mb-2 block">Last Name</label>
              <input
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                className="w-full rounded-xl bg-zinc-800/50 border border-zinc-700 px-4 py-3 text-white placeholder-zinc-500 focus:border-purple-500 focus:outline-none transition"
                placeholder="Smith"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-zinc-400 mb-2 block">Company Domain</label>
              <input
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                className="w-full rounded-xl bg-zinc-800/50 border border-zinc-700 px-4 py-3 text-white placeholder-zinc-500 focus:border-purple-500 focus:outline-none transition"
                placeholder="acme.com"
              />
            </div>
          </div>

          <button
            onClick={handleGenerate}
            disabled={loading}
            className="w-full rounded-xl bg-gradient-to-r from-purple-500 to-pink-500 px-6 py-4 font-medium text-white shadow-lg shadow-purple-500/25 hover:shadow-purple-500/40 transition disabled:opacity-50"
          >
            {loading ? "⏳ Generating..." : "✉️ Generate Email Candidates"}
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400">{error}</div>
      )}

      {bestGuess && (
        <div className="p-4 bg-green-500/10 border border-green-500/20 rounded-xl">
          <div className="text-sm text-green-400 mb-1">Best Guess</div>
          <div className="flex items-center gap-3">
            <span className="text-xl font-medium text-white">{bestGuess}</span>
            <button
              onClick={() => copyEmail(bestGuess)}
              className="px-3 py-1 text-sm rounded-lg bg-green-500/20 text-green-400 hover:bg-green-500/30 transition"
            >
              📋 Copy
            </button>
          </div>
        </div>
      )}

      {candidates.length > 0 && (
        <div className="rounded-2xl bg-gradient-to-br from-zinc-900 to-zinc-900/50 border border-zinc-800 overflow-hidden">
          <div className="p-4 border-b border-zinc-800">
            <span className="font-semibold text-white">{candidates.length} Email Candidates</span>
          </div>
          <div className="divide-y divide-zinc-800">
            {candidates.map((c, i) => (
              <div key={i} className="p-4 flex items-center justify-between hover:bg-zinc-800/50 transition">
                <div className="flex items-center gap-4">
                  <span className="font-mono text-cyan-400">{c.email}</span>
                  <span className="px-2 py-1 text-xs rounded-full bg-zinc-800 text-zinc-400">
                    {c.pattern_used}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-24 bg-zinc-800 rounded-full h-2">
                    <div 
                      className="bg-gradient-to-r from-purple-500 to-pink-500 h-2 rounded-full"
                      style={{ width: `${c.confidence * 100}%` }}
                    />
                  </div>
                  <span className="text-xs text-zinc-400 w-12">{(c.confidence * 100).toFixed(0)}%</span>
                  <button
                    onClick={() => copyEmail(c.email)}
                    className="px-3 py-1 text-xs rounded-lg bg-zinc-800 border border-zinc-700 text-zinc-300 hover:bg-zinc-700 transition"
                  >
                    📋
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {!loading && candidates.length === 0 && (
        <div className="text-center py-16">
          <div className="text-6xl mb-4">✉️</div>
          <h3 className="text-xl font-semibold text-zinc-300">Email Pattern Generator</h3>
          <p className="text-zinc-500 mt-2">Generate likely email addresses using common corporate patterns</p>
        </div>
      )}
    </div>
  );
}

