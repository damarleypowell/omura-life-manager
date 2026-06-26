/**
 * Automation Control — Active AI agents, task logs, workflow triggers.
 */

import React, { useState, useEffect } from 'react';
import { FiCpu, FiPlay, FiRefreshCw, FiActivity, FiCheckCircle, FiXCircle, FiClock } from 'react-icons/fi';
import { ai } from '../../services/apiService';
import { notifySuccess, notifyError } from '../Shared/Notifications';
import AgentInsights from '../Shared/AgentInsights';

const AGENTS = [
  {
    id: 'inbox',    name: 'Inbox AI',      color: 'text-red-400',
    description: 'Triage emails & DMs, summarize, suggest responses',
    action: 'process_inbox', params: {},
  },
  {
    id: 'content',  name: 'Content AI',    color: 'text-pink-400',
    description: 'Draft, edit, schedule posts and captions',
    action: 'suggest_content_ideas', params: { recent_trends: ['AI tools', 'productivity', 'business growth', 'automation'] },
  },
  {
    id: 'project',  name: 'Project AI',    color: 'text-blue-400',
    description: 'Manage pipeline, predict bottlenecks',
    action: 'analyze_pipeline', params: {},
  },
  {
    id: 'crm',      name: 'CRM AI',        color: 'text-green-400',
    description: 'Lead scoring, follow-ups, pipeline analysis',
    action: 'analyze_pipeline', params: {},
  },
  {
    id: 'finance',  name: 'Finance AI',    color: 'text-yellow-400',
    description: 'Track revenue, generate KPIs, detect anomalies',
    action: 'calculate_kpis', params: {},
  },
  {
    id: 'health',   name: 'Health AI',     color: 'text-emerald-400',
    description: 'Analyze sleep, workouts, supplements',
    action: 'generate_daily_recommendation', params: {},
  },
  {
    id: 'market',   name: 'Market AI',     color: 'text-cyan-400',
    description: 'Monitor competitors, trends, opportunities',
    action: 'monitor_competitors', params: { competitors: [] },
  },
  {
    id: 'scenario', name: 'Scenario AI',   color: 'text-purple-400',
    description: 'What-if simulations for business/life',
    action: 'simulate_business', params: { params: { scenario_description: 'Quick business health check' } },
  },
  {
    id: 'automation', name: 'Automation AI', color: 'text-orange-400',
    description: 'Execute repetitive tasks automatically',
    action: 'run_workflow', params: { workflow_name: 'business_metrics', params: {} },
  },
];

const WORKFLOWS = [
  { id: 'lead_management',   name: 'Lead Management',   description: 'Email → Triage → Score → Follow-up → Dashboard' },
  { id: 'content_publishing', name: 'Content Publishing', description: 'Idea → Draft → Schedule → Predict → Metrics' },
  { id: 'health_optimization', name: 'Health Optimization', description: 'Data → Analyze → Adjust → Energy Score' },
  { id: 'business_metrics',  name: 'Business Metrics',  description: 'Revenue → KPIs → Alerts → Optimizations' },
];

// Renders a run result as a plain-English brief (the backend returns `summary`).
function ResultView({ result }) {
  if (!result) return null;
  const summary = (typeof result === 'object' && result.summary)
    ? result.summary
    : (typeof result === 'string' ? result : '');
  if (!summary) {
    return <p className="text-[11px] text-emerald-400/80 mt-2">✓ Done</p>;
  }
  return (
    <div className="mt-2 rounded-lg bg-black/30 border border-white/[0.08] p-2.5">
      <p className="text-xs text-slate-300 whitespace-pre-wrap leading-relaxed">{summary}</p>
    </div>
  );
}

