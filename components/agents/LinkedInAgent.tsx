"use client";

import { useState, useEffect, useRef } from "react";
import {
  generateLinkedInDM,
  uploadCSV,
  getCSVTemplate,
  getSavedProspects,
  saveProspect,
  saveProspectsBulk,
  deleteSavedProspect,
  deleteAllSavedProspects,
  getProducts,
  getLinkedInTemplates,
  type LinkedInDMInput,
  type SavedProspect,
  type ChillionProduct,
  type Template,
} from "@/lib/api/agents";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useToast } from "@/components/ui/Toaster";

export default function LinkedInAgent() {
  const [prospects, setProspects] = useState<SavedProspect[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [products, setProducts] = useState<ChillionProduct[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [messages, setMessages] = useState<Array<{ prospect: SavedProspect; message: string; copied: boolean }>>([]);
  const [selectedMessage, setSelectedMessage] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [selectedProduct, setSelectedProduct] = useState("it_infrastructure");
  const [selectedTemplate, setSelectedTemplate] = useState("custom");
  const [customContext, setCustomContext] = useState("");
  const [inputMode, setInputMode] = useState<"list" | "add" | "csv">("list");
  const [conversationStage, setConversationStage] = useState("not_contacted");
  const [filterQuery, setFilterQuery] = useState("");
  const [filterHasLinkedIn, setFilterHasLinkedIn] = useState<"any" | "yes" | "no">("any");
  const copyAllRef = useRef<HTMLButtonElement>(null);
  const toast = useToast();

  const nameRef = useRef<HTMLInputElement>(null);
  const titleRef = useRef<HTMLInputElement>(null);
  const companyRef = useRef<HTMLInputElement>(null);
  const industryRef = useRef<HTMLInputElement>(null);
  const linkedinRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [p, prod, tmpl] = await Promise.all([getSavedProspects(), getProducts(), getLinkedInTemplates()]);
      setProspects(p);
      setProducts(prod);
      setTemplates(tmpl);
    } finally {
      setLoading(false);
    }
  };

  const handleAddProspect = async () => {
    const name = nameRef.current?.value?.trim();
    if (!name) return setError("Name is required");
    try {
      const saved = await saveProspect({
        name,
        title: titleRef.current?.value?.trim(),
        company: companyRef.current?.value?.trim(),
        industry: industryRef.current?.value?.trim(),
        linkedin_url: linkedinRef.current?.value?.trim(),
        source: "manual",
      });
      setProspects([saved, ...prospects]);
      setInputMode("list");
      toast({ title: "Prospect added", variant: "success" });
      // Clear form
      if (nameRef.current) nameRef.current.value = "";
      if (titleRef.current) titleRef.current.value = "";
      if (companyRef.current) companyRef.current.value = "";
      if (industryRef.current) industryRef.current.value = "";
      if (linkedinRef.current) linkedinRef.current.value = "";
    } catch (e: any) {
      setError(e.message);
      toast({ title: "Add failed", description: e.message, variant: "error" });
    }
  };

  const handleGenerate = async () => {
    const selected = prospects.filter(p => selectedIds.has(p.id));
    if (!selected.length) return setError("Select prospects first");
    setGenerating(true);
    setError(null);
    const msgs: typeof messages = [];
    
    for (const prospect of selected) {
      try {
        const output = await generateLinkedInDM({
          prospect_profile: { name: prospect.name, title: prospect.title, company: prospect.company, industry: prospect.industry },
          conversation_stage: conversationStage,
          offer_context: { product_name: products.find(p => p.key === selectedProduct)?.name || "Chillion", value_propositions: ["Single partner for infrastructure, security, and engineering delivery"] },
          product_key: selectedProduct,
          template_key: selectedTemplate,
          custom_message: customContext || undefined,
        });
        msgs.push({ prospect, message: output.message_text, copied: false });
      } catch (e: any) {
        msgs.push({ prospect, message: `Error: ${e.message}`, copied: false });
      }
    }
    
    setMessages(msgs);
    setSelectedMessage(msgs.length ? 0 : null);
    setGenerating(false);
    toast({ title: "Generated", description: `${msgs.length} messages`, variant: "success" });
  };

  const copyMessage = (idx: number) => {
    navigator.clipboard.writeText(messages[idx].message);
    const u = [...messages];
    u[idx].copied = true;
    setMessages(u);
  };

  const copyAllMessages = () => {
    if (!messages.length) return;
    const text = messages
      .map((m, i) => `${i + 1}. ${m.prospect.name}${m.prospect.company ? " @ " + m.prospect.company : ""}\n${m.message}`)
      .join("\n\n---\n\n");
    navigator.clipboard.writeText(text);
    setSuccess("All messages copied");
    setTimeout(() => setSuccess(null), 2000);
  };

  const toggleSelect = (id: number) => {
    const s = new Set(selectedIds);
    if (s.has(id)) s.delete(id);
    else s.add(id);
    setSelectedIds(s);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">
            LinkedIn DM Agent
          </h1>
          <p className="text-zinc-400 mt-1">Generate personalized LinkedIn messages</p>
        </div>
        {prospects.length > 0 && (
          <button
            onClick={() => { if (confirm("Delete all prospects?")) deleteAllSavedProspects().then(() => setProspects([])); }}
            className="text-sm text-red-400 hover:text-red-300"
          >
            Clear all prospects
          </button>
        )}
      </div>

      {/* Alerts */}
      {error && <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400">{error}<button onClick={() => setError(null)} className="float-right">✕</button></div>}
      {success && <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-emerald-400">✓ {success}</div>}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Left - Prospects & Settings */}
        <div className="space-y-6">
          {/* Prospects Card */}
          <div className="rounded-2xl bg-gradient-to-br from-zinc-900 to-zinc-900/50 border border-zinc-800 p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-white flex items-center gap-2">
                <span className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-500 flex items-center justify-center text-sm">👥</span>
                Prospects ({prospects.length})
              </h3>
              <div className="flex gap-1">
                {["list", "add", "csv"].map(m => (
                  <button
                    key={m}
                    onClick={() => setInputMode(m as any)}
                    className={`px-3 py-1.5 text-xs rounded-lg transition ${inputMode === m ? "bg-gradient-to-r from-blue-500 to-indigo-500 text-white" : "bg-zinc-800 text-zinc-400 hover:text-white"}`}
                  >
                    {m === "list" ? "📋 List" : m === "add" ? "➕ Add" : "📄 CSV"}
                  </button>
                ))}
              </div>
            </div>

            {inputMode === "list" && (
              <>
                {prospects.length === 0 ? (
                  <div className="text-center py-8 text-zinc-500">No prospects yet. Add manually or upload CSV.</div>
                ) : (
                  <>
                    <div className="flex flex-wrap items-center gap-3 text-xs text-zinc-500 mb-3">
                      <span>{selectedIds.size} selected</span>
                      <button onClick={() => setSelectedIds(new Set(prospects.map(p => p.id)))} className="text-blue-400 hover:text-blue-300">All</button>
                      <button onClick={() => setSelectedIds(new Set())} className="hover:text-white">None</button>
                      <input
                        value={filterQuery}
                        onChange={(e) => setFilterQuery(e.target.value)}
                        placeholder="Filter by name, title, company"
                        className="ml-auto rounded-lg bg-zinc-800 border border-zinc-700 px-2 py-1 text-[11px] text-white placeholder-zinc-500 focus:border-blue-500 focus:outline-none"
                      />
                      <select
                        value={filterHasLinkedIn}
                        onChange={(e) => setFilterHasLinkedIn(e.target.value as any)}
                        className="rounded bg-zinc-800 border border-zinc-700 px-2 py-1 text-[11px] text-white focus:border-blue-500 focus:outline-none"
                      >
                        <option value="any">Any LinkedIn</option>
                        <option value="yes">Has LinkedIn</option>
                        <option value="no">No LinkedIn</option>
                      </select>
                    </div>
                    <div className="border border-zinc-800 rounded-xl max-h-48 overflow-y-auto">
                      {prospects
                        .filter(p => {
                          const q = filterQuery.toLowerCase();
                          const matches = !q || [p.name, p.title, p.company].some(x => x?.toLowerCase().includes(q));
                          const ln = !!p.linkedin_url;
                          const lnOk = filterHasLinkedIn === "any" ? true : filterHasLinkedIn === "yes" ? ln : !ln;
                          return matches && lnOk;
                        })
                        .map(p => (
                        <div
                          key={p.id}
                          onClick={() => toggleSelect(p.id)}
                          className={`flex items-center gap-3 p-3 border-b border-zinc-800 last:border-0 cursor-pointer hover:bg-zinc-800/50 transition ${selectedIds.has(p.id) ? "bg-blue-500/10" : ""}`}
                        >
                          <input type="checkbox" checked={selectedIds.has(p.id)} readOnly className="rounded bg-zinc-700 border-zinc-600 text-blue-500" />
                          <div className="flex-1 min-w-0">
                            <div className="font-medium text-white text-sm truncate">{p.name}</div>
                            <div className="text-xs text-zinc-500 truncate">{[p.title, p.company].filter(Boolean).join(" @ ")}</div>
                          </div>
                          {p.linkedin_url && <span className="text-blue-400 text-xs">🔗</span>}
                          <button onClick={(e) => { e.stopPropagation(); deleteSavedProspect(p.id).then(() => setProspects(prospects.filter(x => x.id !== p.id))); }} className="text-red-400 hover:text-red-300 text-xs">✕</button>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </>
            )}

            {inputMode === "add" && (
              <div className="space-y-4">
                <div className="grid gap-4 grid-cols-2">
                  <div>
                    <label className="text-xs text-zinc-400 block mb-1">Name *</label>
                    <input ref={nameRef} className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-white text-sm focus:border-blue-500 focus:outline-none" placeholder="John Smith" />
                  </div>
                  <div>
                    <label className="text-xs text-zinc-400 block mb-1">Title</label>
                    <input ref={titleRef} className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-white text-sm focus:border-blue-500 focus:outline-none" placeholder="CFO" />
                  </div>
                  <div>
                    <label className="text-xs text-zinc-400 block mb-1">Company</label>
                    <input ref={companyRef} className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-white text-sm focus:border-blue-500 focus:outline-none" placeholder="Acme Corp" />
                  </div>
                  <div>
                    <label className="text-xs text-zinc-400 block mb-1">Industry</label>
                    <input ref={industryRef} className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-white text-sm focus:border-blue-500 focus:outline-none" placeholder="Manufacturing" />
                  </div>
                  <div className="col-span-2">
                    <label className="text-xs text-zinc-400 block mb-1">LinkedIn URL</label>
                    <input ref={linkedinRef} className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-white text-sm focus:border-blue-500 focus:outline-none" placeholder="https://linkedin.com/in/..." />
                  </div>
                </div>
                <div className="flex gap-2">
                  <button onClick={handleAddProspect} className="px-4 py-2 bg-gradient-to-r from-blue-500 to-indigo-500 text-white text-sm rounded-lg font-medium">Save Prospect</button>
                  <button onClick={() => setInputMode("list")} className="px-4 py-2 bg-zinc-800 text-sm rounded-lg">Cancel</button>
                </div>
              </div>
            )}

            {inputMode === "csv" && (
              <div className="space-y-4">
                <input
                  type="file"
                  accept=".csv"
                  onChange={async (e) => {
                    const f = e.target.files?.[0];
                    if (!f) return;
                    try {
                      const r = await uploadCSV(f);
                      if (r.prospects?.length) {
                        await saveProspectsBulk(r.prospects.map(p => ({ ...p, source: "csv" })));
                        setProspects(await getSavedProspects());
                        setSuccess(`Imported ${r.prospects.length} prospects`);
                        setInputMode("list");
                      }
                    } catch (err: any) {
                      setError(err.message);
                    }
                  }}
                  className="text-sm text-zinc-400"
                />
                <button
                  onClick={async () => {
                    const c = await getCSVTemplate();
                    const b = new Blob([c], { type: "text/csv" });
                    const a = document.createElement("a");
                    a.href = URL.createObjectURL(b);
                    a.download = "prospects-template.csv";
                    a.click();
                  }}
                  className="text-sm text-blue-400 hover:text-blue-300"
                >
                  📥 Download CSV Template
                </button>
              </div>
            )}
          </div>

          {/* Settings Card */}
          <div className="rounded-2xl bg-gradient-to-br from-zinc-900 to-zinc-900/50 border border-zinc-800 p-6">
            <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
              <span className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-500 flex items-center justify-center text-sm">⚙️</span>
              Message Settings
            </h3>
            <div className="space-y-4">
              <div>
                <label className="text-xs text-zinc-400 block mb-1">Product to Pitch</label>
                <select value={selectedProduct} onChange={e => setSelectedProduct(e.target.value)} className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2.5 text-white text-sm focus:border-blue-500 focus:outline-none">
                  {products.map(p => <option key={p.key} value={p.key}>{p.name}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-zinc-400 block mb-1">Message Template</label>
                <select value={selectedTemplate} onChange={e => setSelectedTemplate(e.target.value)} className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2.5 text-white text-sm focus:border-blue-500 focus:outline-none">
                  {templates.map(t => <option key={t.key} value={t.key}>{t.name}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-zinc-400 block mb-1">Conversation Stage</label>
                <select value={conversationStage} onChange={e => setConversationStage(e.target.value)} className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2.5 text-white text-sm focus:border-blue-500 focus:outline-none">
                  <option value="not_contacted">Not contacted</option>
                  <option value="follow_up">Follow-up</option>
                  <option value="reconnect">Reconnection</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-zinc-400 block mb-1">Custom Context (optional)</label>
                <textarea
                  value={customContext}
                  onChange={e => setCustomContext(e.target.value)}
                  rows={3}
                  className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2.5 text-white text-sm focus:border-blue-500 focus:outline-none resize-none"
                  placeholder="Add specific talking points, pain points to mention..."
                />
              </div>
            </div>
            <button
              onClick={handleGenerate}
              disabled={generating || selectedIds.size === 0}
              className="mt-4 w-full rounded-xl bg-gradient-to-r from-blue-500 to-indigo-500 px-6 py-3 font-medium text-white shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40 transition disabled:opacity-50"
            >
              {generating ? "✨ Generating..." : `✨ Generate ${selectedIds.size} Messages`}
            </button>
          </div>
        </div>

        {/* Right - Generated Messages */}
        <div className="rounded-2xl bg-gradient-to-br from-zinc-900 to-zinc-900/50 border border-zinc-800 overflow-hidden">
          <div className="grid md:grid-cols-2">
            <div className="border-r border-zinc-800">
              <div className="p-4 border-b border-zinc-800 bg-gradient-to-r from-blue-500/10 to-indigo-500/10 flex items-center justify-between">
                <h3 className="font-semibold text-white">📝 Generated Messages ({messages.length})</h3>
                {messages.length > 0 && (
                  <div className="flex gap-2">
                    <Button
                      onClick={copyAllMessages}
                      variant="secondary"
                      className="px-3 py-1.5 text-xs"
                    >
                      📋 Copy All
                    </Button>
                  </div>
                )}
              </div>
              <div className="max-h-[600px] overflow-y-auto divide-y divide-zinc-800">
                {messages.length === 0 ? (
                  <div className="text-center py-16 text-zinc-500">
                    <div className="text-5xl mb-4">💬</div>
                    <p className="font-medium">No messages yet</p>
                    <p className="text-sm">Select prospects and click generate</p>
                  </div>
                ) : (
                  messages.map((item, i) => (
                    <div
                      key={i}
                      className={`p-3 cursor-pointer hover:bg-zinc-800/50 transition ${selectedMessage === i ? "bg-blue-500/10" : ""}`}
                      onClick={() => setSelectedMessage(i)}
                    >
                      <div className="flex justify-between items-center">
                        <div className="font-medium text-white text-sm line-clamp-1">{item.prospect.name}</div>
                        <Button
                          onClick={(e) => { e.stopPropagation(); copyMessage(i); }}
                          variant="secondary"
                          className="px-2 py-1 text-xs"
                        >
                          {item.copied ? "✓ Copied" : "📋 Copy"}
                        </Button>
                      </div>
                      <div className="text-xs text-zinc-500 line-clamp-2 mt-1">{item.message}</div>
                    </div>
                  ))
                )}
              </div>
            </div>
            <div className="p-4">
              <h3 className="font-semibold text-white mb-2">Preview</h3>
              {selectedMessage === null || !messages[selectedMessage] ? (
                <div className="text-sm text-zinc-500">Select a message to preview.</div>
              ) : (
                <div className="space-y-3">
                  <div className="text-sm text-zinc-400">
                    {messages[selectedMessage].prospect.name}
                    {messages[selectedMessage].prospect.company && ` @ ${messages[selectedMessage].prospect.company}`}
                  </div>
                  <div className="text-sm text-zinc-200 whitespace-pre-wrap bg-zinc-900/60 border border-zinc-800 rounded-xl p-4">
                    {messages[selectedMessage].message}
                  </div>
                  <div className="text-xs text-zinc-500">
                    {messages[selectedMessage].message.length} characters
                    {messages[selectedMessage].message.length > 300 && <span className="text-amber-400 ml-2">⚠️ May exceed LinkedIn limit</span>}
                  </div>
                  <div className="flex gap-2">
                    <Button variant="secondary" onClick={() => copyMessage(selectedMessage)} className="text-sm">
                      📋 Copy
                    </Button>
                    <Button variant="secondary" onClick={copyAllMessages} className="text-sm">
                      📋 Copy All
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

