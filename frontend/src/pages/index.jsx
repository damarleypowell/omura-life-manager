import React, { useState } from 'react';
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
};

export default function Dashboard() {
  const [activeSection, setActiveSection] = useState('chat');

  const ActiveComponent = SECTION_COMPONENTS[activeSection];

  return (
    <div className="relative min-h-screen bg-[#09090B]">
      <div className="ambient-bg" />

      <div className="relative z-10 flex min-h-screen">
        <Sidebar activeSection={activeSection} onNavigate={setActiveSection} />

        <div className="flex-1 flex flex-col" style={{ marginLeft: '220px' }}>
          <Header
            title={SECTION_TITLES[activeSection] || 'Omura'}
            onNavigate={setActiveSection}
          />

          <main className="flex-1 p-6">
            {ActiveComponent && <ActiveComponent />}
          </main>
        </div>
      </div>

      {/* Floating chat bubble — hidden when on chat section */}
      {activeSection !== 'chat' && <ChatInterface />}
    </div>
  );
}
