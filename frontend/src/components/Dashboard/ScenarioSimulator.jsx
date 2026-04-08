/**
 * Scenario Simulator — Type what you want to simulate. AI guides you through it.
 */

import React, { useState } from 'react';
import {
  FiTrendingUp, FiPlay, FiBarChart2, FiDollarSign, FiEdit3,
  FiHeart, FiArrowLeft, FiSave, FiZap,
} from 'react-icons/fi';
import { ai, scenarios as scenariosApi } from '../../services/apiService';
import { notifySuccess, notifyError } from '../Shared/Notifications';

// ── Scenario type detection from free text ──────────────────────────
const TYPE_PATTERNS = {
  business: /price|client|customer|churn|hire|service|charge|revenue|business|market|product|competitor|expand|growth/i,
  finance:  /invest|cash|burn|runway|expense|budget|cost|fund|roi|profit|loss|debt|loan|capital/i,
  content:  /post|content|tiktok|instagram|youtube|follower|engagement|viral|audience|creator|social|video/i,
  life:     /sleep|workout|exercise|meditation|health|energy|screen|diet|routine|habit|stress|focus|productivity/i,
};

const SCENARIO_TYPES = {
  business: {
    label: 'Business', icon: FiBarChart2, color: 'text-blue-400',
    fields: [
      { key: 'current_revenue',   label: 'Current monthly revenue ($)', type: 'number', placeholder: 'e.g. 15000' },
      { key: 'current_customers', label: 'Current number of clients',   type: 'number', placeholder: 'e.g. 50' },
      { key: 'price_change_pct',  label: 'Price change (%)',            type: 'number', placeholder: 'e.g. +20 or -10' },
      { key: 'new_clients',       label: 'Expected new clients/month',  type: 'number', placeholder: 'e.g. 5' },
      { key: 'churn_rate',        label: 'Current churn rate (%)',      type: 'number', placeholder: 'e.g. 5' },
    ],
  },
  finance: {
    label: 'Finance', icon: FiDollarSign, color: 'text-emerald-400',
    fields: [
      { key: 'current_revenue',    label: 'Monthly revenue ($)',       type: 'number', placeholder: 'e.g. 20000' },
      { key: 'current_expenses',   label: 'Monthly expenses ($)',      type: 'number', placeholder: 'e.g. 14000' },
      { key: 'cash_reserves',      label: 'Cash reserves ($)',         type: 'number', placeholder: 'e.g. 80000' },
      { key: 'revenue_change_pct', label: 'Revenue change (%)',        type: 'number', placeholder: 'e.g. -30 or +15' },
      { key: 'cost_cut_pct',       label: 'Cost reduction (%)',        type: 'number', placeholder: 'e.g. 15' },
      { key: 'investment_amount',  label: 'New investment ($)',        type: 'number', placeholder: 'e.g. 10000' },
    ],
  },
  content: {
    label: 'Content', icon: FiEdit3, color: 'text-amber-400',
    fields: [
      { key: 'current_followers',       label: 'Current followers',          type: 'number', placeholder: 'e.g. 5000' },
      { key: 'current_engagement_rate', label: 'Current engagement rate (%)', type: 'number', placeholder: 'e.g. 3.5' },
      { key: 'posting_frequency',       label: 'Posts per day',              type: 'number', placeholder: 'e.g. 2' },
      { key: 'content_type',            label: 'Content type',               type: 'text',   placeholder: 'short_video / carousel / image' },
      { key: 'platforms',               label: 'Platforms (comma-separated)', type: 'text',  placeholder: 'tiktok, instagram' },
    ],
  },
  life: {
    label: 'Life', icon: FiHeart, color: 'text-red-400',
    fields: [
      { key: 'current_energy_score', label: 'Current energy score (0-100)', type: 'number', placeholder: 'e.g. 60' },
      { key: 'sleep_hours',          label: 'Target sleep hours/night',     type: 'number', placeholder: 'e.g. 8' },
      { key: 'exercise_days',        label: 'Workout days/week',            type: 'number', placeholder: 'e.g. 5' },
      { key: 'meditation_minutes',   label: 'Meditation minutes/day',       type: 'number', placeholder: 'e.g. 10' },
      { key: 'screen_time_hours',    label: 'Screen time hours/day',        type: 'number', placeholder: 'e.g. 4' },
      { key: 'work_hours',           label: 'Work hours/day',               type: 'number', placeholder: 'e.g. 8' },
    ],
  },
};

