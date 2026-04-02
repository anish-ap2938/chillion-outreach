"use client";

import { useState, useEffect } from "react";
import { getEmailTemplates, getLinkedInTemplates, type Template } from "@/lib/api/agents";

const AGENTS_API_URL = process.env.NEXT_PUBLIC_AGENTS_API_URL || "http://localhost:8000";

interface FullTemplate {
  key: string;
  name: string;
  type: "email" | "linkedin";
  subject?: string;
  body?: string;
  message?: string;
}

export default function TemplatesManager() {
  const [templates, setTemplates] = useState<FullTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [editingTemplate, setEditingTemplate] = useState<FullTemplate | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newTemplate, setNewTemplate] = useState<Partial<FullTemplate>>({ type: "email", name: "", key: "" });

  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    setLoading(true);
    try {
      const [emailTmpl, linkedinTmpl] = await Promise.all([
        getEmailTemplates(),
        getLinkedInTemplates(),
      ]);
      
      // Fetch full template content
      const fullEmailTemplates = await fetch(`${AGENTS_API_URL}/api/v1/settings/email-templates`).then(r => r.json()).catch(() => []);
      const fullLinkedinTemplates = await fetch(`${AGENTS_API_URL}/api/v1/settings/linkedin-templates`).then(r => r.json()).catch(() => []);
      
      setTemplates([
        ...fullEmailTemplates.map((t: any) => ({ ...t, type: "email" as const })),
        ...fullLinkedinTemplates.map((t: any) => ({ ...t, type: "linkedin" as const })),
      ]);
    } catch (e) {
      console.error(e);
      // Fallback to basic templates
      setTemplates([
        { key: "ar_visibility", name: "AR Visibility - Version 1", type: "email", subject: "Enterprise AR teams still lack real-time receivables visibility" },
        { key: "multi_erp_risk", name: "Multi-ERP Risk View - Version 2", type: "email", subject: "Single view of risk across your ERPs" },
        { key: "custom", name: "AI-Generated Custom", type: "email" },
        { key: "connection_request", name: "Connection Request", type: "linkedin" },
        { key: "ar_pain_point", name: "AR Pain Point", type: "linkedin" },
        { key: "dso_reduction", name: "DSO Reduction", type: "linkedin" },
        { key: "follow_up", name: "Follow-Up", type: "linkedin" },
        { key: "custom", name: "AI-Generated Custom", type: "linkedin" },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveTemplate = async (template: FullTemplate) => {
    try {
      const endpoint = template.type === "email" 
        ? `${AGENTS_API_URL}/api/v1/settings/email-templates/${template.key}`
        : `${AGENTS_API_URL}/api/v1/settings/linkedin-templates/${template.key}`;
      
      await fetch(endpoint, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(template),
      });
      
      setSuccess("Template saved!");
      setTimeout(() => setSuccess(null), 2000);
      setEditingTemplate(null);
      await loadTemplates();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleAddTemplate = async () => {
    if (!newTemplate.name || !newTemplate.key) {
      setError("Name and key are required");
      return;
    }
    
    try {
      const endpoint = newTemplate.type === "email"
        ? `${AGENTS_API_URL}/api/v1/settings/email-templates`
        : `${AGENTS_API_URL}/api/v1/settings/linkedin-templates`;
      
      await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newTemplate),
      });
      
      setSuccess("Template added!");
      setTimeout(() => setSuccess(null), 2000);
      setShowAddModal(false);
      setNewTemplate({ type: "email", name: "", key: "" });
      await loadTemplates();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const emailTemplates = templates.filter(t => t.type === "email");
  const linkedinTemplates = templates.filter(t => t.type === "linkedin");

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-amber-400 to-orange-400 bg-clip-text text-transparent">
            Message Templates
          </h1>
          <p className="text-zinc-400 mt-1">Manage email and LinkedIn message templates</p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="px-4 py-2 bg-gradient-to-r from-amber-500 to-orange-500 text-white text-sm rounded-xl font-medium shadow-lg shadow-amber-500/25 hover:shadow-amber-500/40 transition"
        >
          ➕ Add Template
        </button>
      </div>

      {/* Alerts */}
      {error && <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400">{error}<button onClick={() => setError(null)} className="float-right">✕</button></div>}
      {success && <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-emerald-400">✓ {success}</div>}

      {/* Email Templates */}
      <div className="rounded-2xl bg-gradient-to-br from-zinc-900 to-zinc-900/50 border border-zinc-800 p-6">
        <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
          <span className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center text-sm">✉️</span>
          Email Templates ({emailTemplates.length})
        </h3>
        <div className="space-y-3">
          {emailTemplates.map((template) => (
            <div key={`email-${template.key}`} className="p-4 rounded-xl bg-zinc-800/50 border border-zinc-700 hover:border-amber-500/30 transition">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium text-white">{template.name}</div>
                  {template.subject && <div className="text-sm text-zinc-400 mt-1">Subject: {template.subject}</div>}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setEditingTemplate(template)}
                    className="px-3 py-1.5 text-xs bg-zinc-700 rounded-lg hover:bg-zinc-600 transition"
                  >
                    ✏️ Edit
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* LinkedIn Templates */}
      <div className="rounded-2xl bg-gradient-to-br from-zinc-900 to-zinc-900/50 border border-zinc-800 p-6">
        <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
          <span className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-500 flex items-center justify-center text-sm">💼</span>
          LinkedIn Templates ({linkedinTemplates.length})
        </h3>
        <div className="space-y-3">
          {linkedinTemplates.map((template) => (
            <div key={`linkedin-${template.key}`} className="p-4 rounded-xl bg-zinc-800/50 border border-zinc-700 hover:border-amber-500/30 transition">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium text-white">{template.name}</div>
                  {template.message && <div className="text-sm text-zinc-400 mt-1 line-clamp-1">{template.message}</div>}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setEditingTemplate(template)}
                    className="px-3 py-1.5 text-xs bg-zinc-700 rounded-lg hover:bg-zinc-600 transition"
                  >
                    ✏️ Edit
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Edit Modal */}
      {editingTemplate && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
          <div className="bg-zinc-900 rounded-2xl border border-zinc-800 p-6 max-w-2xl w-full max-h-[80vh] overflow-y-auto">
            <h3 className="text-xl font-bold text-white mb-4">Edit Template</h3>
            <div className="space-y-4">
              <div>
                <label className="text-sm text-zinc-400 block mb-1">Name</label>
                <input
                  value={editingTemplate.name}
                  onChange={e => setEditingTemplate({ ...editingTemplate, name: e.target.value })}
                  className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-white focus:border-amber-500 focus:outline-none"
                />
              </div>
              {editingTemplate.type === "email" && (
                <>
                  <div>
                    <label className="text-sm text-zinc-400 block mb-1">Subject Line</label>
                    <input
                      value={editingTemplate.subject || ""}
                      onChange={e => setEditingTemplate({ ...editingTemplate, subject: e.target.value })}
                      className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-white focus:border-amber-500 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-sm text-zinc-400 block mb-1">Body</label>
                    <textarea
                      value={editingTemplate.body || ""}
                      onChange={e => setEditingTemplate({ ...editingTemplate, body: e.target.value })}
                      rows={10}
                      className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-white focus:border-amber-500 focus:outline-none resize-none font-mono text-sm"
                      placeholder="Use {first_name}, {company_name}, etc. for placeholders"
                    />
                  </div>
                </>
              )}
              {editingTemplate.type === "linkedin" && (
                <div>
                  <label className="text-sm text-zinc-400 block mb-1">Message</label>
                  <textarea
                    value={editingTemplate.message || ""}
                    onChange={e => setEditingTemplate({ ...editingTemplate, message: e.target.value })}
                    rows={6}
                    className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-white focus:border-amber-500 focus:outline-none resize-none"
                    placeholder="Use {first_name}, {company_name}, etc. for placeholders"
                  />
                </div>
              )}
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button onClick={() => setEditingTemplate(null)} className="px-4 py-2 bg-zinc-800 rounded-lg text-sm">Cancel</button>
              <button onClick={() => handleSaveTemplate(editingTemplate)} className="px-4 py-2 bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-lg text-sm font-medium">Save Template</button>
            </div>
          </div>
        </div>
      )}

      {/* Add Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
          <div className="bg-zinc-900 rounded-2xl border border-zinc-800 p-6 max-w-2xl w-full">
            <h3 className="text-xl font-bold text-white mb-4">Add New Template</h3>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm text-zinc-400 block mb-1">Type</label>
                  <select
                    value={newTemplate.type}
                    onChange={e => setNewTemplate({ ...newTemplate, type: e.target.value as "email" | "linkedin" })}
                    className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-white focus:border-amber-500 focus:outline-none"
                  >
                    <option value="email">Email</option>
                    <option value="linkedin">LinkedIn</option>
                  </select>
                </div>
                <div>
                  <label className="text-sm text-zinc-400 block mb-1">Key (unique identifier)</label>
                  <input
                    value={newTemplate.key}
                    onChange={e => setNewTemplate({ ...newTemplate, key: e.target.value.toLowerCase().replace(/\s+/g, "_") })}
                    className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-white focus:border-amber-500 focus:outline-none"
                    placeholder="my_template"
                  />
                </div>
              </div>
              <div>
                <label className="text-sm text-zinc-400 block mb-1">Name</label>
                <input
                  value={newTemplate.name}
                  onChange={e => setNewTemplate({ ...newTemplate, name: e.target.value })}
                  className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-white focus:border-amber-500 focus:outline-none"
                  placeholder="My Custom Template"
                />
              </div>
              {newTemplate.type === "email" && (
                <>
                  <div>
                    <label className="text-sm text-zinc-400 block mb-1">Subject Line</label>
                    <input
                      value={newTemplate.subject || ""}
                      onChange={e => setNewTemplate({ ...newTemplate, subject: e.target.value })}
                      className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-white focus:border-amber-500 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-sm text-zinc-400 block mb-1">Body</label>
                    <textarea
                      value={newTemplate.body || ""}
                      onChange={e => setNewTemplate({ ...newTemplate, body: e.target.value })}
                      rows={6}
                      className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-white focus:border-amber-500 focus:outline-none resize-none"
                    />
                  </div>
                </>
              )}
              {newTemplate.type === "linkedin" && (
                <div>
                  <label className="text-sm text-zinc-400 block mb-1">Message</label>
                  <textarea
                    value={newTemplate.message || ""}
                    onChange={e => setNewTemplate({ ...newTemplate, message: e.target.value })}
                    rows={4}
                    className="w-full rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-white focus:border-amber-500 focus:outline-none resize-none"
                  />
                </div>
              )}
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button onClick={() => setShowAddModal(false)} className="px-4 py-2 bg-zinc-800 rounded-lg text-sm">Cancel</button>
              <button onClick={handleAddTemplate} className="px-4 py-2 bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-lg text-sm font-medium">Add Template</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

