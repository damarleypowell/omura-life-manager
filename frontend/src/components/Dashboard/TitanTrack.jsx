/**
 * Titan Track — a clear, Duolingo-style learning system.
 *
 * One question answered fast: "What do I study today, and where am I?"
 *
 * Views:
 *   Dashboard  — streak + XP + level, today's lessons, active projects,
 *                your path, this week, next test.
 *   Lesson     — Robert-Greene-style: big picture → concept → history →
 *                today → visual → exercise → quiz → explain-back → project.
 *   Project    — build a real thing; AI grades it. (or a negotiation sim)
 *   Syllabus   — the whole curriculum, by track, with where you are.
 *   Test       — weekly/monthly review, graded per track.
 */

import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  FiZap, FiStar, FiAward, FiLock, FiCheck, FiCheckCircle, FiPlay, FiArrowRight,
  FiArrowLeft, FiX, FiTarget, FiRefreshCw, FiBookOpen, FiClock, FiSettings,
  FiChevronRight, FiList, FiTrendingUp, FiEdit3, FiSend, FiMessageCircle,
} from 'react-icons/fi';
import { titan } from '../../services/apiService';

// ── Levels (XP thresholds) ──
const LEVELS = [
  { name: 'Apprentice', min: 0,    color: '#9CA3AF' },
  { name: 'Analyst',    min: 150,  color: '#60A5FA' },
  { name: 'Strategist', min: 400,  color: '#A78BFA' },
  { name: 'Architect',  min: 800,  color: '#34D399' },
  { name: 'Sovereign',  min: 1500, color: '#FBBF24' },
];

function levelFor(xp) {
  let cur = LEVELS[0];
  let next = null;
  for (let i = 0; i < LEVELS.length; i++) {
    if (xp >= LEVELS[i].min) { cur = LEVELS[i]; next = LEVELS[i + 1] || null; }
  }
  const span = next ? next.min - cur.min : 1;
  const into = next ? xp - cur.min : 1;
  const pct = next ? Math.min(100, Math.round((into / span) * 100)) : 100;
  return { cur, next, pct, num: LEVELS.indexOf(cur) + 1 };
}

const STATUS_META = {
  mastered:    { color: '#34D399', icon: '✓', label: 'Mastered' },
  in_progress: { color: '#FBBF24', icon: '◐', label: 'In progress' },
  available:   { color: '#60A5FA', icon: '○', label: 'Ready' },
  locked:      { color: '#3F3F46', icon: '🔒', label: 'Locked' },
};

const SLOT_ICON = { morning: '🌅', afternoon: '☀️', evening: '🌙' };

// ════════════════════════════════════════════════════════════════
// Shared bits
// ════════════════════════════════════════════════════════════════

