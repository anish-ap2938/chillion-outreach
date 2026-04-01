import AppShell from "@/components/layout/AppShell";
import { getOptionalSession } from "@/lib/auth/guards";
import Link from "next/link";
import ActivityFeed from "@/components/dashboard/ActivityFeed";
import SystemStatus from "@/components/dashboard/SystemStatus";

export default async function DashboardPage() {
  const session = await getOptionalSession();

  const stats = [
    { label: "GTM Skills", value: "7", icon: "🧩", href: "/skills", gradient: "from-indigo-500 to-violet-600" },
    { label: "Intent Signals", value: "—", icon: "🔍", href: "/intent", gradient: "from-cyan-500 to-blue-600" },
    { label: "Lead Discovery", value: "—", icon: "🎯", href: "/leads", gradient: "from-purple-500 to-pink-600" },
    { label: "LinkedIn Drafts", value: "—", icon: "💼", href: "/linkedin", gradient: "from-blue-500 to-indigo-600" },
    { label: "Email Campaigns", value: "—", icon: "✉️", href: "/email", gradient: "from-emerald-500 to-teal-600" },
    { label: "Meetings", value: "—", icon: "📅", href: "/meetings", gradient: "from-violet-500 to-purple-600" },
  ];

  return (
    <AppShell>
      <div className="space-y-8">
        {/* Hero Header */}
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-lime-600 via-green-600 to-emerald-800 p-8 md:p-12 shadow-2xl shadow-lime-500/20">
          <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZGVmcz48cGF0dGVybiBpZD0iZ3JpZCIgd2lkdGg9IjQwIiBoZWlnaHQ9IjQwIiBwYXR0ZXJuVW5pdHM9InVzZXJTcGFjZU9uVXNlIj48cGF0aCBkPSJNIDQwIDAgTCAwIDAgMCA0MCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLW9wYWNpdHk9IjAuMSIgc3Ryb2tlLXdpZHRoPSIxIi8+PC9wYXR0ZXJuPjwvZGVmcz48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSJ1cmwoI2dyaWQpIi8+PC9zdmc+')] opacity-40"></div>
          <div className="relative z-10">
            <h1 className="text-3xl md:text-4xl font-bold text-white mb-2">
              Welcome to CHILLION Outreach Command Center
            </h1>
            <p className="text-lime-100 text-lg max-w-2xl">
              Where strategy meets technology. Run intent discovery, qualify pipeline, and execute outreach for IT, defense, and enterprise programs.
            </p>
          </div>
          <div className="absolute -right-20 -bottom-20 w-80 h-80 bg-white/10 rounded-full blur-3xl"></div>
          <div className="absolute -left-10 -top-10 w-40 h-40 bg-purple-400/20 rounded-full blur-2xl"></div>
        </div>

        {/* Quick Stats */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {stats.map((stat, index) => (
            <Link
              key={index}
              href={stat.href}
              className="group rounded-2xl bg-gradient-to-br from-zinc-900 to-zinc-900/50 border border-zinc-800 p-6 transition hover:border-zinc-700 hover:shadow-xl hover:shadow-black/20"
            >
              <div className="flex items-center justify-between">
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${stat.gradient} flex items-center justify-center text-2xl shadow-lg group-hover:scale-110 transition`}>
                  {stat.icon}
                </div>
                <span className="text-zinc-500 group-hover:text-zinc-300 transition">→</span>
              </div>
              <div className="mt-4">
                <div className="text-sm font-medium text-zinc-400">{stat.label}</div>
              </div>
            </Link>
          ))}
        </div>

        {/* Quick Actions Grid */}
        <div>
          <h2 className="text-lg font-semibold text-white mb-4">Quick Actions</h2>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
            <Link
              href="/skills"
              className="group relative overflow-hidden rounded-2xl bg-gradient-to-br from-indigo-500/10 to-violet-500/10 border border-indigo-500/20 p-6 transition hover:border-indigo-500/40 hover:shadow-xl hover:shadow-indigo-500/10"
            >
              <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-transparent opacity-0 group-hover:opacity-100 transition"></div>
              <div className="relative z-10">
                <div className="text-4xl mb-4">🧩</div>
                <h3 className="font-semibold text-white mb-1">GTM Skills</h3>
                <p className="text-sm text-zinc-400">Run ICP, scoring, outbound strategy, and meeting prep</p>
              </div>
            </Link>

            <Link
              href="/intent"
              className="group relative overflow-hidden rounded-2xl bg-gradient-to-br from-cyan-500/10 to-blue-500/10 border border-cyan-500/20 p-6 transition hover:border-cyan-500/40 hover:shadow-xl hover:shadow-cyan-500/10"
            >
              <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/5 to-transparent opacity-0 group-hover:opacity-100 transition"></div>
              <div className="relative z-10">
                <div className="text-4xl mb-4">🔍</div>
                <h3 className="font-semibold text-white mb-1">Intent Signals</h3>
                <p className="text-sm text-zinc-400">Find prospects on Twitter, Reddit, and forums</p>
              </div>
            </Link>

            <Link
              href="/leads"
              className="group relative overflow-hidden rounded-2xl bg-gradient-to-br from-purple-500/10 to-pink-500/10 border border-purple-500/20 p-6 transition hover:border-purple-500/40 hover:shadow-xl hover:shadow-purple-500/10"
            >
              <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 to-transparent opacity-0 group-hover:opacity-100 transition"></div>
              <div className="relative z-10">
                <div className="text-4xl mb-4">🎯</div>
                <h3 className="font-semibold text-white mb-1">Lead Discovery</h3>
                <p className="text-sm text-zinc-400">Discover companies and finance decision makers</p>
              </div>
            </Link>

            <Link
              href="/linkedin"
              className="group relative overflow-hidden rounded-2xl bg-gradient-to-br from-blue-500/10 to-indigo-500/10 border border-blue-500/20 p-6 transition hover:border-blue-500/40 hover:shadow-xl hover:shadow-blue-500/10"
            >
              <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-transparent opacity-0 group-hover:opacity-100 transition"></div>
              <div className="relative z-10">
                <div className="text-4xl mb-4">💼</div>
                <h3 className="font-semibold text-white mb-1">LinkedIn DMs</h3>
                <p className="text-sm text-zinc-400">Generate personalized connection messages</p>
              </div>
            </Link>

            <Link
              href="/email"
              className="group relative overflow-hidden rounded-2xl bg-gradient-to-br from-emerald-500/10 to-teal-500/10 border border-emerald-500/20 p-6 transition hover:border-emerald-500/40 hover:shadow-xl hover:shadow-emerald-500/10"
            >
              <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/5 to-transparent opacity-0 group-hover:opacity-100 transition"></div>
              <div className="relative z-10">
                <div className="text-4xl mb-4">✉️</div>
                <h3 className="font-semibold text-white mb-1">Email Campaigns</h3>
                <p className="text-sm text-zinc-400">Generate and send professional B2B emails</p>
              </div>
            </Link>
          </div>
        </div>

        {/* Settings Links */}
        <div>
          <h2 className="text-lg font-semibold text-white mb-4">Configuration</h2>
          <div className="grid gap-4 md:grid-cols-3">
            <Link
              href="/settings/templates"
              className="rounded-2xl bg-zinc-900/50 border border-zinc-800 p-5 transition hover:border-amber-500/30 hover:bg-zinc-900 flex items-center gap-4"
            >
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center text-lg shadow-lg">
                📝
              </div>
              <div>
                <div className="font-medium text-white">Templates</div>
                <div className="text-xs text-zinc-500">Manage message templates</div>
              </div>
            </Link>

            <Link
              href="/settings/products"
              className="rounded-2xl bg-zinc-900/50 border border-zinc-800 p-5 transition hover:border-pink-500/30 hover:bg-zinc-900 flex items-center gap-4"
            >
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-pink-500 to-rose-500 flex items-center justify-center text-lg shadow-lg">
                📦
              </div>
              <div>
                <div className="font-medium text-white">Products</div>
                <div className="text-xs text-zinc-500">Configure catalog and value props</div>
              </div>
            </Link>

            <Link
              href="/settings/knowledge"
              className="rounded-2xl bg-zinc-900/50 border border-zinc-800 p-5 transition hover:border-fuchsia-500/30 hover:bg-zinc-900 flex items-center gap-4"
            >
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-fuchsia-500 to-purple-500 flex items-center justify-center text-lg shadow-lg">
                🧠
              </div>
              <div>
                <div className="font-medium text-white">Knowledge Base</div>
                <div className="text-xs text-zinc-500">Upload PDFs & docs</div>
              </div>
            </Link>
          </div>
        </div>

        {/* Activity Feed */}
        <div className="grid gap-4 md:grid-cols-3">
          <div className="md:col-span-2 rounded-2xl border border-zinc-800 bg-zinc-900/60 p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-white">Activity</h3>
            </div>
            <ActivityFeed />
          </div>
          <div className="space-y-4">
            <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-5">
              <h3 className="font-semibold text-white mb-3">Shortcuts</h3>
              <div className="space-y-2 text-sm">
                <Link href="/skills" className="block px-3 py-2 rounded-lg border border-indigo-500/20 bg-indigo-500/5 text-indigo-100 hover:border-indigo-400/40">Run GTM skills workspace</Link>
                <Link href="/intent" className="block px-3 py-2 rounded-lg border border-cyan-500/20 bg-cyan-500/5 text-cyan-100 hover:border-cyan-400/40">Find intent signals</Link>
                <Link href="/leads" className="block px-3 py-2 rounded-lg border border-purple-500/20 bg-purple-500/5 text-purple-100 hover:border-purple-400/40">Discover companies</Link>
                <Link href="/linkedin" className="block px-3 py-2 rounded-lg border border-blue-500/20 bg-blue-500/5 text-blue-100 hover:border-blue-400/40">Generate LinkedIn DMs</Link>
                <Link href="/email" className="block px-3 py-2 rounded-lg border border-emerald-500/20 bg-emerald-500/5 text-emerald-100 hover:border-emerald-400/40">Generate emails</Link>
              </div>
            </div>
            <SystemStatus />
          </div>
        </div>
      </div>
    </AppShell>
  );
}