const EXAMPLE_PROMPTS = [
  "What if I raise my service prices by 25% and lose 10% of clients?",
  "What happens if my revenue drops 30% — how long is my runway?",
  "If I post 3x per day on TikTok with $500 in ads, what's my growth?",
  "What if I sleep 8 hours and workout 5 days a week?",
  "What if I hire 2 people and expand to a new market?",
  "If I cut expenses 20% and invest $15k in marketing, what's the ROI?",
];

function extractParams(text, type) {
  const params = { scenario_description: text };
  const nums = [...text.matchAll(/[-+]?\d+\.?\d*/g)].map(m => parseFloat(m[0]));

  if (type === 'business') {
    const pct = text.match(/(\d+)\s*%/);
    if (pct) params.price_change_pct = parseFloat(pct[1]);
  }
  if (type === 'finance') {
    const dollarMatch = text.match(/\$\s*([\d,]+)/);
    if (dollarMatch) params.investment_amount = parseFloat(dollarMatch[1].replace(/,/g, ''));
    const pct = text.match(/(-?\d+)\s*%/);
    if (pct) params.revenue_change_pct = parseFloat(pct[1]);
  }
  if (type === 'content') {
    const freq = text.match(/(\d+)\s*[xX×]\s*(?:per day|daily|a day)/i);
    if (freq) params.posting_frequency = parseInt(freq[1]);
    const dollar = text.match(/\$\s*([\d,]+)/);
    if (dollar) params.ad_budget = parseFloat(dollar[1].replace(/,/g, ''));
    const platforms = [];
    if (/tiktok/i.test(text)) platforms.push('tiktok');
    if (/instagram/i.test(text)) platforms.push('instagram');
    if (/youtube/i.test(text)) platforms.push('youtube');
    if (platforms.length) params.platforms = platforms;
  }
  if (type === 'life') {
    const sleep = text.match(/(\d+\.?\d*)\s*h(?:ours?|rs?)\s*(?:of sleep|sleep)/i);
    if (sleep) params.sleep_hours = parseFloat(sleep[1]);
    const workout = text.match(/(\d+)\s*(?:days?|times?)\s*(?:a week|per week|weekly)/i);
    if (workout) params.exercise_days = parseInt(workout[1]);
  }
  return params;
}

function detectType(text) {
  for (const [type, pattern] of Object.entries(TYPE_PATTERNS)) {
    if (pattern.test(text)) return type;
  }
  return 'business';
}

// ── Result renderers ────────────────────────────────────────────────

function ResultSection({ title, children }) {
  return (
    <div className="glass-inner p-4">
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">{title}</p>
      {children}
    </div>
  );
}

function KVRow({ label, value }) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-white/[0.04] last:border-0">
      <span className="text-sm text-slate-400 capitalize">{String(label).replace(/_/g, ' ')}</span>
      <span className="text-sm font-semibold text-white">{String(value)}</span>
    </div>
  );
}