function Diagram({ diagram }) {
  if (!diagram) return null;
  const { type, title, nodes, columns } = diagram;
  if (type === 'comparison' && Array.isArray(columns)) {
    return (
      <div className="glass-inner" style={{ padding: 14 }}>
        {title && <p style={{ fontSize: 12, color: '#A1A1AA', marginBottom: 10, fontWeight: 600 }}>{title}</p>}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 12 }}>
          {columns.map((col, i) => (
            <div key={i} style={{ background: '#0D0D0F', border: '1px solid #1E1E24', borderRadius: 10, padding: 12 }}>
              <p style={{ fontSize: 12, fontWeight: 700, color: '#FAFAFA', marginBottom: 6 }}>{col.label}</p>
              <ul style={{ margin: 0, paddingLeft: 16 }}>
                {(col.points || []).map((p, j) => (
                  <li key={j} style={{ fontSize: 12, color: '#A1A1AA', marginBottom: 4, lineHeight: 1.5 }}>{p}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    );
  }
  const list = Array.isArray(nodes) ? nodes : [];
  if (!list.length) return null;
  return (
    <div className="glass-inner" style={{ padding: 14 }}>
      {title && <p style={{ fontSize: 12, color: '#A1A1AA', marginBottom: 10, fontWeight: 600 }}>{title}</p>}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8 }}>
        {list.map((n, i) => (
          <React.Fragment key={i}>
            <div style={{ background: '#0D0D0F', border: '1px solid #2A2A33', borderRadius: 10, padding: '10px 14px', fontSize: 13, color: '#E4E4E7', fontWeight: 500 }}>{n}</div>
            {i < list.length - 1 && <FiArrowRight size={14} style={{ color: '#52525B', flexShrink: 0 }} />}
          </React.Fragment>
        ))}
        {type === 'cycle' && list.length > 1 && <span style={{ fontSize: 11, color: '#52525B' }}>↺ repeats</span>}
      </div>
    </div>
  );
}

function ConfidenceTag({ level }) {
  const map = {
    strong: ['STRONG', '#34D399'], moderate: ['MODERATE', '#60A5FA'],
    contested: ['CONTESTED', '#FBBF24'], theoretical: ['THEORETICAL', '#A78BFA'],
  };
  const [label, color] = map[level] || map.moderate;
  return (
    <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.05em', color, border: `1px solid ${color}55`, borderRadius: 6, padding: '2px 7px' }}>
      {label}
    </span>
  );
}

function Overlay({ children, onClose }) {
  return (
    <div
      style={{ position: 'fixed', inset: 0, zIndex: 100, background: 'rgba(8,8,10,0.82)', backdropFilter: 'blur(4px)', overflowY: 'auto', padding: '32px 16px' }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose?.(); }}
    >
      <div style={{ maxWidth: 760, margin: '0 auto' }}>{children}</div>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════
// Dashboard pieces
// ════════════════════════════════════════════════════════════════

function StatHeader({ streak, xp, onOpenSchedule }) {
  const lv = levelFor(xp);
  return (
    <div className="glass-card" style={{ display: 'flex', alignItems: 'center', gap: 24, flexWrap: 'wrap' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ fontSize: 30 }}>🔥</span>
        <div>
          <div style={{ fontSize: 30, fontWeight: 800, color: '#FAFAFA', lineHeight: 1 }}>{streak?.current_streak ?? 0}</div>
          <div style={{ fontSize: 11, color: '#71717A' }}>day streak</div>
        </div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <FiStar size={26} style={{ color: '#FBBF24' }} />
        <div>
          <div style={{ fontSize: 30, fontWeight: 800, color: '#FAFAFA', lineHeight: 1 }}>{xp}</div>
          <div style={{ fontSize: 11, color: '#71717A' }}>XP earned</div>
        </div>
      </div>
      <div style={{ flex: 1, minWidth: 200 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
          <FiAward style={{ color: lv.cur.color }} />
          <span style={{ fontSize: 14, fontWeight: 700, color: '#FAFAFA' }}>Lv.{lv.num} {lv.cur.name}</span>
          <span style={{ fontSize: 11, color: '#71717A', marginLeft: 'auto' }}>
            {lv.next ? `${lv.next.min - xp} XP to ${lv.next.name}` : 'Max level'}
          </span>
        </div>
        <div style={{ height: 8, background: '#1A1A1F', borderRadius: 4, overflow: 'hidden' }}>
          <div style={{ width: `${lv.pct}%`, height: '100%', background: lv.cur.color, transition: 'width .5s ease' }} />
        </div>
      </div>
      <button className="btn btn-ghost" onClick={onOpenSchedule} title="Schedule settings" aria-label="Schedule settings">
        <FiSettings size={16} />
      </button>
    </div>
  );
}

function LessonCard({ card, onOpen }) {
  const m = card.module;
  const locked = !m || m.status === 'locked';
  const color = m?.color_theme || '#3B82F6';
  return (
    <button
      type="button"
      disabled={locked}
      onClick={() => !locked && onOpen(m.id)}
      className="glass-inner"
      style={{
        textAlign: 'left', padding: 16, borderRadius: 14, cursor: locked ? 'not-allowed' : 'pointer',
        borderLeft: `4px solid ${locked ? '#3F3F46' : color}`, opacity: locked ? 0.55 : 1,
        display: 'flex', flexDirection: 'column', gap: 8, minHeight: 132, transition: 'transform .15s',
      }}
      onMouseEnter={(e) => { if (!locked) e.currentTarget.style.transform = 'translateY(-3px)'; }}
      onMouseLeave={(e) => { e.currentTarget.style.transform = 'translateY(0)'; }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: '#A1A1AA' }}>
        <span style={{ fontSize: 16 }}>{SLOT_ICON[card.slot] || '📚'}</span>
        <span style={{ fontWeight: 700, color: '#E4E4E7' }}>{card.time}</span>
        <span style={{ marginLeft: 'auto', textTransform: 'capitalize' }}>{card.slot}</span>
      </div>
      {m ? (
        <>
          <div style={{ fontSize: 15, fontWeight: 700, color: '#FAFAFA', lineHeight: 1.3 }}>{m.title}</div>
          <div style={{ fontSize: 11, color: '#71717A' }}>{m.track_name}</div>
          <div style={{ marginTop: 'auto', display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 700, color: locked ? '#71717A' : color }}>
            {locked ? <><FiLock size={12} /> Locked</> :
              m.status === 'in_progress' ? <><FiPlay size={12} /> Continue</> :
              <><FiPlay size={12} /> Start lesson</>}
          </div>
        </>
      ) : (
        <div style={{ fontSize: 13, color: '#71717A', marginTop: 'auto' }}>All caught up here 🎉</div>
      )}
    </button>
  );
}

// A clean per-track card: progress bar + the one thing to do next.
function TrackProgressCard({ track, modules, onOpen }) {
  const mods = useMemo(
    () => modules.filter((m) => m.track_id === track.id).sort((a, b) => a.order_index - b.order_index),
    [modules, track.id]
  );
  const color = track.color_theme || '#3B82F6';
  const pct = Math.round((track.mastered_count / Math.max(track.module_count, 1)) * 100);
  const current = mods.find((m) => m.status === 'in_progress') || mods.find((m) => m.status === 'available');
  const next = current ? mods.find((m) => m.order_index > current.order_index && m.status !== 'mastered') : null;
  const allDone = track.module_count > 0 && track.mastered_count >= track.module_count;

  return (
    <div className="glass-inner" style={{ padding: 16, borderRadius: 14, borderTop: `3px solid ${color}`, display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ width: 10, height: 10, borderRadius: 3, background: color }} />
        <span style={{ fontSize: 13, fontWeight: 700, color: '#FAFAFA' }}>{track.name}</span>
        <span style={{ marginLeft: 'auto', fontSize: 11, color: '#71717A' }}>{track.mastered_count}/{track.module_count}</span>
      </div>
      <div>
        <div style={{ height: 8, background: '#161619', borderRadius: 4, overflow: 'hidden' }}>
          <div style={{ width: `${pct}%`, height: '100%', background: color, transition: 'width .4s' }} />
        </div>
        <div style={{ fontSize: 11, color: '#71717A', marginTop: 5 }}>{pct}% mastered</div>
      </div>
      {allDone ? (
        <div style={{ fontSize: 13, color: '#34D399', display: 'flex', alignItems: 'center', gap: 6, fontWeight: 600 }}>
          <FiCheckCircle size={14} /> Track complete
        </div>
      ) : current ? (
        <>
          <button type="button" onClick={() => onOpen(current.id)}
            style={{ textAlign: 'left', background: color, color: '#fff', border: 'none', borderRadius: 10, padding: '11px 14px', fontSize: 13, fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8, lineHeight: 1.3 }}>
            <FiPlay size={14} style={{ flexShrink: 0 }} />
            <span>{current.status === 'in_progress' ? 'Continue' : 'Start'}: {current.title}</span>
          </button>
          {next && (
            <div style={{ fontSize: 11, color: '#52525B', display: 'flex', alignItems: 'center', gap: 6 }}>
              <FiLock size={10} /> Up next: {next.title}
            </div>
          )}
        </>
      ) : (
        <div style={{ fontSize: 12, color: '#71717A', display: 'flex', alignItems: 'center', gap: 6 }}>
          <FiLock size={11} /> Finish a prerequisite to unlock this track.
        </div>
      )}
    </div>
  );
}

// GitHub-style contribution heatmap (26 weeks), shaded by minutes.
function Heatmap({ streak }) {
  const cells = streak?.heatmap || [];
  const weeks = [];
  for (let i = 0; i < cells.length; i += 7) weeks.push(cells.slice(i, i + 7));
  const activeDays = cells.filter((c) => c.active).length;
  const shade = (c) => {
    if (!c.active) return '#161619';
    const m = c.minutes || 0;
    if (m >= 45) return '#39D353';
    if (m >= 20) return '#26A641';
    if (m > 0) return '#006D32';
    return '#0E4429';
  };
  return (
    <div className="glass-card">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
        <span style={{ fontSize: 13, fontWeight: 700, color: '#FAFAFA' }}>Your activity</span>
        <span style={{ fontSize: 12, color: '#71717A' }}>Longest streak: <strong style={{ color: '#D4D4D8' }}>{streak?.longest_streak ?? 0}</strong> days</span>
      </div>
      <div role="img"
        aria-label={`Activity heatmap, last ${cells.length} days: ${activeDays} active. Longest streak ${streak?.longest_streak ?? 0} days.`}
        style={{ display: 'flex', gap: 3, overflowX: 'auto', paddingBottom: 6 }}>
        {weeks.map((week, wi) => (
          <div key={wi} style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {week.map((cell, di) => (
              <div key={di}
                title={`${cell.date}${cell.active ? ` · ${cell.minutes || 0} min` : ' · no activity'}`}
                style={{ width: 12, height: 12, borderRadius: 3, background: shade(cell) }} />
            ))}
          </div>
        ))}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginTop: 10, fontSize: 11, color: '#71717A' }}>
        <span>Less</span>
        {['#161619', '#0E4429', '#006D32', '#26A641', '#39D353'].map((cc) => (
          <span key={cc} style={{ width: 11, height: 11, borderRadius: 3, background: cc }} />
        ))}
        <span>More</span>
      </div>
    </div>
  );
}

function ProjectMiniCard({ project, onOpen }) {
  const brief = project.brief || {};
  const steps = brief.steps || [];
  const done = (project.completed_steps || []).length;
  const pct = steps.length ? Math.round((done / steps.length) * 100) : (project.status === 'graded' ? 100 : 0);
  const color = project.color_theme || '#3B82F6';
  return (
    <button type="button" onClick={() => onOpen(project)} className="glass-inner"
      style={{ textAlign: 'left', padding: 14, borderRadius: 12, cursor: 'pointer', display: 'flex', flexDirection: 'column', gap: 8, width: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontSize: 16 }}>{brief.submission_format === 'negotiation_sim' ? '🎤' : '🔨'}</span>
        <span style={{ fontSize: 14, fontWeight: 700, color: '#FAFAFA' }}>{brief.title || project.module_title}</span>
        {project.status === 'graded' && (
          <span style={{ marginLeft: 'auto', fontSize: 12, fontWeight: 700, color: (project.score || 0) >= 80 ? '#34D399' : '#FBBF24' }}>{project.score}%</span>
        )}
      </div>
      <div style={{ fontSize: 11, color: '#71717A' }}>{project.track_name}</div>
      <div style={{ height: 6, background: '#1A1A1F', borderRadius: 3, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, transition: 'width .3s' }} />
      </div>
    </button>
  );
}

function TestBanner({ upcoming, onStart, busy }) {
  if (!upcoming) return null;
  const next = upcoming.next;
  const info = upcoming[next] || {};
  const due = info.due;
  return (
    <div className="glass-card" style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap', borderColor: due ? 'rgba(251,191,36,0.35)' : '#27272A' }}>
      <FiTrendingUp size={22} style={{ color: due ? '#FBBF24' : '#60A5FA' }} />
      <div style={{ flex: 1, minWidth: 180 }}>
        <div style={{ fontSize: 14, fontWeight: 700, color: '#FAFAFA', textTransform: 'capitalize' }}>{next} review test</div>
        <div style={{ fontSize: 12, color: '#A1A1AA' }}>
          {due ? 'Due now — see where you stand across every track.'
               : `Next ${next} test in ${info.due_in_days} day${info.due_in_days === 1 ? '' : 's'}.`}
          {info.last_score != null && ` Last: ${info.last_score}%`}
        </div>
      </div>
      <button className="btn btn-primary" disabled={busy} onClick={() => onStart(next)}>
        {busy ? 'Building…' : due ? 'Take the test' : 'Take it early'}
      </button>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════
// Lesson view
// ════════════════════════════════════════════════════════════════

function LessonView({ moduleId, onClose, onProgress, onOpenProject }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [step, setStep] = useState(0);

  // quiz state
  const [choices, setChoices] = useState({});
  const [quizResult, setQuizResult] = useState(null);
  const [quizPassed, setQuizPassed] = useState(false);
  const [grading, setGrading] = useState(false);

  // explain-back state
  const [explainText, setExplainText] = useState('');
  const [verdict, setVerdict] = useState(null);
  const [attempts, setAttempts] = useState(0);
  const [checking, setChecking] = useState(false);
  const [mastered, setMastered] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const finishedRef = useRef(false);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const res = await titan.getLesson(moduleId);
        if (!alive) return;
        setData(res);
        setQuizPassed(!!res.quiz_passed);
        setMastered(!!res.mastered);
      } catch (e) { if (alive) setError(e.message || 'Could not load the lesson.'); }
      finally { if (alive) setLoading(false); }
    })();
    return () => { alive = false; };
  }, [moduleId]);

  const c = data?.content || {};
  const module = data?.module || {};

  const steps = useMemo(() => {
    const s = [
      { key: 'big_picture', label: 'Big picture' },
      { key: 'concept', label: 'The concept' },
      { key: 'history', label: 'Through history' },
      { key: 'modern', label: 'In your world' },
    ];
    const dg = c.diagram;
    if (dg && (dg.nodes?.length || dg.columns?.length)) s.push({ key: 'diagram', label: 'Visual' });
    if ((c.exercises || []).length) s.push({ key: 'exercises', label: 'Your exercise' });
    s.push({ key: 'quiz', label: 'Quiz' });
    s.push({ key: 'explain', label: 'Explain it back' });
    s.push({ key: 'done', label: 'Done' });
    return s;
  }, [c]);

  async function submitQuiz() {
    setGrading(true);
    try {
      const answers = (c.quiz || []).map((_, i) => choices[i]);
      const res = await titan.attempt(moduleId, answers);
      setQuizResult(res);
      if (res.passed_quiz) setQuizPassed(true);
    } catch (e) { setError(e.message || 'Could not grade the quiz.'); }
    finally { setGrading(false); }
  }

  async function submitExplain() {
    if (!explainText.trim()) return;
    setChecking(true);
    try {
      const res = await titan.explainBack(moduleId, explainText, attempts);
      setVerdict(res);
      setAttempts((a) => a + 1);
      if (res.module_mastered) setMastered(true);
    } catch (e) { setError(e.message || 'Could not run explain-back.'); }
    finally { setChecking(false); }
  }

  async function finishLesson() {
    if (finishedRef.current) return;  // idempotent — one check-in per lesson, no double-counting
    finishedRef.current = true;
    try { await titan.checkin(moduleId, 30); } catch (e) { console.warn('Streak check-in failed (best-effort):', e); }
    onProgress?.();
  }

  async function refreshLesson() {
    setRefreshing(true);
    setError('');
    try {
      const res = await titan.refreshLesson(moduleId);
      setData(res);
      setStep(0);
      setChoices({}); setQuizResult(null); setQuizPassed(!!res.quiz_passed);
      setExplainText(''); setVerdict(null); setAttempts(0); setMastered(!!res.mastered);
      finishedRef.current = false;  // new lesson → allow its completion to check in again
    } catch (e) {
      setError(e.message || 'Could not refresh this lesson.');
    } finally {
      setRefreshing(false);
    }
  }

  if (loading) {
    return <Overlay onClose={onClose}><div className="glass-card"><div className="skeleton" style={{ height: 320, borderRadius: 12 }} /></div></Overlay>;
  }
  if (error && !data) {
    return <Overlay onClose={onClose}><div className="glass-card" style={{ textAlign: 'center', padding: 30 }}>
      <p style={{ color: '#F87171', marginBottom: 12 }}>{error}</p>
      <button className="btn btn-ghost" onClick={onClose}>Close</button>
    </div></Overlay>;
  }

  const cur = steps[step];
  const pct = Math.round(((step + 1) / steps.length) * 100);
  const canAdvance = cur.key === 'quiz' ? quizPassed : true;

  return (
    <Overlay onClose={onClose}>
      <div className="glass-card" style={{ padding: 0, overflow: 'hidden' }}>
        {/* header + progress */}
        <div style={{ padding: '16px 20px', borderBottom: '1px solid #1E1E24' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
            <FiBookOpen style={{ color: '#60A5FA' }} />
            <span style={{ fontSize: 13, fontWeight: 700, color: '#FAFAFA' }}>{module.title}</span>
            <ConfidenceTag level={module.confidence_level} />
            {['available', 'in_progress'].includes(module.status) && (
              <button className="btn btn-ghost" style={{ marginLeft: 'auto', padding: '4px 8px', fontSize: 11 }}
                disabled={refreshing} onClick={refreshLesson} title="Ask the AI to re-author this lesson">
                <FiRefreshCw size={12} /> {refreshing ? 'Refreshing…' : 'Refresh'}
              </button>
            )}
            <button className="btn btn-ghost"
              style={{ marginLeft: ['available', 'in_progress'].includes(module.status) ? 0 : 'auto', padding: 6 }}
              onClick={onClose} aria-label="Close lesson"><FiX size={16} /></button>
          </div>
          <div style={{ height: 6, background: '#1A1A1F', borderRadius: 3, overflow: 'hidden' }}>
            <div style={{ width: `${pct}%`, height: '100%', background: '#60A5FA', transition: 'width .35s' }} />
          </div>
          <div style={{ fontSize: 11, color: '#71717A', marginTop: 6 }}>{cur.label} · {step + 1}/{steps.length}</div>
        </div>

        {/* body */}
        <div style={{ padding: '20px 24px', minHeight: 260 }}>
          {cur.key === 'big_picture' && (
            <Section title="Why this matters">
              <p style={pStyle}>{c.big_picture}</p>
            </Section>
          )}
          {cur.key === 'concept' && (
            <Section title="The concept">
              <p style={{ ...pStyle, whiteSpace: 'pre-wrap' }}>{c.concept}</p>
            </Section>
          )}
          {cur.key === 'history' && c.historical_example && (
            <Section title="Through history">
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 8 }}>
                <span style={{ fontSize: 17, fontWeight: 800, color: '#FAFAFA' }}>{c.historical_example.figure}</span>
                <span style={{ fontSize: 12, color: '#71717A' }}>{c.historical_example.era}</span>
              </div>
              <p style={pStyle}>{c.historical_example.story}</p>
              {c.historical_example.key_lesson && (
                <div className="glass-inner" style={{ padding: 12, marginTop: 12, borderLeft: '3px solid #A78BFA' }}>
                  <span style={{ fontSize: 11, color: '#A78BFA', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em' }}>The lesson</span>
                  <p style={{ ...pStyle, marginTop: 4 }}>{c.historical_example.key_lesson}</p>
                </div>
              )}
            </Section>
          )}
          {cur.key === 'modern' && (
            <Section title="In your world today">
              <p style={pStyle}>{c.modern_practice}</p>
            </Section>
          )}
          {cur.key === 'diagram' && (
            <Section title="The shape of it"><Diagram diagram={c.diagram} /></Section>
          )}
          {cur.key === 'exercises' && (
            <Section title="Your exercise">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {(c.exercises || []).map((ex, i) => (
                  <div key={i} className="glass-inner" style={{ padding: 12, display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                    <span style={{ fontSize: 13, fontWeight: 800, color: '#60A5FA' }}>{i + 1}</span>
                    <span style={{ ...pStyle, flex: 1 }}>{ex.task}</span>
                    <span style={{ fontSize: 11, color: '#71717A', display: 'flex', alignItems: 'center', gap: 4, flexShrink: 0 }}><FiClock size={11} />{ex.minutes}m</span>
                  </div>
                ))}
              </div>
            </Section>
          )}
          {cur.key === 'quiz' && (
            <Section title="Quick check">
              <LessonQuiz quiz={c.quiz} choices={choices} setChoices={setChoices} result={quizResult} />
              {!quizResult ? (
                <button className="btn btn-primary" style={{ marginTop: 14 }} disabled={(c.quiz || []).some((_, i) => choices[i] === undefined) || grading} onClick={submitQuiz}>
                  {grading ? 'Grading…' : 'Submit answers'}
                </button>
              ) : (
                <div className="glass-inner" style={{ marginTop: 14, padding: 12 }}>
                  <p style={{ fontSize: 14, fontWeight: 700, color: quizResult.passed_quiz ? '#34D399' : '#FBBF24' }}>
                    {quizResult.score}% — {quizResult.passed_quiz ? 'Passed! 🎉' : `Need ${quizResult.threshold}%`}
                  </p>
                  <p style={{ fontSize: 12, color: '#A1A1AA', marginTop: 4 }}>{quizResult.feedback}</p>
                  {!quizResult.passed_quiz && (
                    <button className="btn btn-ghost" style={{ marginTop: 10 }} onClick={() => { setQuizResult(null); setChoices({}); }}>
                      <FiRefreshCw size={13} /> Try again
                    </button>
                  )}
                </div>
              )}
            </Section>
          )}
          {cur.key === 'explain' && (
            <Section title="Explain it back">
              {!quizPassed ? (
                <p style={pStyle}>Pass the quiz first to unlock this step.</p>
              ) : mastered ? (
                <div className="glass-inner" style={{ padding: 14, borderLeft: '3px solid #34D399' }}>
                  <p style={{ fontSize: 14, fontWeight: 700, color: '#34D399' }}>✓ Mastered — you proved it in your own words.</p>
                </div>
              ) : (
                <>
                  <p style={{ ...pStyle, marginBottom: 10 }}>{c.explain_back_prompt}</p>
                  <textarea value={explainText} onChange={(e) => setExplainText(e.target.value)} rows={4}
                    placeholder="Explain the mechanism in your own words — not just the label."
                    style={taStyle} disabled={checking} />
                  {verdict && (
                    <div className="glass-inner" style={{ marginTop: 10, padding: 12, borderLeft: `3px solid ${verdict.passed ? '#34D399' : '#60A5FA'}` }}>
                      <p style={{ fontSize: 13, fontWeight: 700, color: verdict.passed ? '#34D399' : '#60A5FA' }}>
                        {verdict.passed ? '✓ Passed — concept mastered' : 'Not yet — keep going'}
                      </p>
                      {verdict.feedback && <p style={{ fontSize: 12, color: '#A1A1AA', marginTop: 4 }}>{verdict.feedback}</p>}
                      {!verdict.passed && verdict.follow_up_question && <p style={{ fontSize: 12, color: '#E4E4E7', marginTop: 8, fontStyle: 'italic' }}>↪ {verdict.follow_up_question}</p>}
                      {!verdict.passed && verdict.model_answer && <p style={{ fontSize: 12, color: '#A78BFA', marginTop: 8 }}>Model answer: {verdict.model_answer}</p>}
                    </div>
                  )}
                  {!verdict?.passed && (
                    <button className="btn btn-primary" style={{ marginTop: 10 }} disabled={!explainText.trim() || checking} onClick={submitExplain}>
                      {checking ? 'Checking…' : attempts === 0 ? 'Submit explanation' : 'Try again'}
                    </button>
                  )}
                </>
              )}
            </Section>
          )}
          {cur.key === 'done' && (
            <div style={{ textAlign: 'center', padding: '20px 0' }}>
              <div style={{ fontSize: 48, marginBottom: 8 }}>{mastered ? '🏆' : '✅'}</div>
              <h2 style={{ fontSize: 22, fontWeight: 800, color: '#FAFAFA', marginBottom: 6 }}>
                {mastered ? 'Module mastered!' : 'Lesson complete!'}
              </h2>
              <p style={{ fontSize: 13, color: '#A1A1AA', marginBottom: 18 }}>
                {mastered ? `+30 XP · ${c.citation || 'Grounded in the research.'}` : 'Pass the explain-back to master this module and earn 30 XP.'}
              </p>
              <div style={{ display: 'flex', gap: 10, justifyContent: 'center', flexWrap: 'wrap' }}>
                <button className="btn btn-primary" onClick={() => onOpenProject(module.id)}>
                  <FiTarget size={14} /> Open the project
                </button>
                <button className="btn btn-ghost" onClick={async () => { await finishLesson(); onClose(); }}>Back to dashboard</button>
              </div>
            </div>
          )}
          {error && <p role="alert" style={{ color: '#F87171', fontSize: 12, marginTop: 12 }}>{error}</p>}
        </div>

        {/* footer nav */}
        {cur.key !== 'done' && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '14px 20px', borderTop: '1px solid #1E1E24' }}>
            {step > 0 && <button className="btn btn-ghost" onClick={() => setStep((s) => s - 1)}><FiArrowLeft size={14} /> Back</button>}
            <button className="btn btn-primary" style={{ marginLeft: 'auto' }} disabled={!canAdvance}
              onClick={async () => { if (cur.key === 'explain') { await finishLesson(); } setStep((s) => Math.min(steps.length - 1, s + 1)); }}>
              {cur.key === 'quiz' && !quizPassed ? 'Pass the quiz to continue' : 'Next'} <FiArrowRight size={14} />
            </button>
          </div>
        )}
      </div>
    </Overlay>
  );
}

