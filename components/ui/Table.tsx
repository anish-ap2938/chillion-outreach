"use client";

import clsx from "clsx";
import React from "react";

type Density = "comfortable" | "compact";

type TableProps = React.HTMLAttributes<HTMLTableElement> & {
  density?: Density;
};

const densityMap: Record<Density, string> = {
  comfortable: "text-sm",
  compact: "text-xs",
};

export function Table({ className, density = "comfortable", ...props }: TableProps) {
  return (
    <div className="overflow-hidden rounded-xl border border-zinc-800 bg-zinc-950">
      <div className="overflow-x-auto">
        <table
          className={clsx(
            "w-full border-collapse whitespace-nowrap",
            densityMap[density],
            className,
          )}
          {...props}
        />
      </div>
    </div>
  );
}

export function TableHead({ className, ...props }: React.HTMLAttributes<HTMLTableSectionElement>) {
  return <thead className={clsx("bg-zinc-900/60 text-zinc-400", className)} {...props} />;
}

export function TableBody({ className, ...props }: React.HTMLAttributes<HTMLTableSectionElement>) {
  return <tbody className={clsx("divide-y divide-zinc-800", className)} {...props} />;
}

export function TableRow({ className, ...props }: React.HTMLAttributes<HTMLTableRowElement>) {
  return <tr className={clsx("hover:bg-zinc-900/60 transition", className)} {...props} />;
}

export function TableHeaderCell({ className, ...props }: React.ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      className={clsx("px-4 py-3 text-left font-semibold uppercase tracking-wide text-[11px]", className)}
      {...props}
    />
  );
}

export function TableCell({ className, ...props }: React.TdHTMLAttributes<HTMLTableCellElement>) {
  return <td className={clsx("px-4 py-3 align-middle text-zinc-200", className)} {...props} />;
}

