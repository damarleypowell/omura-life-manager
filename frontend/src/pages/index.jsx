import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
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
import TitanTrack from '../components/Dashboard/TitanTrack';
import AgentInsights from '../components/Shared/AgentInsights';

// Which insights section to show under each tab (agent results land here, in English).
const INSIGHTS_SECTION = {
  business:      'business',
  communication: 'communication',
  content:       'content',
  health:        'health',
  scenarios:     'scenarios',
};

const SECTION_TITLES = {
  chat:          'AI Chat',
  outreach:      'Outreach Pipeline',
  business:      'Business Command',
  communication: 'Communication Center',
  life:          'Life Overview',
  content:       'Content Studio',
  knowledge:     'Knowledge Hub',
  automation:    'Automation Control',
  scenarios:     'Scenario Simulator',
  health:        'Health & Fitness',
  titan:         'Titan Track',
};

const SECTION_COMPONENTS = {
  chat:          ChatPage,
  outreach:      OutreachPipeline,
  business:      BusinessCommand,
  communication: CommunicationCenter,
  life:          LifeOverview,
  content:       ContentStudio,
  knowledge:     KnowledgeHub,
  automation:    AutomationControl,
  scenarios:     ScenarioSimulator,
  health:        HealthDashboard,
  titan:         TitanTrack,
};

export default function Dashboard() {
  const router = useRouter();
  // Titan Track is home — open Omura and the one thing to do now is right there,
  // no tab-hunting. (The chat is one click away via the floating bubble + sidebar.)
  const [activeSection, setActiveSection] = useState('titan');

  // Honor ?section=… so returning from the /settings page lands on the right tab.
  useEffect(() => {
    const s = router.query.section;
    if (s && SECTION_COMPONENTS[s]) setActiveSection(s);
  }, [router.query.section]);

  // 'settings' is a real page route, not an in-dashboard section — navigate to it
  // instead of resolving an undefined section component (which rendered blank).
  const handleNavigate = (section) => {
    if (section === 'settings') router.push('/settings');
    else setActiveSection(section);
  };

  const ActiveComponent = SECTION_COMPONENTS[activeSection];

  return (
    <div className="relative min-h-screen bg-[#09090B]">
      <div className="ambient-bg" />

      <div className="relative z-10 flex min-h-screen">
        <Sidebar activeSection={activeSection} onNavigate={handleNavigate} />

        <div className="flex-1 flex flex-col" style={{ marginLeft: '220px' }}>
          <Header
            title={SECTION_TITLES[activeSection] || 'Omura'}
            onNavigate={handleNavigate}
          />

          <main className="flex-1 p-6 space-y-6">
            {ActiveComponent && <ActiveComponent />}
            {INSIGHTS_SECTION[activeSection] && (
              <AgentInsights section={INSIGHTS_SECTION[activeSection]} />
            )}
          </main>
        </div>
      </div>

      {/* Floating chat bubble — hidden when on chat section */}
      {activeSection !== 'chat' && <ChatInterface />}
    </div>
  );
}
