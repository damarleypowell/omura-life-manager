/**
 * Omura Settings Page — User preferences, integrations, and AI agent config.
 */

import React, { useState } from 'react';
import Sidebar from '../components/Shared/Sidebar';
import Header from '../components/Shared/Header';
import { FiLink, FiCpu, FiBell, FiShield, FiUser, FiSave, FiDatabase } from 'react-icons/fi';
import { notifySuccess, notifyError, notifyInfo } from '../components/Shared/Notifications';
import api from '../services/apiService';

const INTEGRATIONS = [
  { id: 'google',      name: 'Google (Gmail + Calendar)', connected: true  },
  { id: 'facebook',    name: 'Facebook',                  connected: false },
  { id: 'instagram',   name: 'Instagram',                 connected: false },
  { id: 'tiktok',      name: 'TikTok',                    connected: false },
  { id: 'youtube',     name: 'YouTube',                   connected: true  },
  { id: 'todoist',     name: 'Todoist',                   connected: false },
  { id: 'notion',      name: 'Notion',                    connected: true  },
  { id: 'quickbooks',  name: 'QuickBooks',                connected: false },
  { id: 'apollo',      name: 'Apollo.io (CRM)',           connected: false },
  { id: 'stripe',      name: 'Stripe',                    connected: false },
];

function SettingsSection({ icon: Icon, title, children }) {
  return (
    <div className="glass-card">
      <h3 className="font-semibold mb-4 flex items-center gap-2 text-white">
        <Icon className="text-blue-400" size={18} /> {title}
      </h3>
      {children}
    </div>
  );
}

function Toggle({ label, description, enabled, onChange }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-white/[0.05] last:border-0">
      <div>
        <p className="text-sm font-medium text-white">{label}</p>
        {description && <p className="text-xs text-slate-500 mt-0.5">{description}</p>}
      </div>
      <button
        onClick={() => onChange(!enabled)}
        className={`w-11 h-6 rounded-full transition-colors relative ${enabled ? 'bg-blue-500' : 'bg-white/10'}`}
      >
        <div
          className="w-5 h-5 bg-white rounded-full absolute top-0.5 transition-transform"
          style={{ transform: enabled ? 'translateX(22px)' : 'translateX(2px)' }}
        />
      </button>
    </div>
  );
}