function AgentCard({ agent, onRun }) {
  const [status, setStatus] = useState('idle');
  const [lastResult, setLastResult] = useState(null);

  async function handleRun() {
    setStatus('running');
    try {
      const result = await onRun(agent.id, agent.action, agent.params);
      setLastResult(result);
      setStatus('success');
      setTimeout(() => setStatus('idle'), 3000);
    } catch {
      setStatus('error');
      setTimeout(() => setStatus('idle'), 3000);
    }
  }

  return (
    <div className="glass-inner p-4 hover:bg-white/[0.06] transition-all">
      <div className="flex items-center gap-3 mb-2">
        <FiCpu className={agent.color} size={18} />
        <h4 className="text-sm font-semibold text-white flex-1">{agent.name}</h4>
        <div className="flex items-center gap-1.5">
          <div className={`w-2 h-2 rounded-full ${
            status === 'running' ? 'bg-blue-400 animate-pulse' :
            status === 'success' ? 'bg-emerald-400' :
            status === 'error'   ? 'bg-red-400' : 'bg-slate-600'
          }`} />
          <span className={`badge ${
            status === 'running' ? 'badge-accent' :
            status === 'success' ? 'badge-success' :
            status === 'error'   ? 'badge-danger' : 'badge-info'
          }`}>
            {status}
          </span>
        </div>
      </div>
      <p className="text-xs text-slate-400 mb-3">{agent.description}</p>
      <button
        onClick={handleRun}
        className="btn btn-ghost text-xs w-full justify-center"
        disabled={status === 'running'}
      >
        {status === 'running'
          ? <><FiRefreshCw size={13} className="animate-spin" /> Running...</>
          : <><FiPlay size={13} /> Run Agent</>
        }
      </button>
      {status === 'error' && (
        <p className="text-[11px] text-red-400 mt-2">✗ Failed — check the activity log.</p>
      )}
      {lastResult && <ResultView result={lastResult} />}
    </div>
  );
}

