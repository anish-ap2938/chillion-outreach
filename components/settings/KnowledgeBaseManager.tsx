"use client";

import { useState, useEffect, useRef } from "react";

const AGENTS_API_URL = process.env.NEXT_PUBLIC_AGENTS_API_URL || "http://localhost:8000";

interface KnowledgeDoc {
  id: string;
  filename: string;
  file_type: string;
  uploaded_at: string;
  chunks_count: number;
  status: "processing" | "ready" | "error";
}

export default function KnowledgeBaseManager() {
  const [documents, setDocuments] = useState<KnowledgeDoc[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [stats, setStats] = useState<{ total_docs: number; total_chunks: number } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadDocuments();
    loadStats();
  }, []);

  const loadDocuments = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${AGENTS_API_URL}/api/v1/knowledge/documents`);
      if (response.ok) {
        const data = await response.json();
        setDocuments(data);
      }
    } catch (e) {
      console.error("Failed to load documents:", e);
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const response = await fetch(`${AGENTS_API_URL}/api/v1/knowledge/stats`);
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (e) {
      console.error("Failed to load stats:", e);
    }
  };

  const handleUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    
    setUploading(true);
    setError(null);
    
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append("files", files[i]);
    }
    
    try {
      const response = await fetch(`${AGENTS_API_URL}/api/v1/knowledge/upload`, {
        method: "POST",
        body: formData,
      });
      
      if (response.ok) {
        const result = await response.json();
        setSuccess(`Uploaded ${result.uploaded_count} files!`);
        setTimeout(() => setSuccess(null), 3000);
        await loadDocuments();
        await loadStats();
      } else {
        const err = await response.json();
        setError(err.detail || "Upload failed");
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleDelete = async (docId: string) => {
    if (!confirm("Are you sure you want to delete this document?")) return;
    
    try {
      const response = await fetch(`${AGENTS_API_URL}/api/v1/knowledge/documents/${docId}`, {
        method: "DELETE",
      });
      
      if (response.ok) {
        setSuccess("Document deleted");
        setTimeout(() => setSuccess(null), 2000);
        await loadDocuments();
        await loadStats();
      }
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleReindex = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${AGENTS_API_URL}/api/v1/knowledge/reindex`, {
        method: "POST",
      });
      
      if (response.ok) {
        setSuccess("Knowledge base reindexed!");
        setTimeout(() => setSuccess(null), 3000);
        await loadStats();
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-fuchsia-400 to-purple-400 bg-clip-text text-transparent">
            Knowledge Base
          </h1>
          <p className="text-zinc-400 mt-1">Upload PDFs to enhance AI with Chillion product knowledge</p>
        </div>
        <button
          onClick={handleReindex}
          disabled={loading}
          className="px-4 py-2 bg-zinc-800 border border-zinc-700 rounded-xl text-sm hover:bg-zinc-700 transition disabled:opacity-50"
        >
          🔄 Reindex All
        </button>
      </div>

      {/* Alerts */}
      {error && <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400">{error}<button onClick={() => setError(null)} className="float-right">✕</button></div>}
      {success && <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-emerald-400">✓ {success}</div>}

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 gap-4">
          <div className="rounded-2xl bg-gradient-to-br from-fuchsia-500/10 to-purple-500/10 border border-fuchsia-500/20 p-6">
            <div className="text-4xl font-bold text-fuchsia-400">{stats.total_docs}</div>
            <div className="text-sm text-zinc-400 mt-1">Documents</div>
          </div>
          <div className="rounded-2xl bg-gradient-to-br from-purple-500/10 to-violet-500/10 border border-purple-500/20 p-6">
            <div className="text-4xl font-bold text-purple-400">{stats.total_chunks}</div>
            <div className="text-sm text-zinc-400 mt-1">Knowledge Chunks</div>
          </div>
        </div>
      )}

      {/* Upload Area */}
      <div
        className="rounded-2xl border-2 border-dashed border-fuchsia-500/30 bg-fuchsia-500/5 p-12 text-center hover:border-fuchsia-500/50 transition cursor-pointer"
        onClick={() => fileInputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); }}
        onDrop={(e) => { e.preventDefault(); e.stopPropagation(); handleUpload(e.dataTransfer.files); }}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.txt,.md,.doc,.docx"
          multiple
          className="hidden"
          onChange={(e) => handleUpload(e.target.files)}
        />
        {uploading ? (
          <div className="space-y-2">
            <div className="text-5xl animate-pulse">⏳</div>
            <div className="text-lg font-medium text-fuchsia-400">Uploading & Processing...</div>
          </div>
        ) : (
          <div className="space-y-2">
            <div className="text-5xl">📄</div>
            <div className="text-lg font-medium text-white">Drop files here or click to upload</div>
            <div className="text-sm text-zinc-500">Supports PDF, TXT, MD, DOC, DOCX</div>
          </div>
        )}
      </div>

      {/* Documents List */}
      <div className="rounded-2xl bg-gradient-to-br from-zinc-900 to-zinc-900/50 border border-zinc-800 overflow-hidden">
        <div className="p-4 border-b border-zinc-800 bg-gradient-to-r from-fuchsia-500/10 to-purple-500/10">
          <h3 className="font-semibold text-white">📚 Indexed Documents ({documents.length})</h3>
        </div>
        
        {documents.length === 0 ? (
          <div className="p-16 text-center text-zinc-500">
            <div className="text-5xl mb-4">📭</div>
            <p className="font-medium">No documents yet</p>
            <p className="text-sm mt-1">Upload PDF files to build your knowledge base</p>
          </div>
        ) : (
          <div className="divide-y divide-zinc-800 max-h-[400px] overflow-y-auto">
            {documents.map((doc) => (
              <div key={doc.id} className="p-4 hover:bg-zinc-800/50 transition">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-fuchsia-500/20 to-purple-500/20 flex items-center justify-center text-lg border border-fuchsia-500/20">
                      {doc.file_type === "pdf" ? "📕" : doc.file_type === "txt" ? "📝" : "📄"}
                    </div>
                    <div>
                      <div className="font-medium text-white">{doc.filename}</div>
                      <div className="text-xs text-zinc-500">
                        {doc.chunks_count} chunks • {formatDate(doc.uploaded_at)}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                      doc.status === "ready" ? "bg-emerald-500/20 text-emerald-400" :
                      doc.status === "processing" ? "bg-amber-500/20 text-amber-400" :
                      "bg-red-500/20 text-red-400"
                    }`}>
                      {doc.status}
                    </span>
                    <button
                      onClick={() => handleDelete(doc.id)}
                      className="text-red-400 hover:text-red-300 p-1"
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Info */}
      <div className="rounded-xl bg-zinc-900/50 border border-zinc-800 p-4">
        <h4 className="font-medium text-fuchsia-400 mb-2">💡 How it works</h4>
        <ul className="text-sm text-zinc-400 space-y-1">
          <li>• Uploaded documents are processed and split into chunks</li>
          <li>• Each chunk is converted to vector embeddings for semantic search</li>
          <li>• When generating messages, relevant chunks are retrieved to provide context</li>
          <li>• Upload product docs, case studies, blog posts to improve AI responses</li>
        </ul>
      </div>
    </div>
  );
}

