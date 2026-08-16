"use client";

import { useMemo, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";

type SkillKey =
  | "icp"
  | "prospecting"
  | "research"
  | "qualification"
  | "signal"
  | "outreach"
  | "meeting";

const skills: Array<{ key: SkillKey; label: string }> = [
  { key: "icp", label: "01 ICP Definition" },
  { key: "prospecting", label: "02 Prospecting" },
  { key: "research", label: "03 Account Research" },
  { key: "qualification", label: "04 Qualification & Scoring" },
  { key: "signal", label: "05 Signal-Based Outbound" },
  { key: "outreach", label: "06 Outreach Strategy" },
  { key: "meeting", label: "07 Meeting Prep" },
];

function scoreBucket(score: number): "Tier A" | "Tier B" | "Tier C" {
  if (score >= 75) return "Tier A";
  if (score >= 50) return "Tier B";
  return "Tier C";
}

export default function SkillsWorkbench() {
  const [activeSkill, setActiveSkill] = useState<SkillKey>("icp");

  // Skill 01: ICP Definition
  const [targetIndustries, setTargetIndustries] = useState("SaaS, Manufacturing, Logistics");
  const [targetEmployeeBand, setTargetEmployeeBand] = useState("200-5000");
  const [targetTitles, setTargetTitles] = useState("CFO, VP Finance, Controller");
  const [winningSignals, setWinningSignals] = useState(
    "Infrastructure refresh, cyber security upgrade, cloud migration, defense program sourcing"
  );

  // Skill 02 + 04 data
  const [firmographicFit, setFirmographicFit] = useState(70);
  const [timingSignals, setTimingSignals] = useState(60);
  const [accessPath, setAccessPath] = useState(45);
  const [intentStrength, setIntentStrength] = useState(80);

  // Skill 03
  const [accountName, setAccountName] = useState("Acme Finance Inc.");
  const [accountCatalyst, setAccountCatalyst] = useState("Expanding into 3 new regions in Q2");
  const [engageRoles, setEngageRoles] = useState("CFO, VP Finance Systems, AR Director");

  // Skill 05
  const [signalType, setSignalType] = useState("Website revisit");
  const [signalContext, setSignalContext] = useState(
    "Visited pricing page 3x in 48 hours and viewed collections automation docs"
  );

  // Skill 06
  const [primaryAngle, setPrimaryAngle] = useState("Cash acceleration");
  const [objection, setObjection] = useState("We already have an ERP and collections process.");

  // Skill 07
  const [meetingType, setMeetingType] = useState("Discovery call");
  const [relationshipHistory, setRelationshipHistory] = useState(
    "Intro email sent, one reply received, call booked by CFO."
  );

  const qualificationScore = useMemo(() => {
    const weighted =
      firmographicFit * 0.35 +
      timingSignals * 0.25 +
      accessPath * 0.2 +
      intentStrength * 0.2;
    return Math.round(weighted);
  }, [firmographicFit, timingSignals, accessPath, intentStrength]);

  const qualificationTier = scoreBucket(qualificationScore);

  const outreachAngle = useMemo(() => {
    if (signalType.toLowerCase().includes("website")) {
      return "You are evaluating solutions right now. Lead with a concrete before/after result.";
    }
    if (signalType.toLowerCase().includes("hiring")) {
      return "Hiring is a change signal. Position automation as scale without headcount bloat.";
    }
    return "Start with the business change, then map to one measurable win in 90 days.";
  }, [signalType]);

  return (
    <div className="space-y-6">
      <div className="rounded-2xl bg-gradient-to-br from-lime-600 via-green-600 to-emerald-700 p-7 text-white shadow-2xl shadow-lime-500/20">
        <h1 className="text-3xl font-bold">CHILLION GTM Skills Lab</h1>
        <p className="mt-2 max-w-3xl text-lime-100">
          Repeatable outreach methodology for Chillion — IT infrastructure, cyber security, cloud, software licensing, and advanced engineering.
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-[300px_1fr]">
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-3">
          <div className="mb-2 px-2 text-xs font-semibold uppercase tracking-wider text-zinc-500">
            Skills
          </div>
          <div className="space-y-1">
            {skills.map((skill) => (
              <button
                key={skill.key}
                onClick={() => setActiveSkill(skill.key)}
                className={`w-full rounded-xl px-3 py-2 text-left text-sm transition ${
                  activeSkill === skill.key
                    ? "bg-indigo-500/20 text-indigo-100 border border-indigo-500/40"
                    : "text-zinc-300 hover:bg-zinc-800"
                }`}
              >
                {skill.label}
              </button>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6">
          {activeSkill === "icp" && (
            <div className="space-y-4">
              <h2 className="text-xl font-semibold text-white">Skill 01 - ICP Definition</h2>
              <p className="text-sm text-zinc-400">
                Pressure-test your ICP from observed winning signals, not assumptions.
              </p>
              <div className="grid gap-4 md:grid-cols-2">
                <label className="text-sm text-zinc-300">
                  Industries
                  <textarea
                    value={targetIndustries}
                    onChange={(e) => setTargetIndustries(e.target.value)}
                    rows={2}
                    className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-white"
                  />
                </label>
                <label className="text-sm text-zinc-300">
                  Employee band
                  <input
                    value={targetEmployeeBand}
                    onChange={(e) => setTargetEmployeeBand(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-white"
                  />
                </label>
                <label className="text-sm text-zinc-300">
                  Buying committee titles
                  <textarea
                    value={targetTitles}
                    onChange={(e) => setTargetTitles(e.target.value)}
                    rows={2}
                    className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-white"
                  />
                </label>
                <label className="text-sm text-zinc-300">
                  Winning signals
                  <textarea
                    value={winningSignals}
                    onChange={(e) => setWinningSignals(e.target.value)}
                    rows={2}
                    className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-white"
                  />
                </label>
              </div>
              <div className="rounded-xl border border-indigo-500/30 bg-indigo-500/10 p-4 text-sm text-indigo-100">
                ICP Snapshot: Prioritize {targetIndustries} companies in the {targetEmployeeBand}{" "}
                employee range, targeting {targetTitles}. Key trigger signals: {winningSignals}.
              </div>
            </div>
          )}

          {activeSkill === "prospecting" && (
            <div className="space-y-4">
              <h2 className="text-xl font-semibold text-white">Skill 02 - Prospecting</h2>
              <p className="text-sm text-zinc-400">
                Run disciplined qualification on firmographics, triggers, and timing.
              </p>
              <div className="space-y-3">
                <Slider label="Firmographic fit" value={firmographicFit} onChange={setFirmographicFit} />
                <Slider label="Timing signals" value={timingSignals} onChange={setTimingSignals} />
                <Slider label="Access path" value={accessPath} onChange={setAccessPath} />
                <Slider label="Intent strength" value={intentStrength} onChange={setIntentStrength} />
              </div>
              <div className="flex items-center gap-3">
                <Badge variant="info">Prospect score: {qualificationScore}</Badge>
                <Badge variant={qualificationTier === "Tier A" ? "success" : "warning"}>
                  {qualificationTier}
                </Badge>
              </div>
            </div>
          )}

          {activeSkill === "research" && (
            <div className="space-y-4">
              <h2 className="text-xl font-semibold text-white">Skill 03 - Account Research</h2>
              <p className="text-sm text-zinc-400">
                Build a full commercial picture: why this company, why now, who to engage.
              </p>
              <div className="grid gap-4 md:grid-cols-2">
                <label className="text-sm text-zinc-300">
                  Account name
                  <input
                    value={accountName}
                    onChange={(e) => setAccountName(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-white"
                  />
                </label>
                <label className="text-sm text-zinc-300">
                  Current catalyst
                  <input
                    value={accountCatalyst}
                    onChange={(e) => setAccountCatalyst(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-white"
                  />
                </label>
                <label className="text-sm text-zinc-300 md:col-span-2">
                  Stakeholders to engage
                  <input
                    value={engageRoles}
                    onChange={(e) => setEngageRoles(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-white"
                  />
                </label>
              </div>
              <div className="rounded-xl border border-zinc-700 bg-zinc-800/50 p-4 text-sm text-zinc-200">
                Why now: {accountCatalyst}. Recommended stakeholder sequence: {engageRoles}.
              </div>
            </div>
          )}

          {activeSkill === "qualification" && (
            <div className="space-y-4">
              <h2 className="text-xl font-semibold text-white">Skill 04 - Qualification & Scoring</h2>
              <p className="text-sm text-zinc-400">
                Score every lead using Fit, Timing, Access, and Intent (4D model).
              </p>
              <div className="grid gap-3 md:grid-cols-2">
                <ScoreCard label="Fit" value={firmographicFit} />
                <ScoreCard label="Timing" value={timingSignals} />
                <ScoreCard label="Access" value={accessPath} />
                <ScoreCard label="Intent" value={intentStrength} />
              </div>
              <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-emerald-100">
                Composite score: <strong>{qualificationScore}</strong> ({qualificationTier}) - use
                this to prioritize outreach order and channel intensity.
              </div>
            </div>
          )}

          {activeSkill === "signal" && (
            <div className="space-y-4">
              <h2 className="text-xl font-semibold text-white">Skill 05 - Signal-Based Outbound</h2>
              <p className="text-sm text-zinc-400">
                Convert raw signal into contextual outreach angle.
              </p>
              <label className="text-sm text-zinc-300">
                Signal type
                <input
                  value={signalType}
                  onChange={(e) => setSignalType(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-white"
                />
              </label>
              <label className="text-sm text-zinc-300">
                Signal context
                <textarea
                  value={signalContext}
                  onChange={(e) => setSignalContext(e.target.value)}
                  rows={3}
                  className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-white"
                />
              </label>
              <div className="rounded-xl border border-cyan-500/30 bg-cyan-500/10 p-4 text-sm text-cyan-100">
                Recommended angle: {outreachAngle}
              </div>
              <div className="rounded-xl border border-zinc-700 bg-zinc-800/50 p-4 text-sm text-zinc-200">
                Outreach draft starter: "Noticed {signalType.toLowerCase()} at your team. {signalContext}.
                Teams in similar situations usually optimize cash conversion within 90 days by fixing
                one workflow first."
              </div>
            </div>
          )}

          {activeSkill === "outreach" && (
            <div className="space-y-4">
              <h2 className="text-xl font-semibold text-white">Skill 06 - Outreach Strategy</h2>
              <p className="text-sm text-zinc-400">
                Define angle, channel sequence, and objection pre-emption before writing copy.
              </p>
              <div className="grid gap-4 md:grid-cols-2">
                <label className="text-sm text-zinc-300">
                  Primary angle
                  <input
                    value={primaryAngle}
                    onChange={(e) => setPrimaryAngle(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-white"
                  />
                </label>
                <label className="text-sm text-zinc-300">
                  Likely objection
                  <input
                    value={objection}
                    onChange={(e) => setObjection(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-white"
                  />
                </label>
              </div>
              <div className="rounded-xl border border-zinc-700 bg-zinc-800/50 p-4 text-sm text-zinc-200">
                Sequence: Day 1 LinkedIn note - Day 3 value email - Day 7 objection-handling follow-up
                - Day 12 short breakup message.
              </div>
              <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-100">
                {`Objection pre-emption: "${objection}" -> acknowledge existing stack, position as layer that increases ROI from current systems.`}
              </div>
            </div>
          )}

          {activeSkill === "meeting" && (
            <div className="space-y-4">
              <h2 className="text-xl font-semibold text-white">Skill 07 - Meeting Prep</h2>
              <p className="text-sm text-zinc-400">
                Generate a one-page brief before every prospect conversation.
              </p>
              <div className="grid gap-4 md:grid-cols-2">
                <label className="text-sm text-zinc-300">
                  Meeting type
                  <input
                    value={meetingType}
                    onChange={(e) => setMeetingType(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-white"
                  />
                </label>
                <label className="text-sm text-zinc-300">
                  Account
                  <input
                    value={accountName}
                    onChange={(e) => setAccountName(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-white"
                  />
                </label>
              </div>
              <label className="text-sm text-zinc-300">
                Relationship history
                <textarea
                  value={relationshipHistory}
                  onChange={(e) => setRelationshipHistory(e.target.value)}
                  rows={3}
                  className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-white"
                />
              </label>
              <div className="rounded-xl border border-violet-500/30 bg-violet-500/10 p-4 text-sm text-violet-100">
                <div className="font-semibold">Brief</div>
                <div className="mt-1">Meeting: {meetingType}</div>
                <div>Company: {accountName}</div>
                <div>Why now: {accountCatalyst}</div>
                <div>Stakeholders: {engageRoles}</div>
                <div className="mt-2">Relationship history: {relationshipHistory}</div>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="flex justify-end">
        <Button className="bg-indigo-500 text-white hover:bg-indigo-400">
          Save Skill Defaults
        </Button>
      </div>
    </div>
  );
}

function Slider({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (next: number) => void;
}) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-3">
      <div className="mb-2 flex items-center justify-between text-sm">
        <span className="text-zinc-300">{label}</span>
        <span className="text-zinc-100">{value}</span>
      </div>
      <input
        type="range"
        min={0}
        max={100}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full"
      />
    </div>
  );
}

function ScoreCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-zinc-700 bg-zinc-800/40 p-4">
      <div className="text-sm text-zinc-400">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-white">{value}</div>
    </div>
  );
}