export default function AutomationControl() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [runningWorkflow, setRunningWorkflow] = useState(null);
  const [workflowResults, setWorkflowResults] = useState({});
  const [lastRefresh, setLastRefresh] = useState(null);

  useEffect(() => {
    loadLogs();
    // Auto-refresh every 10 seconds to show live agent activity
    const interval = setInterval(loadLogs, 10000);
    return () => clearInterval(interval);
  }, []);

  async function loadLogs() {
    try {
      const result = await ai.getLogs(undefined, 30);
      setLogs(Array.isArray(result) ? result : []);
    } catch {
      setLogs([]);
    } finally {
      setLoading(false);
      setLastRefresh(new Date());
    }
  }

  async function handleRunAgent(agentId, action, params) {
    const result = await ai.execute(agentId, action, params);
    await loadLogs();
    notifySuccess(`${agentId} agent ran successfully`);
    return result;
  }

  async function handleRunWorkflow(workflowId) {
    setRunningWorkflow(workflowId);
    try {
      const res = await ai.runWorkflow(workflowId, {});
      setWorkflowResults((prev) => ({ ...prev, [workflowId]: res }));
      await loadLogs();
      notifySuccess(`Workflow "${workflowId}" completed`);
    } catch {
      notifyError(`Workflow "${workflowId}" failed`);
    } finally { setRunningWorkflow(null); }
  }

  if (loading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div>
          <div className="flex items-center gap-2 mb-4">
            <div className="skeleton w-5 h-5 rounded" />
            <div className="skeleton w-24 h-5 rounded" />
          </div>
          <div className="grid grid-cols-3 gap-4">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="glass-inner p-4">
                <div className="flex items-center gap-3 mb-2">
                  <div className="skeleton w-5 h-5 rounded" />
                  <div className="skeleton w-20 h-4 rounded flex-1" />
                  <div className="skeleton w-12 h-5 rounded-full" />
                </div>
                <div className="skeleton w-full h-3 rounded mb-3" />
                <div className="skeleton w-full h-9 rounded-xl" />
              </div>
            ))}
          </div>
        </div>
        <div className="glass-card">
          <div className="skeleton w-40 h-5 rounded mb-4" />
          <div className="grid grid-cols-2 gap-4">
            {[1, 2, 3, 4].map((i) => <div key={i} className="skeleton w-full h-20 rounded-xl" />)}
          </div>
        </div>
        <div className="glass-card">
          <div className="skeleton w-36 h-5 rounded mb-4" />
          {[1, 2, 3].map((i) => <div key={i} className="skeleton w-full h-10 rounded-lg mb-2" />)}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Agent Grid */}
      <div>
        <h3 className="font-semibold mb-4 flex items-center gap-2 text-white">
          <FiCpu className="text-blue-400" /> AI Agents
        </h3>
        <div className="grid grid-cols-3 gap-4">
          {AGENTS.map((agent) => (
            <AgentCard key={agent.id} agent={agent} onRun={handleRunAgent} />
          ))}
        </div>
      </div>

      {/* Workflows */}
      <div className="glass-card">
        <h3 className="font-semibold mb-4 flex items-center gap-2 text-white">
          <FiActivity className="text-violet-400" /> Automation Workflows
        </h3>
        <div className="grid grid-cols-2 gap-4">
          {WORKFLOWS.map((wf) => (
            <div key={wf.id} className="glass-inner p-4 hover:bg-white/[0.06] transition-all">
              <div className="flex items-center gap-4">
                <div className="flex-1">
                  <p className="text-sm font-medium text-white">{wf.name}</p>
                  <p className="text-xs text-slate-400 mt-1">{wf.description}</p>
                </div>
                <button
                  onClick={() => handleRunWorkflow(wf.id)}
                  disabled={runningWorkflow === wf.id}
                  className="btn btn-primary text-xs"
                >
                  {runningWorkflow === wf.id
                    ? <><FiRefreshCw size={13} className="animate-spin" /> Running</>
                    : <><FiPlay size={13} /> Run</>
                  }
                </button>
              </div>
              {workflowResults[wf.id] && <ResultView result={workflowResults[wf.id]} />}
            </div>
          ))}
        </div>
      </div>

      {/* Plain-English results from every agent run */}
      <AgentInsights title="Latest AI results (plain English)" limit={8} />

      {/* Logs */}
      <div className="glass-card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold flex items-center gap-2 text-white">
            <FiClock className="text-blue-400" /> Recent Activity Log
            <span className="flex items-center gap-1 ml-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-[10px] text-emerald-400/70 font-normal">live</span>
            </span>
          </h3>
          <div className="flex items-center gap-2">
            {lastRefresh && (
              <span className="text-[10px] text-slate-600">
                updated {lastRefresh.toLocaleTimeString()}
              </span>
            )}
            <button onClick={loadLogs} className="btn btn-ghost text-xs">
              <FiRefreshCw size={13} /> Refresh
            </button>
          </div>
        </div>
        {logs.length > 0 ? (
          <div className="space-y-1">
            {logs.map((log, i) => (
              <div key={i} className="glass-inner flex items-center gap-3 py-2.5 px-3 mb-1 text-sm">
                {log.status === 'success'
                  ? <FiCheckCircle className="text-emerald-400 flex-shrink-0" size={14} />
                  : <FiXCircle className="text-red-400 flex-shrink-0" size={14} />
                }
                <span className="badge badge-accent text-xs">{log.agent_name}</span>
                <span className="text-slate-400 flex-1 font-mono text-xs truncate">{log.action}</span>
                {log.duration_ms && <span className="text-xs text-slate-500 font-mono">{log.duration_ms}ms</span>}
                <span className="text-xs text-slate-600">{log.created_at ? new Date(log.created_at).toLocaleTimeString() : ''}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-10">
            <div className="w-14 h-14 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center mx-auto mb-4">
              <FiClock className="text-blue-400/60" size={22} />
            </div>
            <p className="text-sm font-medium text-slate-400">No activity yet</p>
            <p className="text-xs text-slate-600 mt-1">Run an agent or workflow to see logs here</p>
          </div>
        )}
      </div>
    </div>
  );
}
