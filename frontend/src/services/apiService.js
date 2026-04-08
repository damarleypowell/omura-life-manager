/**
 * Omura API Service
 * Central HTTP client for all backend communication.
 */

import axios from 'axios';

// Use relative URLs — Next.js rewrites in next.config.js proxy /api/* to the backend
const api = axios.create({
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// ── Request interceptor: attach auth token ──
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('omura_token');
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Response interceptor: handle errors ──
api.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const message = err.response?.data?.detail || err.message || 'Request failed';
    console.error('[Omura API]', message);
    return Promise.reject({ message, status: err.response?.status });
  }
);

// ══════════════════════════════════════
// Dashboard Aggregation
// ══════════════════════════════════════
export const dashboard = {
  getLifeOverview: () => api.get('/api/dashboard/life-overview'),
  getBusinessCommand: () => api.get('/api/dashboard/business-command'),
  getContentStudio: () => api.get('/api/dashboard/content-studio'),
  getCommunicationCenter: () => api.get('/api/dashboard/communication-center'),
};

// ══════════════════════════════════════
// Communications
// ══════════════════════════════════════
export const communications = {
  list: (params) => api.get('/api/communications', { params }),
  getUnread: (platform) => api.get('/api/communications/unread', { params: { platform } }),
  getFlagged: () => api.get('/api/communications/flagged'),
  getUrgent: () => api.get('/api/communications/urgent'),
  get: (id) => api.get(`/api/communications/${id}`),
  create: (data) => api.post('/api/communications', data),
  update: (id, data) => api.patch(`/api/communications/${id}`, data),
};

// ══════════════════════════════════════
// Projects
// ══════════════════════════════════════
export const projects = {
  list: (params) => api.get('/api/projects', { params }),
  getActive: () => api.get('/api/projects/active'),
  get: (id) => api.get(`/api/projects/${id}`),
  create: (data) => api.post('/api/projects', data),
  update: (id, data) => api.patch(`/api/projects/${id}`, data),
  delete: (id) => api.delete(`/api/projects/${id}`),
};

// ══════════════════════════════════════
// Tasks
// ══════════════════════════════════════
export const tasks = {
  list: (params) => api.get('/api/tasks', { params }),
  getToday: () => api.get('/api/tasks/today'),
  getOverdue: () => api.get('/api/tasks/overdue'),
  create: (data) => api.post('/api/tasks', data),
  update: (id, data) => api.patch(`/api/tasks/${id}`, data),
  delete: (id) => api.delete(`/api/tasks/${id}`),
};

// ══════════════════════════════════════
// Content
// ══════════════════════════════════════
export const content = {
  list: (params) => api.get('/api/content', { params }),
  getPipeline: () => api.get('/api/content/pipeline'),
  getScheduled: (platform) => api.get('/api/content/scheduled', { params: { platform } }),
  create: (data) => api.post('/api/content', data),
  update: (id, data) => api.patch(`/api/content/${id}`, data),
  delete: (id) => api.delete(`/api/content/${id}`),
};

// ══════════════════════════════════════
// Leads / CRM
// ══════════════════════════════════════
export const leads = {
  list: (params) => api.get('/api/leads', { params }),
  getHot: (minScore) => api.get('/api/leads/hot', { params: { min_score: minScore } }),
  getFollowups: () => api.get('/api/leads/followups'),
  create: (data) => api.post('/api/leads', data),
  update: (id, data) => api.patch(`/api/leads/${id}`, data),
};

// ══════════════════════════════════════
// Metrics
// ══════════════════════════════════════
export const metrics = {
  list: (params) => api.get('/api/metrics', { params }),
  getKPIs: (days) => api.get('/api/metrics/kpis', { params: { days } }),
  create: (data) => api.post('/api/metrics', data),
};

// ══════════════════════════════════════
// Health
// ══════════════════════════════════════
export const health = {
  list: (params) => api.get('/api/health', { params }),
  create: (data) => api.post('/api/health', data),
};

// ══════════════════════════════════════
// Calendar
// ══════════════════════════════════════
export const calendar = {
  list: (days) => api.get('/api/calendar', { params: { days } }),
  getToday: () => api.get('/api/calendar/today'),
  create: (data) => api.post('/api/calendar', data),
};