export default function ScenarioSimulator() {
  const [step, setStep]           = useState('describe'); // 'describe' | 'configure' | 'results'
  const [description, setDescription] = useState('');
  const [detectedType, setDetectedType] = useState('business');
  const [params, setParams]       = useState({});
  const [result, setResult]       = useState(null);
  const [running, setRunning]     = useState(false);
  const [savedId, setSavedId]     = useState(null);

  function handleAnalyze() {
    if (!description.trim()) return;
    const type = detectType(description);
    setDetectedType(type);
    const extracted = extractParams(description, type);
    setParams(extracted);
    setStep('configure');
  }

  function updateParam(key, value) {
    setParams(prev => ({ ...prev, [key]: value }));
  }

  async function runSimulation() {
    setRunning(true);
    setResult(null);
    try {
      const simParams = { ...params };
      // Convert comma-separated platforms to array
      if (typeof simParams.platforms === 'string') {
        simParams.platforms = simParams.platforms.split(',').map(s => s.trim()).filter(Boolean);
      }
      // Convert numeric strings
      for (const [k, v] of Object.entries(simParams)) {
        if (k !== 'scenario_description' && k !== 'platforms' && k !== 'content_type' && v !== '' && !isNaN(v)) {
          simParams[k] = parseFloat(v);
        }
      }

      const response = await ai.execute('scenario', `simulate_${detectedType}`, { params: simParams });
      setResult(response.result || response);
      setStep('results');
    } catch {
      notifyError('Simulation failed — make sure backend is running');
      setResult({
        error: true,
        recommendation: 'Could not connect to Omura AI. Check that the backend is running.',
        confidence: 0,
      });
      setStep('results');
    } finally { setRunning(false); }
  }

  async function saveScenario() {
    try {
      const saved = await scenariosApi.create({
        name: description.slice(0, 80),
        category: detectedType,
        parameters: params,
      });
      setSavedId(saved.id);
      notifySuccess('Scenario saved');
    } catch { notifyError('Failed to save scenario'); }
  }

  const typeConfig = SCENARIO_TYPES[detectedType];
  const TypeIcon   = typeConfig.icon;

  // ── Step 1: Describe ─────────────────────────────────────────────
  if (step === 'describe') {
    return (
      <div className="max-w-2xl mx-auto space-y-6">
        <div className="glass-card">
          <div className="flex items-center gap-3 mb-5">
            <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
              <FiTrendingUp className="text-blue-400" size={20} />
            </div>
            <div>
              <h3 className="font-bold text-white">Scenario Simulator</h3>
              <p className="text-xs text-slate-500">Describe what you want to simulate in plain English</p>
            </div>
          </div>

          <textarea
            rows={4}
            value={description}
            onChange={e => setDescription(e.target.value)}
            placeholder="What do you want to simulate? Be specific — the more detail you give, the better the results.&#10;&#10;e.g. &quot;What if I raise my consulting rates by 30% and add 3 new enterprise clients per month?&quot;"
            className="glass-input resize-none w-full text-sm leading-relaxed"
            onKeyDown={e => { if (e.key === 'Enter' && e.ctrlKey) handleAnalyze(); }}
          />

          <div className="flex items-center justify-between mt-4">
            <p className="text-xs text-slate-600">Press Ctrl+Enter or click Analyze</p>
            <button
              onClick={handleAnalyze}
              disabled={!description.trim()}
              className="btn btn-primary"
            >
              <FiZap size={14} /> Analyze Scenario
            </button>
          </div>
        </div>

        {/* Example prompts */}
        <div>
          <p className="text-xs text-slate-500 font-medium mb-3 uppercase tracking-wide">Example scenarios — click to use</p>
          <div className="grid grid-cols-2 gap-2">
            {EXAMPLE_PROMPTS.map((prompt, i) => (
              <button
                key={i}
                onClick={() => setDescription(prompt)}
                className="glass-inner text-left p-3 text-xs text-slate-400 hover:text-white hover:bg-white/[0.06] transition-all leading-relaxed"
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // ── Step 2: Configure ───────────────────────────────────────────
  if (step === 'configure') {
    return (
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3">
          <button onClick={() => setStep('describe')} className="btn btn-ghost text-xs">
            <FiArrowLeft size={13} /> Back
          </button>
          <div className="flex-1">
            <p className="text-xs text-slate-500">Simulating as</p>
            <div className="flex items-center gap-2">
              <TypeIcon className={typeConfig.color} size={15} />
              <span className="text-sm font-semibold text-white">{typeConfig.label} Scenario</span>
            </div>
          </div>
          {/* Type override pills */}
          <div className="flex gap-1">
            {Object.entries(SCENARIO_TYPES).map(([type, cfg]) => {
              const Ic = cfg.icon;
              return (
                <button
                  key={type}
                  onClick={() => setDetectedType(type)}
                  className={`w-8 h-8 rounded-lg flex items-center justify-center transition-all ${
                    detectedType === type ? 'bg-blue-500/20 border border-blue-500/30 text-blue-400' : 'btn btn-ghost text-xs p-0'
                  }`}
                  title={cfg.label}
                >
                  <Ic size={14} className={cfg.color} />
                </button>
              );
            })}
          </div>
        </div>

        {/* Scenario description review */}
        <div className="glass-card p-4 border-blue-500/20 bg-blue-500/[0.03]">
          <p className="text-xs text-blue-400 font-medium mb-1">Your scenario</p>
          <p className="text-sm text-slate-300 leading-relaxed">{description}</p>
        </div>

        {/* Parameter fields */}
        <div className="glass-card">
          <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
            <TypeIcon className={typeConfig.color} size={16} /> Fill in the numbers
            <span className="text-xs text-slate-500 font-normal ml-1">— leave blank to use smart defaults</span>
          </h3>
          <div className="grid grid-cols-2 gap-4">
            {typeConfig.fields.map((field) => (
              <div key={field.key}>
                <label className="block text-xs text-slate-400 mb-1">{field.label}</label>
                <input
                  type={field.type}
                  placeholder={field.placeholder}
                  value={params[field.key] ?? ''}
                  onChange={e => updateParam(field.key, e.target.value)}
                  className="glass-input"
                />
              </div>
            ))}
          </div>

          <button
            onClick={runSimulation}
            disabled={running}
            className="btn btn-primary hover-glow-purple w-full justify-center mt-6"
          >
            {running
              ? <><FiTrendingUp className="animate-spin" size={15} /> Running simulation...</>
              : <><FiPlay size={15} /> Run Simulation</>
            }
          </button>
        </div>
      </div>
    );
  }

  // ── Step 3: Results ─────────────────────────────────────────────
  if (step === 'results') {
    const projections = result?.projections || {};
    const hasError    = result?.error;

    return (
      <div className="max-w-3xl mx-auto space-y-5">
        {/* Header */}
        <div className="flex items-center gap-3">
          <button onClick={() => setStep('configure')} className="btn btn-ghost text-xs">
            <FiArrowLeft size={13} /> Adjust
          </button>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <TypeIcon className={typeConfig.color} size={15} />
              <span className="text-sm font-semibold text-white">{typeConfig.label} Simulation Results</span>
              {result?.scenario_id && (
                <span className="text-xs text-slate-600 font-mono">#{result.scenario_id}</span>
              )}
            </div>
            <p className="text-xs text-slate-500 truncate max-w-sm">{description}</p>
          </div>
          <div className="flex gap-2">
            {!savedId && !hasError && (
              <button onClick={saveScenario} className="btn btn-ghost text-xs">
                <FiSave size={13} /> Save
              </button>
            )}
            <button
              onClick={() => { setStep('describe'); setResult(null); setDescription(''); setParams({}); setSavedId(null); }}
              className="btn btn-primary text-xs"
            >
              <FiPlay size={13} /> New Simulation
            </button>
          </div>
        </div>

        {hasError ? (
          <div className="glass-card border-red-500/20 bg-red-500/[0.04]">
            <p className="text-red-400 font-medium mb-2">Simulation Error</p>
            <p className="text-sm text-slate-400">{result.recommendation}</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-5">
            {/* Projections */}
            {Object.keys(projections).length > 0 && (
              <ResultSection title="Projections">
                {Object.entries(projections).map(([k, v]) => (
                  <KVRow key={k} label={k} value={
                    typeof v === 'number'
                      ? k.includes('revenue') || k.includes('cost') || k.includes('flow') || k.includes('profit') || k.includes('burn') || k.includes('investment')
                        ? `$${v.toLocaleString()}`
                        : k.includes('pct') || k.includes('rate') || k.includes('change')
                          ? `${v > 0 ? '+' : ''}${v}%`
                          : v.toLocaleString()
                      : String(v)
                  } />
                ))}
              </ResultSection>
            )}

            {/* Confidence + Recommendation */}
            <div className="space-y-4">
              {result?.confidence != null && (
                <ResultSection title="Confidence">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-slate-400">AI confidence</span>
                    <span className="text-sm font-bold text-white">{Math.round(result.confidence * 100)}%</span>
                  </div>
                  <div className="w-full h-2 bg-white/[0.06] rounded-full overflow-hidden">
                    <div
                      className="h-2 rounded-full transition-all duration-700"
                      style={{
                        width: `${result.confidence * 100}%`,
                        background: result.confidence > 0.75
                          ? 'linear-gradient(90deg, #10B981, #22c55e)'
                          : result.confidence > 0.55
                            ? 'linear-gradient(90deg, #3B82F6, #60A5FA)'
                            : 'linear-gradient(90deg, #F59E0B, #FBBF24)',
                      }}
                    />
                  </div>
                </ResultSection>
              )}

              {/* Risk / warnings */}
              {(result?.risk_assessment || result?.warnings?.length > 0) && (
                <ResultSection title={result.risk_assessment ? 'Risk Assessment' : 'Warnings'}>
                  {result.risk_assessment && (
                    <>
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-xs text-slate-500">Overall risk</span>
                        <span className={`badge ${result.risk_assessment.overall_risk === 'low' ? 'badge-success' : result.risk_assessment.overall_risk === 'high' ? 'badge-danger' : 'badge-warning'}`}>
                          {result.risk_assessment.overall_risk}
                        </span>
                      </div>
                      {result.risk_assessment.key_risks?.slice(0, 2).map((r, i) => (
                        <p key={i} className="text-xs text-slate-400 mb-1">• {r}</p>
                      ))}
                    </>
                  )}
                  {result.warnings?.map((w, i) => (
                    <p key={i} className={`text-xs mb-1 ${w.severity === 'critical' ? 'text-red-400' : 'text-amber-400'}`}>
                      ⚠ {w.message}
                    </p>
                  ))}
                </ResultSection>
              )}
            </div>

            {/* Recommendation — full width */}
            {result?.recommendation && (
              <div className="col-span-2 glass-inner p-4 border-violet-500/10 bg-violet-500/5">
                <p className="text-xs text-violet-400 font-semibold mb-2 uppercase tracking-wide">AI Recommendation</p>
                <p className="text-sm text-slate-300 leading-relaxed">{result.recommendation}</p>
              </div>
            )}

            {/* Timeline if present */}
            {result?.timeline?.length > 0 && (
              <div className="col-span-2">
                <ResultSection title="Implementation Timeline">
                  <div className="space-y-2">
                    {result.timeline.map((phase, i) => (
                      <div key={i} className="flex items-start gap-3">
                        <div className="w-5 h-5 rounded-full bg-blue-500/20 border border-blue-500/30 flex items-center justify-center flex-shrink-0 mt-0.5">
                          <span className="text-[10px] font-bold text-blue-400">{i + 1}</span>
                        </div>
                        <div>
                          <p className="text-sm font-medium text-white">{phase.phase} <span className="text-xs text-slate-500 font-normal">({phase.duration})</span></p>
                          <p className="text-xs text-slate-400">{phase.action}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </ResultSection>
              </div>
            )}

            {/* Mitigation strategies */}
            {result?.risk_assessment?.mitigation_strategies?.length > 0 && (
              <div className="col-span-2">
                <ResultSection title="Mitigation Strategies">
                  {result.risk_assessment.mitigation_strategies.map((s, i) => (
                    <p key={i} className="text-xs text-slate-400 mb-1">✓ {s}</p>
                  ))}
                </ResultSection>
              </div>
            )}
          </div>
        )}
      </div>
    );
  }

  return null;
}
