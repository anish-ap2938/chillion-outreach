"use client";

import clsx from "clsx";
import React from "react";

type BadgeProps = {
  children: React.ReactNode;
  variant?: "neutral" | "info" | "success" | "warning" | "danger";
  className?: string;
};

const variants: Record<NonNullable<BadgeProps["variant"]>, string> = {
  neutral: "bg-zinc-800/50 text-zinc-200 border border-zinc-700",
  info: "bg-blue-500/10 text-blue-200 border border-blue-500/30",
  success: "bg-emerald-500/10 text-emerald-200 border border-emerald-500/30",
  warning: "bg-amber-500/10 text-amber-100 border border-amber-500/30",
  danger: "bg-red-500/10 text-red-200 border border-red-500/30",
};

export function Badge({ children, variant = "neutral", className }: BadgeProps) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-medium",
        variants[variant],
        className,
      )}
    >
      {children}
    </span>
  );
}

