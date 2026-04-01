"use client";

import { useState, useEffect, useRef } from "react";
import {
  generateEmail,
  uploadCSV,
  getSavedProspects,
  saveProspect,
  saveProspectsBulk,
  deleteSavedProspect,
  getProducts,
  getEmailTemplates,
  getGmailStatus,
  getGmailAuthUrl,
  createGmailDrafts,
  disconnectGmail,
  type EmailConversationInput,
  type EmailDraft,
  type SavedProspect,
  type ChillionProduct,
  type Template,
} from "@/lib/api/agents";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toaster";

export default function EmailAgent() {
  const [prospects, setProspects] = useState<SavedProspect[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [products, setProducts] = useState<ChillionProduct[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [drafts, setDrafts] = useState<Array<{ prospect: SavedProspect; draft: EmailDraft; copied: boolean }>>([]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [gmailConnected, setGmailConnected] = useState(false);
  const [gmailEmail, setGmailEmail] = useState<string | null>(null);
  const [selectedProduct, setSelectedProduct] = useState("it_infrastructure");
  const [selectedTemplate, setSelectedTemplate] = useState("custom");
  const [customContext, setCustomContext] = useState("");
  const [inputMode, setInputMode] = useState<"list" | "add" | "csv">("list");
  const [previewIndex, setPreviewIndex] = useState<number | null>(null);
  const [conversationStage, setConversationStage] = useState("not_contacted");
  const [filterHasEmail, setFilterHasEmail] = useState<"any" | "yes" | "no">("any");
  const [filterQuery, setFilterQuery] = useState("");
  const [replyMode, setReplyMode] = useState(false);
  const [threadSummary, setThreadSummary] = useState("");
  const [optOutNote, setOptOutNote] = useState("");
  const [validateBeforeSend, setValidateBeforeSend] = useState(false);
  const toast = useToast();

  const nameRef = useRef<HTMLInputElement>(null);
  const emailRef = useRef<HTMLInputElement>(null);
  const companyRef = useRef<HTMLInputElement>(null);
  const titleRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [p, prod, tmpl, gmail] = await Promise.all([
        getSavedProspects(),
        getProducts(),
        getEmailTemplates(),
        getGmailStatus(),
      ]);
      setProspects(p);
      setProducts(prod);
      setTemplates(tmpl);
      setGmailConnected(gmail.connected);
      setGmailEmail(gmail.email || null);
      toast({ title: "Data loaded", variant: "success" });
    } finally {
      setLoading(false);
    }
  };

  const handleAddProspect = async () => {
    const name = nameRef.current?.value?.trim();
    const email = emailRef.current?.value?.trim();
    if (!name || !email) return setError("Name and email are required");
    try {
      const saved = await saveProspect({
        name,
        email,
        company: companyRef.current?.value?.trim(),
        title: titleRef.current?.value?.trim(),
        source: "manual",
      });
      setProspects([saved, ...prospects]);
      setInputMode("list");
      toast({ title: "Prospect added", variant: "success" });
    } catch (e: any) {
      setError(e.message);
      toast({ title: "Add failed", description: e.message, variant: "error" });
    }
  };

  const handleGenerate = async () => {
    const selected = prospects.filter(p => selectedIds.has(p.id) && p.email);
    if (!selected.length) return setError("Select prospects with email addresses");
    setGenerating(true);
    setError(null);
    const newDrafts: typeof drafts = [];

    for (const prospect of selected) {
      try {
        const output = await generateEmail({
          prospect_record: { id: prospect.id, name: prospect.name, email: prospect.email, title: prospect.title },
          company_context: { name: prospect.company || "Unknown", industry: prospect.industry },
          conversation_stage: conversationStage,
          product_key: selectedProduct,
          template_key: selectedTemplate,
          custom_message: customContext || undefined,
          last_email_thread_summary: replyMode && threadSummary ? threadSummary : undefined,
          opt_out_note: optOutNote || undefined,
          validate_before_send: validateBeforeSend,
        });
        newDrafts.push({
          prospect,
          draft: { to: prospect.email || "", subject: output.subject_line, body_text: output.body_text, body_html: output.body_html },
          copied: false,
        });
      } catch (e: any) {
        newDrafts.push({
          prospect,
          draft: { to: prospect.email || "", subject: "Error", body_text: e.message },
          copied: false,
        });
      }
    }

    setDrafts(newDrafts);
    setGenerating(false);
    toast({ title: "Generated", description: `${newDrafts.length} emails`, variant: "success" });
  };

  const handleSendToGmail = async () => {
    if (!gmailConnected) return setError("Connect Gmail first");
    setLoading(true);
    try {
      const result = await createGmailDrafts(drafts.map(d => d.draft).filter(d => d.to));
      toast({ title: "Gmail drafts created", description: `${result.created} drafts`, variant: "success" });
    } catch (e: any) {
      setError(e.message);
      toast({ title: "Gmail error", description: e.message, variant: "error" });
    } finally {
      setLoading(false);
    }
  };

  const copyDraft = (idx: number) => {
    const d = drafts[idx].draft;
    navigator.clipboard.writeText(`Subject: ${d.subject}\n\n${d.body_text}`);
    const u = [...drafts];
    u[idx].copied = true;
    setDrafts(u);
  };

  const copySubject = (idx: number) => {
    const d = drafts[idx].draft;
    navigator.clipboard.writeText(d.subject || "");
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
          <h1 className="text-3xl font-bold bg-gradient-to-r from-emerald-400 to-teal-400 bg-clip-text text-transparent">
            Email Campaign Agent
          </h1>
          <p className="text-zinc-400 mt-1">Generate and send professional B2B emails</p>
        </div>
        {/* Gmail Status */}
        {gmailConnected ? (
          <div className="flex items-center gap-3 px-4 py-2 bg-emerald-500/10 rounded-xl border border-emerald-500/20">
            <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse"></span>
            <span className="text-sm font-medium text-emerald-400">{gmailEmail}</span>
            <button onClick={() => disconnectGmail().then(() => { setGmailConnected(false); setGmailEmail(null); })} className="text-xs text-red-400 hover:text-red-300">
              Disconnect
            </button>
          </div>
        ) : (
          <button
            onClick={async () => { const { auth_url } = await getGmailAuthUrl(); window.location.href = auth_url; }}
            className="px-4 py-2 bg-gradient-to-r from-emerald-500 to-teal-500 text-white text-sm rounded-xl font-medium shadow-lg shadow-emerald-500/25 hover:shadow-emerald-500/40 transition"
          >
            🔗 Connect Gmail
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
                <span className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center text-sm">👥</span>
                Prospects ({prospects.length})
              </h3>
              <div className="flex gap-1">
                {["list", "add", "csv"].map(m => (
                  <button
                    key={m}
                    onClick={() => setInputMode(m as any)}
                    className={`px-3 py-1.5 text-xs rounded-lg transition ${inputMode === m ? "bg-gradient-to-r from-emerald-500 to-teal-500 text-white" : "bg-zinc-800 text-zinc-400 hover:text-white"}`}
                  >
                    {m === "list" ? "📋" : m === "add" ? "➕" : "📄"}
                  </button>
                ))}
              </div>
            </div>

            {inputMode === "list" && prospects.length > 0 && (
              <>
                <div className="flex flex-wrap items-center gap-3 text-xs text-zinc-500 mb-3">
                  <span>{selectedIds.size} selected</span>
                  <button onClick={() => setSelectedIds(new Set(prospects.filter(p => p.email).map(p => p.id)))} className="text-emerald-400 hover:text-emerald-300">All with email</button>
                  <input
                    value={filterQuery}
                    onChange={(e) => setFilterQuery(e.target.value)}
                    placeholder="Filter by name, company, title"
                    className="ml-auto rounded-lg bg-zinc-800 border border-zinc-700 px-2 py-1 text-[11px] text-white placeholder-zinc-500 focus:border-emerald-500 focus:outline-none"
                  />
                  <select
                    value={filterHasEmail}
                    onChange={(e) => setFilterHasEmail(e.target.value as any)}
                    className="rounded bg-zinc-800 border border-zinc-700 px-2 py-1 text-[11px] text-white focus:border-emerald-500 focus:outline-none"
                  >
                    <option value="any">Any email</option>
                    <option value="yes">Has email</option>
                    <option value="no">No email</option>
                  </select>
                </div>
                <div className="border border-zinc-800 rounded-xl max-h-40 overflow-y-auto">
                  {prospects
                    .filter(p => {
                      const q = filterQuery.toLowerCase();
                      const matches = !q || [p.name, p.company, p.title, p.email].some(x => x?.toLowerCase().includes(q));
                      const has = !!p.email;
                      const ok = filterHasEmail === "any" ? true : filterHasEmail === "yes" ? has : !has;
                      return matches && ok;
                    })
                    .map(p => (
                    <div
                      key={p.id}
                      onClick={() => p.email && toggleSelect(p.id)}
                      className={`flex items-center gap-3 p-3 border-b border-zinc-800 last:border-0 cursor-pointer hover:bg-zinc-800/50 transition ${selectedIds.has(p.id) ? "bg-emerald-500/10" : ""} ${!p.email ? "opacity-50" : ""}`}
                    >
                      <input type="checkbox" checked={selectedIds.has(p.id)} disabled={!p.email} readOnly className="rounded bg-zinc-700 border-zinc-600 text-emerald-500" />
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-white text-sm truncate">{p.name}</div>
                        <div className="text-xs text-zinc-500 truncate">{p.email || "⚠️ No email"}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}

            {inputMode === "add" && (
              <div className="space-y-4">
                <div className="grid gap-4 grid-cols-2">
                  <div>
                    <label className="text-xs text-zinc-400 block mb-1">Name *</label>
                    <input ref={nameRef} className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-white text-sm focus:border-emerald-500 focus:outline-none" />
                  </div>
                  <div>
                    <label className="text-xs text-zinc-400 block mb-1">Email *</label>
                    <input ref={emailRef} type="email" className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-white text-sm focus:border-emerald-500 focus:outline-none" />
                  </div>
                  <div>
                    <label className="text-xs text-zinc-400 block mb-1">Company</label>
                    <input ref={companyRef} className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-white text-sm focus:border-emerald-500 focus:outline-none" />
                  </div>
                  <div>
                    <label className="text-xs text-zinc-400 block mb-1">Title</label>
                    <input ref={titleRef} className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-white text-sm focus:border-emerald-500 focus:outline-none" />
                  </div>
                </div>
                <div className="flex gap-2">
                  <button onClick={handleAddProspect} className="px-4 py-2 bg-gradient-to-r from-emerald-500 to-teal-500 text-white text-sm rounded-lg font-medium">Save</button>
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
                        setSuccess(`Imported ${r.prospects.length}`);
                        setInputMode("list");
                      }
                    } catch (err: any) {
                      setError(err.message);
                    }
                  }}
                  className="text-sm text-zinc-400"
                />
                <p className="text-xs text-zinc-500">CSV must include: name, email columns</p>
              </div>
            )}
          </div>

          {/* Settings Card */}
          <div className="rounded-2xl bg-gradient-to-br from-zinc-900 to-zinc-900/50 border border-zinc-800 p-6">
            <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
              <span className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center text-sm">⚙️</span>
              Email Settings
            </h3>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="text-xs text-zinc-400 block mb-1">Product</label>
                <select value={selectedProduct} onChange={e => setSelectedProduct(e.target.value)} className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2.5 text-white text-sm focus:border-emerald-500 focus:outline-none">
                  {products.map(p => <option key={p.key} value={p.key}>{p.name}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-zinc-400 block mb-1">Template</label>
                <select value={selectedTemplate} onChange={e => setSelectedTemplate(e.target.value)} className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2.5 text-white text-sm focus:border-emerald-500 focus:outline-none">
                  {templates.map(t => <option key={t.key} value={t.key}>{t.name}</option>)}
                </select>
              </div>
            </div>
            <div className="mt-2">
              <label className="text-xs text-zinc-400 block mb-1">Conversation Stage</label>
              <select value={conversationStage} onChange={e => setConversationStage(e.target.value)} className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2.5 text-white text-sm focus:border-emerald-500 focus:outline-none">
                <option value="not_contacted">Not contacted</option>
                <option value="follow_up">Follow-up</option>
                <option value="reengage">Re-engage</option>
              </select>
            </div>
            <div className="mt-2 flex items-center gap-3">
              <label className="flex items-center gap-2 text-sm text-zinc-400">
                <input
                  type="checkbox"
                  checked={replyMode}
                  onChange={(e) => setReplyMode(e.target.checked)}
                  className="rounded border-zinc-600"
                />
                Reply mode (use last thread summary)
              </label>
            </div>
            {replyMode && (
              <div className="mt-2">
                <label className="text-xs text-zinc-400 block mb-1">Last thread summary / customer reply</label>
                <textarea
                  value={threadSummary}
                  onChange={e => setThreadSummary(e.target.value)}
                  rows={3}
                  className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2.5 text-white text-sm focus:border-emerald-500 focus:outline-none resize-none"
                  placeholder="Paste the customer's reply or summarize the latest thread..."
                />
              </div>
            )}
            <div className="mt-2 grid md:grid-cols-2 gap-3">
              <label className="flex items-center gap-2 text-sm text-zinc-400">
                <input
                  type="checkbox"
                  checked={validateBeforeSend}
                  onChange={(e) => setValidateBeforeSend(e.target.checked)}
                  className="rounded border-zinc-600"
                />
                Validate before send (deliverability check)
              </label>
              <div>
                <label className="text-xs text-zinc-400 block mb-1">Opt-out / Unsubscribe note</label>
                <textarea
                  value={optOutNote}
                  onChange={(e) => setOptOutNote(e.target.value)}
                  rows={2}
                  className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2.5 text-white text-sm focus:border-emerald-500 focus:outline-none resize-none"
                  placeholder={'e.g., "If you prefer not to hear from me, let me know and I\'ll stop."'}
                />
              </div>
            </div>
            <div className="mt-4">
              <label className="text-xs text-zinc-400 block mb-1">Custom Context</label>
              <textarea value={customContext} onChange={e => setCustomContext(e.target.value)} rows={2} className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2.5 text-white text-sm focus:border-emerald-500 focus:outline-none resize-none" placeholder="Specific talking points..." />
            </div>
            <button
              onClick={handleGenerate}
              disabled={generating || selectedIds.size === 0}
              className="mt-4 w-full rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 px-6 py-3 font-medium text-white shadow-lg shadow-emerald-500/25 hover:shadow-emerald-500/40 transition disabled:opacity-50"
            >
              {generating ? "✨ Generating..." : `✨ Generate ${selectedIds.size} Emails`}
            </button>
          </div>
        </div>

        {/* Right - Generated Emails */}
        <div className="rounded-2xl bg-gradient-to-br from-zinc-900 to-zinc-900/50 border border-zinc-800 overflow-hidden">
          <div className="p-4 border-b border-zinc-800 bg-gradient-to-r from-emerald-500/10 to-teal-500/10 flex justify-between items-center">
            <h3 className="font-semibold text-white">📧 Generated Emails ({drafts.length})</h3>
            {drafts.length > 0 && gmailConnected && (
              <button onClick={handleSendToGmail} disabled={loading} className="px-4 py-1.5 bg-gradient-to-r from-emerald-500 to-teal-500 text-white text-xs rounded-lg font-medium shadow-lg disabled:opacity-50">
                {loading ? "Sending..." : "📤 Send to Gmail"}
              </button>
            )}
          </div>
          <div className="p-4 max-h-[600px] overflow-y-auto">
            {drafts.length === 0 ? (
              <div className="text-center py-16 text-zinc-500">
                <div className="text-5xl mb-4">📧</div>
                <p className="font-medium">No emails yet</p>
                <p className="text-sm">Select prospects and click generate</p>
              </div>
            ) : (
              <div className="space-y-3">
                {drafts.map((item, i) => (
                  <div key={i} className="rounded-xl border border-zinc-800 overflow-hidden hover:border-emerald-500/30 transition">
                    <div className="p-3 bg-zinc-800/50 flex justify-between items-center">
                      <div>
                        <span className="font-medium text-white text-sm">{item.prospect.name}</span>
                        <span className="text-xs text-zinc-500 ml-2">&lt;{item.draft.to}&gt;</span>
                      </div>
                      <div className="flex gap-2">
                        <button onClick={() => setPreviewIndex(previewIndex === i ? null : i)} className="px-2 py-1 text-xs bg-zinc-700 rounded hover:bg-zinc-600 transition">
                          {previewIndex === i ? "Close" : "Preview"}
                        </button>
                        <button onClick={() => copySubject(i)} className="px-2 py-1 text-xs rounded bg-zinc-700 hover:bg-zinc-600 transition">
                          Copy Subject
                        </button>
                        <button onClick={() => copyDraft(i)} className={`px-2 py-1 text-xs rounded transition ${item.copied ? "bg-emerald-500/20 text-emerald-400" : "bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20"}`}>
                          {item.copied ? "✓" : "📋"}
                        </button>
                      </div>
                    </div>
                    <div className="p-3">
                      <div className="text-sm font-medium text-white">{item.draft.subject}</div>
                      <div className="text-xs text-zinc-500 mt-1 flex gap-4">
                        <span>Subject: {item.draft.subject?.length ?? 0} chars {item.draft.subject && item.draft.subject.length > 72 ? " • ⚠️ long subject" : ""}</span>
                        <span>Body: {item.draft.body_text?.length ?? 0} chars {item.draft.body_text && item.draft.body_text.length > 1200 ? " • ⚠️ long body" : ""}</span>
                      </div>
                      {previewIndex === i ? (
                        <div className="mt-2 text-sm text-zinc-400 whitespace-pre-wrap bg-zinc-800/50 p-3 rounded-lg border border-zinc-700">{item.draft.body_text}</div>
                      ) : (
                        <p className="text-xs text-zinc-500 mt-1 line-clamp-2">{item.draft.body_text}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

