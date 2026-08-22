/**
 * Editorial Operations Console style: parchment workspace, ink-blue structure,
 * signal-orange attention markers, and asymmetric queue-first composition.
 */
import { useMemo, useState } from "react";
import { Activity, ArrowUpRight, CheckCircle2, CircleAlert, Clock3, GitBranch, Menu, Moon, MoreHorizontal, Play, Search, Settings2, ShieldCheck, Sun, X } from "lucide-react";
import { useTheme } from "@/contexts/ThemeContext";

const repositories = [
  { name: "atlas-docs", tech: "TypeScript · React", status: "completed", date: "21 Aug 2026", failures: 0, action: "README structure clarified" },
  { name: "northstar-api", tech: "Python · Django", status: "pending", date: "—", failures: 0, action: "Awaiting inspection" },
  { name: "orchard-cms", tech: "PHP · Laravel", status: "no_action_needed", date: "19 Aug 2026", failures: 0, action: "No safe maintenance found" },
  { name: "ledger-web", tech: "TypeScript · Next.js", status: "failed", date: "18 Aug 2026", failures: 2, action: "Dependency check timed out" },
  { name: "signal-kit", tech: "C# · ASP.NET Core", status: "pending", date: "—", failures: 0, action: "Awaiting inspection" },
];

const statusCopy: Record<string, string> = { completed: "Completed", pending: "Pending", no_action_needed: "No action needed", failed: "Failed" };

function StatusPill({ status }: { status: string }) {
  const styles: Record<string, string> = { completed: "pill pill-green", pending: "pill pill-orange", no_action_needed: "pill pill-slate", failed: "pill pill-red" };
  return <span className={styles[status] || "pill pill-slate"}><span className="pill-dot" />{statusCopy[status] || status}</span>;
}

function Metric({ label, value, note, tone, icon: Icon }: { label: string; value: string; note: string; tone: string; icon: typeof Activity }) {
  return <div className="metric-card"><div className={`metric-icon ${tone}`}><Icon size={17} strokeWidth={1.8} /></div><div><p className="eyebrow">{label}</p><strong>{value}</strong><p className="metric-note">{note}</p></div></div>;
}