function Section({ title, children }) {
  return (
    <div>
      <h3 style={{ fontSize: 12, fontWeight: 700, color: '#71717A', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 12 }}>{title}</h3>
      {children}
    </div>
  );
}

// Accessible single-select option group: proper ARIA radiogroup with roving
// tabindex + arrow-key navigation (one tab stop per group).
function OptionRadios({ groupId, options, value, onPick, disabled, styleFor }) {
  const onKey = (e, oi) => {
    if (disabled) return;
    const n = options.length;
    let next = null;
    if (e.key === 'ArrowDown' || e.key === 'ArrowRight') next = (oi + 1) % n;
    else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') next = (oi - 1 + n) % n;
    if (next == null) return;
    e.preventDefault();
    onPick(next);
    const btns = e.currentTarget.parentElement.querySelectorAll('[role="radio"]');
    if (btns[next]) btns[next].focus();
  };
  return (
    <div role="radiogroup" aria-labelledby={groupId} style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {(options || []).map((opt, oi) => {
        const chosen = value === oi;
        const { border, bg } = styleFor
          ? styleFor(oi, chosen)
          : { border: chosen ? '#3B82F6' : '#27272A', bg: chosen ? 'rgba(59,130,246,0.08)' : 'transparent' };
        const focusable = value == null ? oi === 0 : chosen;
        return (
          <button key={oi} type="button" role="radio" aria-checked={chosen}
            aria-disabled={disabled || undefined} disabled={disabled}
            tabIndex={focusable ? 0 : -1}
            onKeyDown={(e) => onKey(e, oi)}
            onClick={() => !disabled && onPick(oi)}
            style={{ textAlign: 'left', padding: '9px 12px', borderRadius: 8, border: `1px solid ${border}`, background: bg, color: '#D4D4D8', fontSize: 13, cursor: disabled ? 'default' : 'pointer' }}>
            {opt}
          </button>
        );
      })}
    </div>
  );
}

