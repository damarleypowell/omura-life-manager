/**
 * Omura Main Dashboard — Premium dark layout with ambient background.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { FiSettings } from 'react-icons/fi';
import Sidebar from '../components/Shared/Sidebar';
import Header from '../components/Shared/Header';
import ChatInterface, { ChatPage } from '../components/Shared/ChatInterface';
import LifeOverview from '../components/Dashboard/LifeOverview';
import BusinessCommand from '../components/Dashboard/BusinessCommand';
import ContentStudio from '../components/Dashboard/ContentStudio';
import CommunicationCenter from '../components/Dashboard/CommunicationCenter';
import KnowledgeHub from '../components/Dashboard/KnowledgeHub';
import AutomationControl from '../components/Dashboard/AutomationControl';
import ScenarioSimulator from '../components/Dashboard/ScenarioSimulator';
import HealthDashboard from '../components/Dashboard/HealthDashboard';
import OutreachPipeline from '../components/Dashboard/OutreachPipeline';
import { sync, communications, tasks } from '../services/apiService';
import { notifySuccess, notifyError } from '../components/Shared/Notifications';

const SECTION_TITLES = {
  life: 'Life Overview',
  business: 'Business Command',
  content: 'Content Studio',
  communication: 'Communication Center',
  knowledge: 'Knowledge Hub',
  automation: 'Automation Control',
  outreach: 'Outreach Pipeline',
  scenarios: 'Scenario Simulator',
  health: 'Health & Fitness',
  chat: 'AI Chat',
  settings: 'Settings',
};

const SECTION_COMPONENTS = {
  life: LifeOverview,
  business: BusinessCommand,
  content: ContentStudio,
  communication: CommunicationCenter,
  knowledge: KnowledgeHub,
  automation: AutomationControl,
  outreach: OutreachPipeline,
  scenarios: ScenarioSimulator,
  health: HealthDashboard,
  chat: ChatPage,
};

export default function Dashboard() {
  const [activeSection, setActiveSection]   = useState('life');
  const [syncing, setSyncing]               = useState(false);
  const [notifications, setNotifications]   = useState([]);

  // Load notification count from real data on mount and after syncs
  const loadNotifications = useCallback(async () => {
    const items = [];
    try {
      const unread = await communications.getUnread();
      if (Array.isArray(unread) && unread.length > 0) {
        items.push({
          type: 'info',
          message: `${unread.length} unread message${unread.length > 1 ? 's' : ''} in your inbox`,
          time: 'Just now',
          link: 'communication',
        });
      }
    } catch { /* non-critical */ }

    try {
      const overdue = await tasks.getOverdue();
      if (Array.isArray(overdue) && overdue.length > 0) {
        items.push({
          type: 'warning',
          message: `${overdue.length} overdue task${overdue.length > 1 ? 's' : ''} need attention`,
          time: 'Just now',
          link: 'business',
        });
      }
    } catch { /* non-critical */ }

    try {
      const urgent = await communications.getUrgent();
      if (Array.isArray(urgent) && urgent.length > 0) {
        items.push({
          type: 'error',
          message: `${urgent.length} urgent message${urgent.length > 1 ? 's' : ''} require action`,
          time: 'Just now',
          link: 'communication',
        });
      }
    } catch { /* non-critical */ }

    setNotifications(items);
  }, []);

  useEffect(() => { loadNotifications(); }, [loadNotifications]);

  async function handleSync() {
    setSyncing(true);
    try {
      await Promise.all([sync.emails(), sync.calendar(), sync.social()]);
      notifySuccess('All data synced successfully');
      await loadNotifications();
    } catch {
      notifyError('Sync failed — check your connections');
    } finally { setSyncing(false); }
  }

  function dismissNotification(idx) {
    setNotifications(prev => prev.filter((_, i) => i !== idx));
  }

  function dismissAllNotifications() {
    setNotifications([]);
  }

  const ActiveComponent = SECTION_COMPONENTS[activeSection];

  return (
    <div className="relative min-h-screen bg-[#06070A]">
      {/* Ambient background */}
      <div className="ambient-bg">
        <div className="orb orb-1" />
        <div className="orb orb-2" />
        <div className="orb orb-3" />
        <div className="orb orb-4" />
        <div className="noise" />
        <div className="dot-grid" />
      </div>

      <div className="relative z-10 flex min-h-screen">
        <Sidebar activeSection={activeSection} onNavigate={setActiveSection} />

        <div className="flex-1 ml-72">
          <Header
            title={SECTION_TITLES[activeSection] || 'Omura'}
            notifications={notifications}
            onDismissNotification={dismissNotification}
            onDismissAllNotifications={dismissAllNotifications}
            onNavigate={setActiveSection}
            onSync={handleSync}
            syncing={syncing}
          />

          <main className="p-8 pr-24">
            {ActiveComponent ? (
              <ActiveComponent />
            ) : (
              <div className="glass-card text-center py-24">
                <div className="empty-state">
                  <div className="empty-state-icon">
                    <FiSettings className="text-slate-600" size={20} />
                  </div>
                  <p>This section is under construction</p>
                </div>
              </div>
            )}
          </main>

          <footer className="px-8 py-5">
            <div className="h-px bg-gradient-to-r from-transparent via-white/[0.04] to-transparent mb-4" />
            <p className="text-[11px] text-slate-700 text-center tracking-wide">
              Omura Life Manager v1.0 &middot; Personal & Business Operating System
            </p>
          </footer>
        </div>

        <ChatInterface />
      </div>
    </div>
  );
}