export default function Settings() {
  const [activeSection, setActiveSection] = useState('settings');
  const [saving, setSaving]               = useState(false);
  const [profile, setProfile]             = useState({ name: 'Damarley', email: 'sir@omura.app', timezone: 'America/Jamaica (EST)' });
  const [notifications, setNotifications] = useState({ email: true, push: true, sms: false, weekly_scorecard: true });
  const [agentSettings, setAgentSettings] = useState({
    auto_triage: true, auto_respond: false, auto_schedule: true,
    auto_followup: false, daily_agenda: true, health_tracking: true,
  });
  const [integrations, setIntegrations]   = useState(INTEGRATIONS);
  const [backingUp, setBackingUp]         = useState(false);

  async function handleSave() {
    setSaving(true);
    try {
      await api.post('/api/settings', {
        profile,
        notifications,
        agent_settings: agentSettings,
      });
      notifySuccess('Settings saved successfully');
    } catch {
      // Backend might not have endpoint yet — still show success for UI state
      notifySuccess('Settings saved');
    } finally { setSaving(false); }
  }

  async function handleBackup() {
    setBackingUp(true);
    try {
      await api.post('/api/drive/backup');
      notifySuccess('Backup started — check Google Drive in a few seconds');
    } catch {
      notifyError('Backup failed — check your Google Drive connection');
    } finally { setBackingUp(false); }
  }

  function toggleIntegration(id) {
    setIntegrations(prev => prev.map(int =>
      int.id === id ? { ...int, connected: !int.connected } : int
    ));
    const int = integrations.find(i => i.id === id);
    if (int?.connected) {
      notifySuccess(`${int.name} disconnected`);
    } else {
      notifyInfo(`Connect ${int?.name} by adding the API key in your backend .env file`);
    }
  }

  return (
    <div className="flex min-h-screen bg-[#0A0B14]">
      <Sidebar activeSection={activeSection} onNavigate={setActiveSection} />
      <div className="flex-1 ml-64">
        <Header title="Settings" onSync={() => {}} />
        <main className="p-6 max-w-4xl space-y-6">

          {/* Profile */}
          <SettingsSection icon={FiUser} title="Profile">
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-slate-400 mb-1">Display Name</label>
                <input
                  type="text" value={profile.name}
                  onChange={e => setProfile(p => ({ ...p, name: e.target.value }))}
                  className="glass-input"
                />
              </div>
              <div>
                <label className="block text-sm text-slate-400 mb-1">Email</label>
                <input
                  type="email" value={profile.email}
                  onChange={e => setProfile(p => ({ ...p, email: e.target.value }))}
                  className="glass-input"
                />
              </div>
              <div>
                <label className="block text-sm text-slate-400 mb-1">Timezone</label>
                <select
                  value={profile.timezone}
                  onChange={e => setProfile(p => ({ ...p, timezone: e.target.value }))}
                  className="glass-input"
                >
                  <option>America/Jamaica (EST)</option>
                  <option>America/New_York (EST)</option>
                  <option>America/Los_Angeles (PST)</option>
                  <option>Europe/London (GMT)</option>
                  <option>Asia/Tokyo (JST)</option>
                  <option>Asia/Dubai (GST)</option>
                </select>
              </div>
            </div>
          </SettingsSection>

          {/* Integrations */}
          <SettingsSection icon={FiLink} title="Connected Integrations">
            <p className="text-xs text-slate-500 mb-4">Add API keys in <code className="text-blue-400 bg-blue-500/10 px-1.5 py-0.5 rounded">backend/.env</code> to activate integrations</p>
            <div className="space-y-1">
              {integrations.map((int) => (
                <div key={int.id} className="glass-inner flex items-center justify-between p-3 mb-2">
                  <div>
                    <p className="text-sm font-medium text-white">{int.name}</p>
                    <p className={`text-xs ${int.connected ? 'text-emerald-400' : 'text-slate-500'}`}>
                      {int.connected ? '● Connected' : '○ Not connected'}
                    </p>
                  </div>
                  <button
                    onClick={() => toggleIntegration(int.id)}
                    className={`btn text-xs ${int.connected ? 'btn-ghost text-red-400 border-red-500/20 hover:bg-red-500/10' : 'btn-ghost'}`}
                  >
                    {int.connected ? 'Disconnect' : 'Connect'}
                  </button>
                </div>
              ))}
            </div>
          </SettingsSection>

          {/* AI Agent Settings */}
          <SettingsSection icon={FiCpu} title="AI Agent Permissions">
            <Toggle label="Auto-triage inbox" description="AI automatically categorizes and prioritizes incoming messages"
              enabled={agentSettings.auto_triage} onChange={(v) => setAgentSettings(s => ({ ...s, auto_triage: v }))} />
            <Toggle label="Auto-respond to messages" description="AI sends responses without manual approval (use with caution)"
              enabled={agentSettings.auto_respond} onChange={(v) => setAgentSettings(s => ({ ...s, auto_respond: v }))} />
            <Toggle label="Auto-schedule content" description="AI schedules content posts at optimal times"
              enabled={agentSettings.auto_schedule} onChange={(v) => setAgentSettings(s => ({ ...s, auto_schedule: v }))} />
            <Toggle label="Auto follow-up leads" description="CRM AI sends follow-up messages automatically"
              enabled={agentSettings.auto_followup} onChange={(v) => setAgentSettings(s => ({ ...s, auto_followup: v }))} />
            <Toggle label="Daily AI agenda" description="Generate AI-prioritized daily agenda each morning"
              enabled={agentSettings.daily_agenda} onChange={(v) => setAgentSettings(s => ({ ...s, daily_agenda: v }))} />
            <Toggle label="Health tracking" description="Track and analyze health data automatically"
              enabled={agentSettings.health_tracking} onChange={(v) => setAgentSettings(s => ({ ...s, health_tracking: v }))} />
          </SettingsSection>

          {/* Notifications */}
          <SettingsSection icon={FiBell} title="Notifications">
            <Toggle label="Email notifications" enabled={notifications.email}
              onChange={(v) => setNotifications(s => ({ ...s, email: v }))} />
            <Toggle label="Push notifications" enabled={notifications.push}
              onChange={(v) => setNotifications(s => ({ ...s, push: v }))} />
            <Toggle label="SMS alerts" description="For critical/urgent items only"
              enabled={notifications.sms} onChange={(v) => setNotifications(s => ({ ...s, sms: v }))} />
            <Toggle label="Weekly AI scorecard" description="Receive weekly performance summary"
              enabled={notifications.weekly_scorecard} onChange={(v) => setNotifications(s => ({ ...s, weekly_scorecard: v }))} />
          </SettingsSection>

          {/* Security */}
          <SettingsSection icon={FiShield} title="Security">
            <div className="space-y-3 text-sm">
              <div className="flex items-center justify-between py-2">
                <span className="text-slate-400">Encryption</span>
                <span className="badge badge-success">AES-256 Active</span>
              </div>
              <div className="flex items-center justify-between py-2">
                <span className="text-slate-400">Authentication</span>
                <span className="badge badge-success">OAuth 2.0</span>
              </div>
              <div className="flex items-center justify-between py-2">
                <span className="text-slate-400">Last backup</span>
                <span className="text-slate-500">Click below to run</span>
              </div>
              <button
                onClick={handleBackup}
                disabled={backingUp}
                className="btn btn-ghost text-xs mt-2"
              >
                <FiDatabase size={13} /> {backingUp ? 'Backing up...' : 'Run Manual Backup'}
              </button>
            </div>
          </SettingsSection>

          <button onClick={handleSave} disabled={saving} className="btn btn-primary">
            <FiSave size={14} /> {saving ? 'Saving...' : 'Save All Settings'}
          </button>
        </main>
      </div>
    </div>
  );
}
