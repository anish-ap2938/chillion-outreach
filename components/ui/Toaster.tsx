"use client";

import React, { createContext, useCallback, useContext, useMemo, useState } from "react";
import clsx from "clsx";

type ToastVariant = "default" | "success" | "error" | "warning" | "info";

type Toast = {
  id: string;
  title?: string;
  description?: string;
  variant?: ToastVariant;
  duration?: number;
};

type ToastContextValue = {
  toast: (t: Omit<Toast, "id">) => void;
  dismiss: (id: string) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children?: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback(
    (t: Omit<Toast, "id">) => {
      const id = crypto.randomUUID();
      const next: Toast = {
        id,
        variant: "default",
        duration: 4000,
        ...t,
      };
      setToasts((prev) => [...prev, next]);
      if (next.duration && next.duration > 0) {
        setTimeout(() => dismiss(id), next.duration);
      }
    },
    [dismiss],
  );

  const value = useMemo(() => ({ toast, dismiss }), [toast, dismiss]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
        {toasts.map((t) => (
          <ToastCard key={t.id} toast={t} onClose={() => dismiss(t.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export default function Toaster() {
  return <ToastProvider />;
}

function ToastCard({ toast, onClose }: { toast: Toast; onClose: () => void }) {
  const variantMap: Record<ToastVariant, string> = {
    default: "bg-zinc-900 border-zinc-800 text-zinc-100",
    success: "bg-emerald-900/90 border-emerald-800 text-emerald-100",
    error: "bg-red-900/90 border-red-800 text-red-100",
    warning: "bg-amber-900/90 border-amber-800 text-amber-50",
    info: "bg-blue-900/90 border-blue-800 text-blue-100",
  };

  return (
    <div
      className={clsx(
        "min-w-[260px] max-w-sm rounded-lg border px-4 py-3 shadow-lg shadow-black/40 backdrop-blur",
        variantMap[toast.variant || "default"],
      )}
    >
      <div className="flex justify-between gap-3">
        <div className="space-y-1">
          {toast.title && <div className="font-semibold text-sm">{toast.title}</div>}
          {toast.description && <div className="text-xs text-zinc-300">{toast.description}</div>}
        </div>
        <button onClick={onClose} className="text-xs text-zinc-400 hover:text-zinc-200">
          ✕
        </button>
      </div>
    </div>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx.toast;
}

