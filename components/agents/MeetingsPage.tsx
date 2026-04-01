"use client";

import { useState, useEffect } from "react";
import {
  getCalendlyStatus,
  getCalendlyEventTypes,
  getUpcomingMeetings,
  getPastMeetings,
  getMeetingStats,
  type CalendlyStatus,
  type CalendlyEvent,
  type CalendlyEventType,
  type MeetingStats,
} from "@/lib/api/agents";

function StatsCard({ title, value, icon, gradient }: { title: string; value: string | number; icon: string; gradient: string }) {
  return (
    <div className={`rounded-2xl bg-gradient-to-br ${gradient} p-5 text-white shadow-lg`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm opacity-80">{title}</p>
          <p className="text-3xl font-bold mt-1">{value}</p>
        </div>
        <div className="text-4xl opacity-80">{icon}</div>
      </div>
    </div>
  );
}

export default function MeetingsPage() {
  const [calendlyStatus, setCalendlyStatus] = useState<CalendlyStatus | null>(null);
  const [eventTypes, setEventTypes] = useState<CalendlyEventType[]>([]);
  const [upcomingMeetings, setUpcomingMeetings] = useState<CalendlyEvent[]>([]);
  const [pastMeetings, setPastMeetings] = useState<CalendlyEvent[]>([]);
  const [stats, setStats] = useState<MeetingStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeView, setActiveView] = useState<"upcoming" | "past">("upcoming");

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [status, types, upcoming, past, meetingStats] = await Promise.all([
        getCalendlyStatus(),
        getCalendlyEventTypes(),
        getUpcomingMeetings(30),
        getPastMeetings(30),
        getMeetingStats(),
      ]);
      setCalendlyStatus(status);
      setEventTypes(types);
      setUpcomingMeetings(upcoming);
      setPastMeetings(past);
      setStats(meetingStats);
    } catch (e) {
      console.error("Failed to load Calendly data:", e);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
  };

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
  };

  const isToday = (dateStr: string) => {
    const date = new Date(dateStr);
    const today = new Date();
    return date.toDateString() === today.toDateString();
  };

  const meetings = activeView === "upcoming" ? upcomingMeetings : pastMeetings;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-violet-400 to-purple-400 bg-clip-text text-transparent">
            Meetings
          </h1>
          <p className="text-zinc-400 mt-1">Track all your Calendly meetings in one place</p>
        </div>
        {calendlyStatus?.connected && calendlyStatus.user && (
          <div className="flex items-center gap-3 px-4 py-2 bg-violet-500/10 rounded-xl border border-violet-500/20">
            <span className="w-2 h-2 bg-violet-400 rounded-full animate-pulse"></span>
            <span className="text-sm font-medium text-violet-400">{calendlyStatus.user.name}</span>
            <a href={calendlyStatus.user.scheduling_url} target="_blank" rel="noopener noreferrer" className="text-xs text-violet-300 hover:text-violet-200">
              Booking Page →
            </a>
          </div>
        )}
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatsCard title="Today" value={stats.today_count} icon="📆" gradient="from-violet-500 to-purple-600" />
          <StatsCard title="This Week" value={stats.this_week_count} icon="📊" gradient="from-blue-500 to-indigo-600" />
          <StatsCard title="Upcoming" value={stats.upcoming_count} icon="🚀" gradient="from-emerald-500 to-teal-600" />
          <StatsCard title="Completed" value={stats.past_30_days_count} icon="✅" gradient="from-amber-500 to-orange-600" />
        </div>
      )}

      {/* Not Connected State */}
      {!calendlyStatus?.connected && !loading && (
        <div className="rounded-2xl border-2 border-dashed border-violet-500/30 bg-violet-500/5 p-12 text-center">
          <div className="text-6xl mb-4">📅</div>
          <h3 className="font-semibold text-xl text-white">Connect Calendly</h3>
          <p className="text-zinc-400 mt-2 max-w-md mx-auto">
            Add your Calendly credentials to your <code className="bg-zinc-800 px-2 py-0.5 rounded text-violet-400">.env</code> file
          </p>
          <div className="mt-6 text-left max-w-lg mx-auto bg-zinc-900 rounded-xl p-4 text-sm font-mono border border-zinc-800">
            <div className="text-zinc-500">CALENDLY_ACCESS_TOKEN=your_token</div>
            <div className="text-zinc-500">CALENDLY_USER_URI=https://api.calendly.com/users/...</div>
          </div>
        </div>
      )}

      {calendlyStatus?.connected && (
        <>
          {/* Event Types */}
          {eventTypes.length > 0 && (
            <div className="rounded-2xl bg-gradient-to-br from-zinc-900 to-zinc-900/50 border border-zinc-800 p-6">
              <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
                <span className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-purple-500 flex items-center justify-center text-sm">🔗</span>
                Your Booking Links
              </h3>
              <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                {eventTypes.map((et) => (
                  <a
                    key={et.uri}
                    href={et.scheduling_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-3 p-4 rounded-xl bg-zinc-800/50 border border-zinc-700 hover:border-violet-500/50 hover:bg-violet-500/5 transition group"
                  >
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: et.color || "#8b5cf6" }}></div>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-white text-sm truncate group-hover:text-violet-300 transition">{et.name}</div>
                      <div className="text-xs text-zinc-500">{et.duration_minutes} min</div>
                    </div>
                    <span className="text-violet-400 text-xs opacity-0 group-hover:opacity-100 transition">Open →</span>
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* Meetings List */}
          <div className="rounded-2xl bg-gradient-to-br from-zinc-900 to-zinc-900/50 border border-zinc-800 overflow-hidden">
            <div className="p-4 border-b border-zinc-800 flex justify-between items-center">
              <div className="flex gap-2">
                <button
                  onClick={() => setActiveView("upcoming")}
                  className={`px-4 py-2 rounded-xl text-sm font-medium transition ${
                    activeView === "upcoming"
                      ? "bg-gradient-to-r from-violet-500 to-purple-500 text-white shadow-lg"
                      : "text-zinc-400 hover:text-white hover:bg-zinc-800"
                  }`}
                >
                  Upcoming ({upcomingMeetings.length})
                </button>
                <button
                  onClick={() => setActiveView("past")}
                  className={`px-4 py-2 rounded-xl text-sm font-medium transition ${
                    activeView === "past"
                      ? "bg-gradient-to-r from-violet-500 to-purple-500 text-white shadow-lg"
                      : "text-zinc-400 hover:text-white hover:bg-zinc-800"
                  }`}
                >
                  Past ({pastMeetings.length})
                </button>
              </div>
              <button onClick={loadData} disabled={loading} className="text-sm text-violet-400 hover:text-violet-300">
                {loading ? "Loading..." : "🔄 Refresh"}
              </button>
            </div>

            {meetings.length === 0 ? (
              <div className="p-16 text-center text-zinc-500">
                <div className="text-5xl mb-4">{activeView === "upcoming" ? "📭" : "📪"}</div>
                <p className="font-medium">No {activeView} meetings</p>
              </div>
            ) : (
              <div className="divide-y divide-zinc-800 max-h-[500px] overflow-y-auto">
                {meetings.map((meeting) => (
                  <div key={meeting.uri} className={`p-4 hover:bg-zinc-800/50 transition ${isToday(meeting.start_time) ? "bg-violet-500/5" : ""}`}>
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                            meeting.status === "active" ? "bg-emerald-500/20 text-emerald-400" : "bg-zinc-700 text-zinc-400"
                          }`}>
                            {meeting.status}
                          </span>
                          {isToday(meeting.start_time) && (
                            <span className="px-2 py-0.5 rounded text-xs font-medium bg-violet-500/20 text-violet-400">Today</span>
                          )}
                        </div>
                        <h4 className="font-medium text-white mt-2">{meeting.name}</h4>
                        {meeting.invitee_name && (
                          <div className="text-sm text-zinc-400 mt-1">
                            👤 {meeting.invitee_name}
                            {meeting.invitee_email && <span className="text-zinc-500 ml-2">{meeting.invitee_email}</span>}
                            {meeting.invitee_company && <span className="text-zinc-500 ml-2">@ {meeting.invitee_company}</span>}
                          </div>
                        )}
                        {meeting.location && (
                          <div className="text-xs text-zinc-500 mt-1">📍 {meeting.location}</div>
                        )}
                      </div>
                      <div className="text-right">
                        <div className="font-semibold text-violet-400">{formatTime(meeting.start_time)}</div>
                        <div className="text-xs text-zinc-500">{formatDate(meeting.start_time)}</div>
                        {meeting.reschedule_url && activeView === "upcoming" && (
                          <a href={meeting.reschedule_url} target="_blank" rel="noopener noreferrer" className="text-xs text-violet-400 hover:text-violet-300 mt-1 block">
                            Reschedule
                          </a>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