// ══════════════════════════════════════
// Notes
// ══════════════════════════════════════
export const notes = {
  list: (params) => api.get('/api/notes', { params }),
  create: (data) => api.post('/api/notes', data),
  update: (id, data) => api.patch(`/api/notes/${id}`, data),
  delete: (id) => api.delete(`/api/notes/${id}`),
};

// ══════════════════════════════════════
// Scenarios
// ══════════════════════════════════════
export const scenarios = {
  list: (params) => api.get('/api/scenarios', { params }),
  get: (id) => api.get(`/api/scenarios/${id}`),
  create: (data) => api.post('/api/scenarios', data),
};

// ══════════════════════════════════════
// AI Agents
// ══════════════════════════════════════
export const ai = {
  execute: (agent, action, params = {}) =>
    api.post('/api/ai/execute', { agent, action, params }),
  runWorkflow: (workflow, params = {}) =>
    api.post('/api/ai/workflow', { workflow, params }),
  getLogs: (agentName, limit) =>
    api.get('/api/agent-logs', { params: { agent_name: agentName, limit } }),
};

// ══════════════════════════════════════
// Email Sending
// ══════════════════════════════════════
export const email = {
  send: (to, subject, body, cc) => api.post('/api/email/send', { to, subject, body, cc }),
};

// ══════════════════════════════════════
// Chat (Omura AI) — legacy
// ══════════════════════════════════════
export const chat = {
  send: (message) => api.post('/api/chat', { message }),
  history: (limit = 50) => api.get('/api/chat/history', { params: { limit } }),
};

// ══════════════════════════════════════
// Conversations — multi-session chat
// ══════════════════════════════════════
export const conversations = {
  list: () => api.get('/api/conversations'),
  create: (title = 'New Conversation') => api.post('/api/conversations', { title }),
  delete: (id) => api.delete(`/api/conversations/${id}`),
  messages: (id) => api.get(`/api/conversations/${id}/messages`),
  chat: (id, message) => api.post(`/api/conversations/${id}/chat`, { message }),
};

// ══════════════════════════════════════
// Apollo.io — Lead Enrichment & CRM
// ══════════════════════════════════════
export const apollo = {
  search: (params) => api.get('/api/apollo/search', { params }),
  enrichPerson: (email) => api.get('/api/apollo/enrich/person', { params: { email } }),
  enrichCompany: (domain) => api.get('/api/apollo/enrich/company', { params: { domain } }),
  syncLead: (leadId) => api.post(`/api/apollo/sync-lead/${leadId}`),
  contacts: (q = '', page = 1, perPage = 25) =>
    api.get('/api/apollo/contacts', { params: { q, page, per_page: perPage } }),
};

// ══════════════════════════════════════
// Google Drive — Document Storage
// ══════════════════════════════════════
export const drive = {
  listFiles: (folder, q, pageSize = 25) =>
    api.get('/api/drive/files', { params: { folder, q, page_size: pageSize } }),
  getFile: (id) => api.get(`/api/drive/files/${id}`),
  folders: () => api.get('/api/drive/folders'),
  leadDocs: (leadName) => api.get(`/api/drive/lead/${encodeURIComponent(leadName)}/documents`),
  backup: () => api.post('/api/drive/backup'),
};

// ══════════════════════════════════════
// Sync
// ══════════════════════════════════════
export const sync = {
  emails: () => api.post('/api/sync/emails'),
  calendar: () => api.post('/api/sync/calendar'),
  social: () => api.post('/api/sync/social'),
};

// ══════════════════════════════════════
// Scheduler (Automation Jobs)
// ══════════════════════════════════════
export const scheduler = {
  jobs: () => api.get('/api/scheduler/jobs'),
  trigger: (jobId) => api.post(`/api/scheduler/trigger/${jobId}`),
};

// ══════════════════════════════════════
// Outreach Pipeline — Autonomous Lead Gen
// ══════════════════════════════════════
export const outreach = {
  runPipeline: (params = {}) => api.post('/api/outreach/run-pipeline', params),
  verifyEmail: (email) => api.post('/api/outreach/verify-email', { email }),
  sendInitial: (leadId) => api.post(`/api/outreach/send/${leadId}`),
  research: (data) => api.post('/api/outreach/research', data),
};

export default api;