export default function Home() {
  const { theme, toggleTheme } = useTheme();
  const [query, setQuery] = useState("");
  const [navOpen, setNavOpen] = useState(false);
  const filtered = useMemo(() => repositories.filter((repo) => `${repo.name} ${repo.tech}`.toLowerCase().includes(query.toLowerCase())), [query]);
  return <div className="app-shell">
    <aside className={`sidebar ${navOpen ? "sidebar-open" : ""}`}>
      <div className="brand"><div className="brand-mark"><span /><span /><i /></div><div><strong>Daily Pipeline</strong><small>repository care, daily</small></div><button className="mobile-close" onClick={() => setNavOpen(false)} aria-label="Close navigation"><X size={18} /></button></div>
      <div className="rail-section"><p className="eyebrow rail-label">Workspace</p><button className="rail-link active"><Activity size={17} />Overview</button><button className="rail-link"><GitBranch size={17} />Repositories <span className="rail-count">12</span></button><button className="rail-link"><Clock3 size={17} />Run history</button></div>
      <div className="rail-section"><p className="eyebrow rail-label">System</p><button className="rail-link"><Settings2 size={17} />Configuration</button><button className="rail-link"><ShieldCheck size={17} />Safety policy</button></div>
      <div className="sidebar-footer"><div className="secure-line"><span className="secure-pulse" />Actions connected</div><p>Last sync<br /><b>Today, 09:42 PKT</b></p><div className="avatar">AR</div></div>
    </aside>
    {navOpen && <button className="scrim" onClick={() => setNavOpen(false)} aria-label="Close navigation" />}
    <main className="main-content">
      <header className="topbar"><button className="mobile-menu" onClick={() => setNavOpen(true)} aria-label="Open navigation"><Menu size={20} /></button><div className="breadcrumb"><span>Operations</span><b>/</b><strong>Overview</strong></div><div className="top-actions"><span className="live-label"><span className="live-dot" />Live queue</span><button className="icon-button" onClick={toggleTheme} aria-label="Toggle theme">{theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}</button><button className="profile-button"><span className="avatar avatar-small">AR</span><MoreHorizontal size={17} /></button></div></header>
      <div className="workspace">
        <section className="intro"><div className="intro-copy"><p className="kicker"><span className="kicker-line" /> Friday, 22 August 2026 · 09:42 PKT</p><h1>One repository.<br /><em>One honest improvement.</em></h1><p className="intro-lede">A quiet daily pass across your GitHub workspace. The pipeline inspects one eligible repository at a time and only ships changes that genuinely improve the project.</p><div className="intro-actions"><button className="primary-button"><Play size={15} fill="currentColor" />Run dry check</button><button className="text-button">Review safety policy <ArrowUpRight size={15} /></button></div></div><div className="intro-art"><img src="/manus-storage/github-pipeline-hero_d0adb85c.png" alt="Notebook and laptop on a warm desk" /><div className="art-caption"><span>01</span><span>Inspection, not activity</span></div></div></section>
        <section className="metrics"><Metric label="Total repositories" value="12" note="11 eligible · 1 archived" tone="blue" icon={GitBranch} /><Metric label="Pending queue" value="07" note="Next: northstar-api" tone="orange" icon={Clock3} /><Metric label="Completed this month" value="08" note="6 meaningful updates" tone="green" icon={CheckCircle2} /><Metric label="Manual review" value="01" note="ledger-web · 2 failures" tone="red" icon={CircleAlert} /></section>
        <div className="content-grid"><section className="queue-panel panel"><div className="panel-heading"><div><p className="eyebrow">Repository queue</p><h2>Next in line</h2></div><div className="heading-tools"><div className="search-wrap"><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Filter repositories" aria-label="Filter repositories" /></div><button className="filter-button">All statuses</button></div></div><div className="table-wrap"><table><thead><tr><th>Repository</th><th>Status</th><th>Last processed</th><th>Failures</th><th>Latest action</th><th /></tr></thead><tbody>{filtered.map((repo) => <tr key={repo.name}><td><div className="repo-cell"><div className="repo-icon"><GitBranch size={15} /></div><div><strong>{repo.name}</strong><span>{repo.tech}</span></div></div></td><td><StatusPill status={repo.status} /></td><td className="mono">{repo.date}</td><td className={`failure-count ${repo.failures > 0 ? "failure-hot" : ""}`}>{String(repo.failures).padStart(2, "0")}</td><td className="action-cell">{repo.action}</td><td><button className="row-menu" aria-label={`Actions for ${repo.name}`}><MoreHorizontal size={17} /></button></td></tr>)}</tbody></table></div><div className="panel-foot"><span>Showing {filtered.length} of 12 repositories</span><button className="text-button">Open queue <ArrowUpRight size={14} /></button></div></section>
          <aside className="run-panel panel"><div className="run-top"><div><p className="eyebrow">Today’s run</p><h2>Northstar API</h2></div><span className="run-index">02 / 12</span></div><div className="run-status"><div className="status-orbit"><span /><span /><span /></div><div><StatusPill status="pending" /><p>Queued for inspection</p></div></div><div className="run-details"><div><span>Scheduled</span><strong>10:00 AM <small>PKT</small></strong></div><div><span>Branch</span><strong className="mono">main</strong></div><div><span>Last action</span><strong>Never processed</strong></div></div><div className="run-note"><div className="note-mark">!</div><p><strong>What happens next</strong>The engine will detect the stack, inspect project health, and stop if it cannot find a safe, meaningful change.</p></div><button className="outline-button">View repository <ArrowUpRight size={15} /></button><div className="run-footer"><span><span className="green-dot" />DRY_RUN enabled</span><button>Change setting <ArrowUpRight size={13} /></button></div></aside></div>
      </div>
    </main>
  </div>;
}