function LessonQuiz({ quiz, choices, setChoices, result }) {
  if (!quiz?.length) return <p style={pStyle}>No quiz for this module.</p>;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {quiz.map((q, qi) => {
        const pq = result?.per_question?.[qi];
        return (
          <div key={qi} className="glass-inner" style={{ padding: 12 }}>
            <p id={`lq-${qi}`} style={{ fontSize: 14, color: '#E4E4E7', marginBottom: 8 }}>{qi + 1}. {q.question}</p>
            <OptionRadios
              groupId={`lq-${qi}`}
              options={q.options}
              value={choices[qi] ?? null}
              disabled={!!result}
              onPick={(oi) => setChoices((c) => ({ ...c, [qi]: oi }))}
              styleFor={(oi, chosen) => {
                let border = '#27272A', bg = 'transparent';
                if (pq) {
                  if (oi === pq.correct_index) { border = '#34D399'; bg = 'rgba(16,185,129,0.08)'; }
                  else if (chosen && !pq.is_correct) { border = '#F87171'; bg = 'rgba(239,68,68,0.08)'; }
                } else if (chosen) { border = '#3B82F6'; bg = 'rgba(59,130,246,0.08)'; }
                return { border, bg };
              }}
            />
            {pq?.explanation && <p style={{ fontSize: 12, color: pq.is_correct ? '#34D399' : '#FBBF24', marginTop: 6 }}>{pq.is_correct ? '✓ ' : '✗ '}{pq.explanation}</p>}
          </div>
        );
      })}
    </div>
  );
}

