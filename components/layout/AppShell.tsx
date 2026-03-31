import Link from "next/link";
import Image from "next/image";
import { getOptionalSession } from "@/lib/auth/guards";
import { ThemeToggle } from "@/components/ui/ThemeToggle";

export default async function AppShell({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await getOptionalSession();

  const mainLinks = [
    { href: "/dashboard", label: "Dashboard", icon: "📊", gradient: "from-slate-500 to-slate-600" },
    { href: "/skills", label: "GTM Skills", icon: "🧩", gradient: "from-indigo-500 to-violet-600" },
    { href: "/meetings", label: "Meetings", icon: "📅", gradient: "from-violet-500 to-purple-600" },
  ];

  const agentLinks = [
    { href: "/intent", label: "Intent Signals", icon: "🔍", gradient: "from-cyan-500 to-blue-600" },
    { href: "/leads", label: "Lead Discovery", icon: "🎯", gradient: "from-purple-500 to-pink-600" },
    { href: "/linkedin", label: "LinkedIn DM", icon: "💼", gradient: "from-blue-500 to-indigo-600" },
    { href: "/email", label: "Email Campaign", icon: "✉️", gradient: "from-emerald-500 to-teal-600" },
  ];

  const settingsLinks = [
    { href: "/settings/templates", label: "Templates", icon: "📝", gradient: "from-amber-500 to-orange-600" },
    { href: "/settings/products", label: "Products", icon: "📦", gradient: "from-pink-500 to-rose-600" },
    { href: "/settings/knowledge", label: "Knowledge Base", icon: "🧠", gradient: "from-fuchsia-500 to-purple-600" },
  ];

  return (
    <div className="flex min-h-screen bg-zinc-950 text-zinc-50">
      {/* Sidebar */}
      <aside className="hidden w-72 flex-col bg-gradient-to-b from-zinc-900 via-zinc-900 to-zinc-950 border-r border-zinc-800 md:flex">
        {/* Logo */}
        <div className="p-6 border-b border-zinc-800">
          <Link href="/dashboard" className="flex items-center gap-3">
            <Image
              src="/images/logo.svg"
              alt="CHILLION IT Consulting"
              width={160}
              height={40}
              className="h-9 w-auto object-contain object-left"
              priority
            />
          </Link>
          <div className="mt-2 text-xs text-zinc-500">Outreach Command Center</div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-6 overflow-y-auto">
          {/* Main */}
          <div>
            <div className="px-3 mb-2 text-xs font-semibold text-zinc-500 uppercase tracking-wider">Overview</div>
            <div className="space-y-1">
              {mainLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-zinc-300 hover:text-white transition group"
                >
                  <div className={`w-9 h-9 rounded-lg bg-gradient-to-br ${link.gradient} flex items-center justify-center text-lg shadow-lg group-hover:scale-110 transition`}>
                    {link.icon}
                  </div>
                  <span className="font-medium">{link.label}</span>
                </Link>
              ))}
            </div>
          </div>

          {/* AI Agents */}
          <div>
            <div className="px-3 mb-2 text-xs font-semibold text-zinc-500 uppercase tracking-wider">AI Agents</div>
            <div className="space-y-1">
              {agentLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-zinc-300 hover:text-white transition group"
                >
                  <div className={`w-9 h-9 rounded-lg bg-gradient-to-br ${link.gradient} flex items-center justify-center text-lg shadow-lg group-hover:scale-110 transition`}>
                    {link.icon}
                  </div>
                  <span className="font-medium">{link.label}</span>
                </Link>
              ))}
            </div>
          </div>

          {/* Settings */}
          <div>
            <div className="px-3 mb-2 text-xs font-semibold text-zinc-500 uppercase tracking-wider">Configuration</div>
            <div className="space-y-1">
              {settingsLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-zinc-300 hover:text-white transition group"
                >
                  <div className={`w-9 h-9 rounded-lg bg-gradient-to-br ${link.gradient} flex items-center justify-center text-lg shadow-lg group-hover:scale-110 transition`}>
                    {link.icon}
                  </div>
                  <span className="font-medium">{link.label}</span>
                </Link>
              ))}
            </div>
          </div>
        </nav>

        {/* User Info */}
        {session?.user && (
          <div className="p-4 border-t border-zinc-800">
            <div className="flex items-center gap-3 px-3 py-2">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-zinc-600 to-zinc-700 flex items-center justify-center text-lg">
                👤
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-zinc-200 truncate">
                  {session.user.email}
                </div>
                <div className="text-xs text-zinc-500">
                  {session.workspace?.name ?? "Workspace"}
                </div>
              </div>
            </div>
          </div>
        )}
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <div className="min-h-screen bg-gradient-to-br from-zinc-950 via-zinc-900 to-zinc-950">
          <div className="mx-auto max-w-7xl px-6 py-8 space-y-4">
            <div className="flex items-center justify-end">
              <ThemeToggle />
            </div>
            {children}
          </div>
        </div>
      </main>
    </div>
  );
}