// ════════════════════════════════════════════════════════════════
// Project view
// ════════════════════════════════════════════════════════════════

function ProjectView({ moduleId, project: initial, onClose, onProgress, onStartNegotiation }) {
  const [project, setProject] = useState(initial || null);
  const [loading, setLoading] = useState(!initial);
  const [error, setError] = useState('');
  const [submission, setSubmission] = useState(initial?.submission_text || '');
  const [submitting, setSubmitting] = useState(false);
  const [grade, setGrade] = useState(initial?.ai_feedback && initial?.status === 'graded' ? initial.ai_feedback : null);

  useEffect(() => {
    if (initial) return;
    let alive = true;
    (async () => {
      try {
        const res = await titan.getModuleProject(moduleId);
        if (!alive) return;
        setProject(res);
        setSubmission(res.submission_text || '');
        if (res.status === 'graded') setGrade(res.ai_feedback);
      } catch (e) { if (alive) setError(e.message || 'Could not load the project.'); }
      finally { if (alive) setLoading(false); }
    })();
    return () => { alive = false; };
  }, [moduleId, initial]);

  const brief = project?.brief || {};
  const steps = brief.steps || [];
  const completed = new Set(project?.completed_steps || []);
  const isNegotiation = brief.submission_format === 'negotiation_sim';

  async function toggleStep(i) {
    const prev = project?.completed_steps || [];
    const next = new Set(prev);
    next.has(i) ? next.delete(i) : next.add(i);
    const arr = [...next];
    setError('');
    setProject((p) => ({ ...p, completed_steps: arr }));  // optimistic
    try {
      await titan.updateProjectProgress(project.id, arr);
    } catch (e) {
      setProject((p) => ({ ...p, completed_steps: prev }));  // server rejected → revert
      setError(e.message || "Couldn't save that step — it's been undone. Try again.");
    }
  }

  async function submit() {
    if (!submission.trim()) return;
    setSubmitting(true); setError('');
    try {
      const res = await titan.submitProject(project.id, submission);
      setGrade(res.grade);
      setProject((p) => ({ ...p, status: 'graded', score: res.grade?.score }));
      await titan.checkin(project.module_id, 60).catch((e) => console.warn('Streak check-in failed (best-effort):', e));
      onProgress?.();
    } catch (e) { setError(e.message || 'Could not submit the project.'); }
    finally { setSubmitting(false); }
  }

  if (loading) return <Overlay onClose={onClose}><div className="glass-card"><div className="skeleton" style={{ height: 300, borderRadius: 12 }} /></div></Overlay>;
  if (!project) return <Overlay onClose={onClose}><div className="glass-card" style={{ textAlign: 'center', padding: 30 }}><p style={{ color: '#F87171' }}>{error || 'Project unavailable.'}</p><button className="btn btn-ghost" style={{ marginTop: 12 }} onClick={onClose}>Close</button></div></Overlay>;

  return (
    <Overlay onClose={onClose}>
      <div className="glass-card">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
          <span style={{ fontSize: 22 }}>{isNegotiation ? '🎤' : '🔨'}</span>
          <span className="badge badge-info">Project</span>
          <span style={{ fontSize: 11, color: '#71717A' }}>{project.track_name} · ~{brief.estimated_hours || 2}h</span>
          <button className="btn btn-ghost" style={{ marginLeft: 'auto', padding: 6 }} onClick={onClose} aria-label="Close"><FiX size={16} /></button>
        </div>
        <h2 style={{ fontSize: 21, fontWeight: 800, color: '#FAFAFA', marginBottom: 8 }}>{brief.title}</h2>
        <p style={{ ...pStyle, marginBottom: 16 }}>{brief.description}</p>

        {isNegotiation ? (
          <div className="glass-inner" style={{ padding: 16, textAlign: 'center', borderLeft: '3px solid #EC4899' }}>
            <p style={{ ...pStyle, marginBottom: 12 }}>This one's live. You'll negotiate against an AI counterpart — name your ask and hold the line.</p>
            <button className="btn btn-primary" onClick={() => onStartNegotiation(project.module_id)}>
              <FiMessageCircle size={14} /> Start the simulation
            </button>
          </div>
        ) : (
          <>
            {/* steps */}
            <h3 style={{ fontSize: 12, fontWeight: 700, color: '#71717A', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10 }}>What you're building</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 16 }}>
              {steps.map((s, i) => {
                const isDone = completed.has(i);
                return (
                  <button key={i} type="button" onClick={() => toggleStep(i)} className="glass-inner"
                    role="checkbox" aria-checked={isDone}
                    aria-label={`${s.title}${isDone ? ' — completed' : ''}`}
                    style={{ textAlign: 'left', padding: 12, borderRadius: 10, cursor: 'pointer', display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                    <span style={{ width: 22, height: 22, borderRadius: 6, flexShrink: 0, border: `2px solid ${isDone ? '#34D399' : '#3F3F46'}`, background: isDone ? '#34D399' : 'transparent', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#0D0D0F' }}>
                      {isDone && <FiCheck size={14} />}
                    </span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 14, fontWeight: 600, color: isDone ? '#71717A' : '#FAFAFA', textDecoration: isDone ? 'line-through' : 'none' }}>{s.title}</div>
                      {s.detail && <div style={{ fontSize: 12, color: '#A1A1AA', marginTop: 2 }}>{s.detail}</div>}
                    </div>
                    {s.minutes && <span style={{ fontSize: 11, color: '#71717A', flexShrink: 0 }}>{s.minutes}m</span>}
                  </button>
                );
              })}
            </div>
            {error && <p role="alert" style={{ color: '#F87171', fontSize: 12, marginTop: -8, marginBottom: 12 }}>{error}</p>}

            {brief.starter_code && (
              <>
                <h3 style={{ fontSize: 12, fontWeight: 700, color: '#71717A', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>Starter code</h3>
                <pre style={{ background: '#0A0A0C', border: '1px solid #1E1E24', borderRadius: 10, padding: 14, overflowX: 'auto', fontSize: 12, color: '#D4D4D8', marginBottom: 16 }}>{brief.starter_code}</pre>
              </>
            )}

            {(brief.rubric || []).length > 0 && (
              <div className="glass-inner" style={{ padding: 12, marginBottom: 16 }}>
                <p style={{ fontSize: 11, color: '#71717A', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>How it's graded</p>
                {brief.rubric.map((r, i) => (
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#A1A1AA', padding: '2px 0' }}>
                    <span>{r.criterion}</span><span style={{ color: '#71717A' }}>{r.max_points} pts</span>
                  </div>
                ))}
              </div>
            )}

            {grade ? (
              <GradeCard grade={grade} onRetry={() => { setGrade(null); }} />
            ) : (
              <>
                <h3 style={{ fontSize: 12, fontWeight: 700, color: '#71717A', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>Your submission</h3>
                <textarea value={submission} onChange={(e) => setSubmission(e.target.value)} rows={8}
                  placeholder="Paste your code, write-up, or log here — then submit for AI review."
                  style={taStyle} disabled={submitting} />
                {error && <p role="alert" style={{ color: '#F87171', fontSize: 12, marginTop: 8 }}>{error}</p>}
                <button className="btn btn-primary" style={{ marginTop: 12 }} disabled={!submission.trim() || submitting} onClick={submit}>
                  {submitting ? 'Grading…' : <><FiSend size={14} /> Submit for AI review</>}
                </button>
              </>
            )}
          </>
        )}
      </div>
    </Overlay>
  );
}

function GradeCard({ grade, onRetry }) {
  const passed = grade.passed;
  return (
    <div className="glass-inner" style={{ padding: 16, borderLeft: `3px solid ${passed ? '#34D399' : '#FBBF24'}` }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
        <span style={{ fontSize: 28, fontWeight: 800, color: passed ? '#34D399' : '#FBBF24' }}>{grade.score}%</span>
        <span style={{ fontSize: 14, fontWeight: 700, color: passed ? '#34D399' : '#FBBF24' }}>{passed ? 'Passed 🎉' : 'Solid start'}</span>
      </div>
      {grade.summary && <p style={{ ...pStyle, marginBottom: 12 }}>{grade.summary}</p>}
      {(grade.strengths || []).length > 0 && (
        <div style={{ marginBottom: 10 }}>
          <p style={{ fontSize: 11, color: '#34D399', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>Strengths</p>
          <ul style={{ margin: 0, paddingLeft: 18 }}>{grade.strengths.map((s, i) => <li key={i} style={{ fontSize: 13, color: '#A1A1AA', marginBottom: 2 }}>{s}</li>)}</ul>
        </div>
      )}
      {(grade.improvements || []).length > 0 && (
        <div style={{ marginBottom: 10 }}>
          <p style={{ fontSize: 11, color: '#FBBF24', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>Make it better</p>
          <ul style={{ margin: 0, paddingLeft: 18 }}>{grade.improvements.map((s, i) => <li key={i} style={{ fontSize: 13, color: '#A1A1AA', marginBottom: 2 }}>{s}</li>)}</ul>
        </div>
      )}
      <button className="btn btn-ghost" style={{ marginTop: 6 }} onClick={onRetry}><FiRefreshCw size={13} /> Revise & resubmit</button>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════
// Negotiation view
// ════════════════════════════════════════════════════════════════

function NegotiationView({ moduleId, onClose, onProgress }) {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const res = await titan.startNegotiation(moduleId);
        if (alive) setSession(res);
      } catch (e) { if (alive) setError(e.message || 'Could not start the simulation.'); }
      finally { if (alive) setLoading(false); }
    })();
    return () => { alive = false; };
  }, [moduleId]);

  async function send() {
    if (!msg.trim() || busy) return;
    setBusy(true);
    const text = msg; setMsg('');
    try { setSession(await titan.negotiationRespond(session.id, text)); }
    catch (e) { setError(e.message || 'Could not send.'); }
    finally { setBusy(false); }
  }
  async function finish() {
    setBusy(true);
    try { setSession(await titan.finishNegotiation(session.id)); await titan.checkin(moduleId, 30).catch((e) => console.warn('Streak check-in failed (best-effort):', e)); onProgress?.(); }
    catch (e) { setError(e.message || 'Could not finish.'); }
    finally { setBusy(false); }
  }

  if (loading) return <Overlay onClose={onClose}><div className="glass-card"><div className="skeleton" style={{ height: 280, borderRadius: 12 }} /></div></Overlay>;
  if (!session) return <Overlay onClose={onClose}><div className="glass-card" style={{ textAlign: 'center', padding: 30 }}><p style={{ color: '#F87171' }}>{error}</p><button className="btn btn-ghost" style={{ marginTop: 12 }} onClick={onClose}>Close</button></div></Overlay>;

  const sc = session.scenario || {};
  const done = !!session.completed_at;
  const out = session.outcome;

  return (
    <Overlay onClose={onClose}>
      <div className="glass-card">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
          <span style={{ fontSize: 20 }}>🎤</span>
          <span style={{ fontSize: 13, fontWeight: 700, color: '#FAFAFA' }}>Negotiation sim</span>
          <button className="btn btn-ghost" style={{ marginLeft: 'auto', padding: 6 }} onClick={onClose} aria-label="Close"><FiX size={16} /></button>
        </div>
        <div className="glass-inner" style={{ padding: 12, marginBottom: 14, fontSize: 12, color: '#A1A1AA' }}>
          <div><strong style={{ color: '#E4E4E7' }}>You:</strong> {sc.role}</div>
          <div><strong style={{ color: '#E4E4E7' }}>Them:</strong> {sc.counterpart}</div>
          <div style={{ marginTop: 4 }}><strong style={{ color: '#E4E4E7' }}>Goal:</strong> {sc.objective}</div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxHeight: 320, overflowY: 'auto', marginBottom: 14 }}>
          {(session.rounds || []).map((r, i) => {
            const isUser = r.role === 'user';
            return (
              <div key={i} style={{ alignSelf: isUser ? 'flex-end' : 'flex-start', maxWidth: '82%' }}>
                <div style={{ fontSize: 10, color: '#71717A', marginBottom: 2, textAlign: isUser ? 'right' : 'left' }}>{isUser ? 'You' : (sc.counterpart || 'Counterpart')}</div>
                <div style={{ padding: '10px 14px', borderRadius: 12, fontSize: 13, lineHeight: 1.5,
                  background: isUser ? '#1E3A5F' : '#18181B', color: '#E4E4E7',
                  border: `1px solid ${isUser ? '#2563EB55' : '#27272A'}` }}>{r.text}</div>
              </div>
            );
          })}
        </div>

        {done ? (
          <div className="glass-inner" style={{ padding: 16, borderLeft: '3px solid #34D399' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
              <span style={{ fontSize: 26, fontWeight: 800, color: '#34D399' }}>{out?.score}</span>
              <span style={{ fontSize: 14, fontWeight: 700, color: '#FAFAFA' }}>Debrief</span>
            </div>
            <p style={{ ...pStyle, marginBottom: 10 }}>{out?.analysis}</p>
            {(out?.what_worked || []).length > 0 && <Bullets title="What worked" color="#34D399" items={out.what_worked} />}
            {(out?.what_cost_you || []).length > 0 && <Bullets title="What cost you" color="#FBBF24" items={out.what_cost_you} />}
            <button className="btn btn-primary" style={{ marginTop: 12 }} onClick={onClose}>Done</button>
          </div>
        ) : (
          <>
            <div style={{ display: 'flex', gap: 8 }}>
              <input value={msg} onChange={(e) => setMsg(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && send()}
                placeholder="Your move…" disabled={busy}
                style={{ flex: 1, background: '#0D0D0F', border: '1px solid #27272A', borderRadius: 10, padding: '10px 14px', color: '#E4E4E7', fontSize: 13 }} />
              <button className="btn btn-primary" disabled={!msg.trim() || busy} onClick={send}><FiSend size={14} /></button>
            </div>
            <button className="btn btn-ghost" style={{ marginTop: 10 }} disabled={busy || (session.rounds || []).length < 3} onClick={finish}>
              End & get my debrief
            </button>
            {error && <p role="alert" style={{ color: '#F87171', fontSize: 12, marginTop: 8 }}>{error}</p>}
          </>
        )}
      </div>
    </Overlay>
  );
}

function Bullets({ title, color, items }) {
  return (
    <div style={{ marginBottom: 8 }}>
      <p style={{ fontSize: 11, color, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>{title}</p>
      <ul style={{ margin: 0, paddingLeft: 18 }}>{items.map((s, i) => <li key={i} style={{ fontSize: 13, color: '#A1A1AA', marginBottom: 2 }}>{s}</li>)}</ul>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════
// Syllabus view
// ════════════════════════════════════════════════════════════════

function SyllabusView({ tracks, modules, onClose, onOpen }) {
  return (
    <Overlay onClose={onClose}>
      <div className="glass-card">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
          <FiList style={{ color: '#60A5FA' }} />
          <span style={{ fontSize: 16, fontWeight: 800, color: '#FAFAFA' }}>The full syllabus</span>
          <button className="btn btn-ghost" style={{ marginLeft: 'auto', padding: 6 }} onClick={onClose} aria-label="Close"><FiX size={16} /></button>
        </div>
        {tracks.map((t) => {
          const mods = modules.filter((m) => m.track_id === t.id).sort((a, b) => a.order_index - b.order_index);
          if (!mods.length) return null;
          return (
            <div key={t.id} style={{ marginBottom: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                <span style={{ width: 10, height: 10, borderRadius: 3, background: t.color_theme || '#3B82F6' }} />
                <span style={{ fontSize: 14, fontWeight: 700, color: '#FAFAFA' }}>{t.name}</span>
                <span style={{ fontSize: 11, color: '#71717A', marginLeft: 'auto' }}>{t.mastered_count}/{t.module_count}</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {mods.map((m) => {
                  const meta = STATUS_META[m.status] || STATUS_META.locked;
                  const here = m.status === 'in_progress';
                  const locked = m.status === 'locked';
                  return (
                    <button key={m.id} type="button" disabled={locked} onClick={() => !locked && onOpen(m.id)}
                      className="glass-inner" style={{ textAlign: 'left', padding: 12, borderRadius: 10, cursor: locked ? 'not-allowed' : 'pointer', opacity: locked ? 0.55 : 1, display: 'flex', alignItems: 'center', gap: 10, border: here ? '1px solid #FBBF2455' : undefined }}>
                      <span style={{ fontSize: 15, color: meta.color, width: 20, textAlign: 'center' }}>
                        {m.status === 'mastered' ? '✓' : m.status === 'locked' ? '🔒' : m.status === 'in_progress' ? '◐' : '○'}
                      </span>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: 13, fontWeight: 600, color: '#E4E4E7' }}>{m.title}</div>
                        {m.week_number && <div style={{ fontSize: 11, color: '#71717A' }}>Week {m.week_number}</div>}
                      </div>
                      {here && <span style={{ fontSize: 10, fontWeight: 700, color: '#FBBF24' }}>YOU ARE HERE</span>}
                      <ConfidenceTag level={m.confidence_level} />
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </Overlay>
  );
}

// ════════════════════════════════════════════════════════════════
// Test view
// ════════════════════════════════════════════════════════════════

function TestView({ test, trackNames, onClose, onProgress }) {
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const questions = test.questions || [];
  const answered = questions.length > 0 && questions.every((_, i) => answers[i] !== undefined);

  async function submit() {
    setSubmitting(true); setError('');
    try {
      const arr = questions.map((_, i) => answers[i]);
      const res = await titan.submitTest(test.id, arr);
      setResult(res);
      await titan.checkin(null, 20).catch((e) => console.warn('Streak check-in failed (best-effort):', e));
      onProgress?.();
    } catch (e) { setError(e.message || 'Could not grade the test.'); }
    finally { setSubmitting(false); }
  }

  return (
    <Overlay onClose={onClose}>
      <div className="glass-card">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
          <FiTrendingUp style={{ color: '#FBBF24' }} />
          <span style={{ fontSize: 16, fontWeight: 800, color: '#FAFAFA', textTransform: 'capitalize' }}>{test.type} review</span>
          <button className="btn btn-ghost" style={{ marginLeft: 'auto', padding: 6 }} onClick={onClose} aria-label="Close"><FiX size={16} /></button>
        </div>

        {result ? (
          <div>
            <div style={{ textAlign: 'center', marginBottom: 18 }}>
              <div style={{ fontSize: 44, fontWeight: 800, color: result.score_overall >= 70 ? '#34D399' : '#FBBF24' }}>{result.score_overall}%</div>
              <div style={{ fontSize: 13, color: '#A1A1AA' }}>{result.correct}/{result.total} correct</div>
            </div>
            <h3 style={{ fontSize: 12, fontWeight: 700, color: '#71717A', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10 }}>By track</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 18 }}>
              {Object.entries(result.scores_by_track || {}).map(([code, score]) => (
                <div key={code}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 3 }}>
                    <span style={{ color: '#E4E4E7' }}>{trackNames[code] || `Track ${code}`}</span>
                    <span style={{ color: score >= 80 ? '#34D399' : score >= 60 ? '#FBBF24' : '#F87171', fontWeight: 700 }}>
                      {score}% · {score >= 80 ? 'Strong' : score >= 60 ? 'Good' : 'Needs work'}
                    </span>
                  </div>
                  <div style={{ height: 8, background: '#1A1A1F', borderRadius: 4, overflow: 'hidden' }}>
                    <div style={{ width: `${score}%`, height: '100%', background: score >= 80 ? '#34D399' : score >= 60 ? '#FBBF24' : '#F87171' }} />
                  </div>
                </div>
              ))}
            </div>
            <details style={{ marginBottom: 12 }}>
              <summary style={{ fontSize: 12, color: '#60A5FA', cursor: 'pointer' }}>Review answers</summary>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 10 }}>
                {(result.per_question || []).map((pq, i) => (
                  <div key={i} className="glass-inner" style={{ padding: 10 }}>
                    <p style={{ fontSize: 12, color: '#E4E4E7', marginBottom: 4 }}>{i + 1}. {pq.question}</p>
                    <p style={{ fontSize: 12, color: pq.is_correct ? '#34D399' : '#F87171' }}>{pq.is_correct ? '✓ Correct' : '✗ Incorrect'} — {pq.explanation}</p>
                  </div>
                ))}
              </div>
            </details>
            <button className="btn btn-primary" onClick={onClose}>Done</button>
          </div>
        ) : (
          <>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {questions.map((q, qi) => (
                <div key={qi} className="glass-inner" style={{ padding: 12 }}>
                  <p id={`tq-${qi}`} style={{ fontSize: 14, color: '#E4E4E7', marginBottom: 8 }}>{qi + 1}. {q.question}</p>
                  <OptionRadios
                    groupId={`tq-${qi}`}
                    options={q.options}
                    value={answers[qi] ?? null}
                    onPick={(oi) => setAnswers((a) => ({ ...a, [qi]: oi }))}
                  />
                </div>
              ))}
            </div>
            {error && <p role="alert" style={{ color: '#F87171', fontSize: 12, marginTop: 10 }}>{error}</p>}
            <button className="btn btn-primary" style={{ marginTop: 14 }} disabled={!answered || submitting} onClick={submit}>
              {submitting ? 'Grading…' : 'Submit test'}
            </button>
          </>
        )}
      </div>
    </Overlay>
  );
}

// ════════════════════════════════════════════════════════════════
// Schedule settings
// ════════════════════════════════════════════════════════════════

function ScheduleSettings({ slots, trackOptions, onClose, onSave }) {
  const [local, setLocal] = useState(() => slots.map((s) => ({ ...s })));
  const [saving, setSaving] = useState(false);

  function update(i, key, val) { setLocal((l) => l.map((s, j) => (j === i ? { ...s, [key]: val } : s))); }
  async function save() { setSaving(true); try { await onSave(local); onClose(); } finally { setSaving(false); } }

  return (
    <Overlay onClose={onClose}>
      <div className="glass-card">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
          <FiSettings style={{ color: '#60A5FA' }} />
          <span style={{ fontSize: 16, fontWeight: 800, color: '#FAFAFA' }}>Your daily schedule</span>
          <button className="btn btn-ghost" style={{ marginLeft: 'auto', padding: 6 }} onClick={onClose} aria-label="Close"><FiX size={16} /></button>
        </div>
        <p style={{ ...pStyle, marginBottom: 16 }}>2–3 lessons a day, ~1 hour each. Pick your times and which track each slot leans toward.</p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {local.map((s, i) => (
            <div key={i} className="glass-inner" style={{ padding: 12, display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
              <span style={{ fontSize: 18 }}>{SLOT_ICON[s.slot] || '📚'}</span>
              <span style={{ fontSize: 13, fontWeight: 600, color: '#E4E4E7', textTransform: 'capitalize', width: 80 }}>{s.slot}</span>
              <input type="time" aria-label={`${s.slot} lesson time`} value={s.time} onChange={(e) => update(i, 'time', e.target.value)}
                style={{ background: '#0D0D0F', border: '1px solid #27272A', borderRadius: 8, padding: '7px 10px', color: '#E4E4E7', fontSize: 13 }} />
              <select aria-label={`${s.slot} track focus`} value={s.track_pref || ''} onChange={(e) => update(i, 'track_pref', e.target.value)}
                style={{ background: '#0D0D0F', border: '1px solid #27272A', borderRadius: 8, padding: '7px 10px', color: '#E4E4E7', fontSize: 13, flex: 1, minWidth: 140 }}>
                <option value="">Any track</option>
                {trackOptions.map((t) => <option key={t.code} value={t.code}>{t.name}</option>)}
              </select>
            </div>
          ))}
        </div>
        <button className="btn btn-primary" style={{ marginTop: 16 }} disabled={saving} onClick={save}>{saving ? 'Saving…' : 'Save schedule'}</button>
      </div>
    </Overlay>
  );
}

// ════════════════════════════════════════════════════════════════
// shared inline styles
// ════════════════════════════════════════════════════════════════
const pStyle = { fontSize: 14, color: '#D4D4D8', lineHeight: 1.7 };
const taStyle = { width: '100%', background: '#0D0D0F', border: '1px solid #27272A', borderRadius: 10, padding: 12, color: '#E4E4E7', fontSize: 13, resize: 'vertical', fontFamily: 'inherit' };

// ════════════════════════════════════════════════════════════════
// Main
// ════════════════════════════════════════════════════════════════

export default function TitanTrack() {
  const [dash, setDash] = useState(null);
  const [modules, setModules] = useState([]);
  const [projects, setProjects] = useState([]);
  const [tests, setTests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // overlays
  const [lessonModule, setLessonModule] = useState(null);
  const [projectCtx, setProjectCtx] = useState(null); // {moduleId} | {project}
  const [negotiationModule, setNegotiationModule] = useState(null);
  const [showSyllabus, setShowSyllabus] = useState(false);
  const [showSchedule, setShowSchedule] = useState(false);
  const [activeTest, setActiveTest] = useState(null);
  const [testBusy, setTestBusy] = useState(false);

  async function load() {
    try {
      const [d, mods, projs, hist] = await Promise.all([
        titan.getDashboard(),
        titan.getModules(),
        titan.getProjects().catch(() => []),
        titan.getTestHistory().catch(() => []),
      ]);
      setDash(d); setModules(mods); setProjects(projs); setTests(hist); setError('');
    } catch (e) {
      setError(e.message || 'Could not load Titan Track.');
    } finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);

  const nowTracks = dash?.now_tracks || [];
  const trackNames = useMemo(() => {
    const map = {};
    [...nowTracks, ...(dash?.horizon_tracks || [])].forEach((t) => { map[t.code] = t.name; });
    return map;
  }, [dash]);

  const xp = useMemo(() => {
    const mastered = modules.filter((m) => m.status === 'mastered').length;
    const streakDays = dash?.streak?.current_streak || 0;
    const projXp = projects.reduce((s, p) => s + (p.status === 'graded' ? ((p.score || 0) >= 80 ? 50 : 20) : 0), 0);
    const testXp = tests.reduce((s, t) => s + (t.submitted_at && (t.score_overall || 0) >= 70 ? (t.type === 'monthly' ? 75 : 30) : 0), 0);
    return mastered * 30 + streakDays * 10 + projXp + testXp;
  }, [modules, projects, tests, dash]);

  async function startTest(type) {
    setTestBusy(true);
    try {
      const t = await titan.generateTest(type);
      setActiveTest(t);
    } catch (e) { setError(e.message || 'Could not start the test.'); }
    finally { setTestBusy(false); }
  }

  async function saveSchedule(slots) {
    await titan.updateSchedulePreferences(slots);
    await load();
  }

  // ── open helpers ──
  const openLesson = (id) => { setShowSyllabus(false); setLessonModule(id); };
  const openProjectByModule = (id) => { setLessonModule(null); setProjectCtx({ moduleId: id }); };
  const openProject = (project) => {
    if (project.brief?.submission_format === 'negotiation_sim') { setNegotiationModule(project.module_id); }
    else setProjectCtx({ project });
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="skeleton" style={{ height: 96, borderRadius: 12 }} />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
          {[1, 2, 3].map((i) => <div key={i} className="skeleton" style={{ height: 132, borderRadius: 12 }} />)}
        </div>
        <div className="skeleton" style={{ height: 220, borderRadius: 12 }} />
      </div>
    );
  }
  if (error && !dash) {
    return (
      <div className="glass-card" style={{ textAlign: 'center', padding: 40 }}>
        <p style={{ color: '#F87171', marginBottom: 12 }}>{error}</p>
        <button className="btn btn-primary" onClick={load}><FiRefreshCw size={14} /> Retry</button>
      </div>
    );
  }

  const todayLessons = dash?.today_lessons || [];
  const activeProjects = projects.filter((p) => p.status === 'in_progress' || p.status === 'submitted');

  return (
    <div className="space-y-6">
      {/* Header: streak / XP / level */}
      <StatHeader streak={dash?.streak} xp={xp} onOpenSchedule={() => setShowSchedule(true)} />

      {/* Today's lessons */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: 12 }}>
          <h2 style={{ fontSize: 15, fontWeight: 800, color: '#FAFAFA' }}>Today's lessons</h2>
          <button className="btn btn-ghost" style={{ marginLeft: 'auto', fontSize: 12 }} onClick={() => setShowSyllabus(true)}>
            <FiList size={13} /> Full syllabus
          </button>
        </div>
        {todayLessons.length > 0 ? (
          <div style={{ display: 'grid', gridTemplateColumns: `repeat(${Math.max(todayLessons.length, 1)}, 1fr)`, gap: 14 }}>
            {todayLessons.map((card, i) => <LessonCard key={i} card={card} onOpen={openLesson} />)}
          </div>
        ) : (
          <button type="button" onClick={() => setShowSchedule(true)} className="glass-inner"
            style={{ width: '100%', textAlign: 'left', padding: 16, borderRadius: 14, cursor: 'pointer', color: '#A1A1AA', fontSize: 13, border: '1px dashed #2A2A30' }}>
            No lessons scheduled yet — tap to set your daily times, or pick a track below to start now.
          </button>
        )}
      </div>

      {/* Active projects */}
      {activeProjects.length > 0 && (
        <div>
          <h2 style={{ fontSize: 15, fontWeight: 800, color: '#FAFAFA', marginBottom: 12 }}>Active projects</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 12 }}>
            {activeProjects.map((p) => <ProjectMiniCard key={p.id} project={p} onOpen={openProject} />)}
          </div>
        </div>
      )}

      {/* Your tracks */}
      <div>
        <h2 style={{ fontSize: 15, fontWeight: 800, color: '#FAFAFA', marginBottom: 12 }}>Your tracks</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 14 }}>
          {nowTracks.map((t) => <TrackProgressCard key={t.id} track={t} modules={modules} onOpen={openLesson} />)}
        </div>
      </div>

      {/* Activity heatmap (GitHub-style) + next test */}
      <Heatmap streak={dash?.streak} />
      <TestBanner upcoming={dash?.upcoming_test} onStart={startTest} busy={testBusy} />

      {/* ── Overlays ── */}
      {lessonModule != null && (
        <LessonView key={lessonModule} moduleId={lessonModule} onClose={() => { setLessonModule(null); load(); }}
          onProgress={load} onOpenProject={openProjectByModule} />
      )}
      {projectCtx && (
        <ProjectView moduleId={projectCtx.moduleId} project={projectCtx.project}
          onClose={() => { setProjectCtx(null); load(); }} onProgress={load}
          onStartNegotiation={(id) => { setProjectCtx(null); setNegotiationModule(id); }} />
      )}
      {negotiationModule != null && (
        <NegotiationView moduleId={negotiationModule} onClose={() => { setNegotiationModule(null); load(); }} onProgress={load} />
      )}
      {showSyllabus && (
        <SyllabusView tracks={[...nowTracks, ...(dash?.horizon_tracks || [])]} modules={modules}
          onClose={() => setShowSyllabus(false)} onOpen={openLesson} />
      )}
      {showSchedule && (
        <ScheduleSettings slots={dash?.schedule?.slots || []} trackOptions={nowTracks}
          onClose={() => setShowSchedule(false)} onSave={saveSchedule} />
      )}
      {activeTest && (
        <TestView key={activeTest.id} test={activeTest} trackNames={trackNames}
          onClose={() => { setActiveTest(null); load(); }} onProgress={load} />
      )}
    </div>
  );
}
