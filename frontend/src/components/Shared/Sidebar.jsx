import React from 'react';
import {
  FiMessageCircle, FiTarget, FiBriefcase, FiMessageSquare,
  FiHome, FiEdit3, FiBook, FiCpu, FiTrendingUp, FiActivity,
  FiSettings, FiLogOut,
} from 'react-icons/fi';
import { logout } from '../../services/authService';

const NAV_ITEMS = [
  { id: 'chat',          label: 'AI Chat',             icon: FiMessageCircle },
  { id: 'outreach',      label: 'Outreach',            icon: FiTarget },
  { id: 'business',      label: 'Business',            icon: FiBriefcase },
  { id: 'communication', label: 'Inbox',               icon: FiMessageSquare },
  { id: 'life',          label: 'Life Overview',       icon: FiHome },
  { id: 'content',       label: 'Content',             icon: FiEdit3 },
  { id: 'knowledge',     label: 'Knowledge',           icon: FiBook },
  { id: 'automation',    label: 'Automation',          icon: FiCpu },
  { id: 'scenarios',     label: 'Scenarios',           icon: FiTrendingUp },
  { id: 'health',        label: 'Health',              icon: FiActivity },
];

export default function Sidebar({ activeSection, onNavigate }) {
  return (
    <aside
      className="fixed left-0 top-0 h-screen z-50 flex flex-col"
      style={{
        width: '220px',
        background: '#0D0D0F',
        borderRight: '1px solid #1E1E24',
      }}
    >
      {/* Logo */}
      <div style={{ padding: '20px 16px 16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '32px', height: '32px', borderRadius: '8px',
            background: 'linear-gradient(135deg, #2563EB, #7C3AED)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0,
          }}>
            <span style={{ color: 'white', fontWeight: 800, fontSize: '14px' }}>O</span>
          </div>
          <div>
            <div style={{ fontSize: '15px', fontWeight: 700, color: '#FAFAFA', letterSpacing: '-0.02em' }}>Omura</div>
            <div style={{ fontSize: '10px', color: '#52525B', letterSpacing: '0.08em', textTransform: 'uppercase' }}>Life OS</div>
          </div>
        </div>
        <div style={{ marginTop: '16px', height: '1px', background: '#1E1E24' }} />
      </div>

      {/* Navigation */}
      <nav style={{ flex: 1, overflowY: 'auto', padding: '4px 8px' }}>
        <div style={{ fontSize: '10px', color: '#3F3F46', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 600, padding: '4px 8px 8px' }}>
          Menu
        </div>
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = activeSection === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                padding: '8px 10px',
                borderRadius: '6px',
                fontSize: '13px',
                fontWeight: isActive ? 500 : 400,
                color: isActive ? '#FAFAFA' : '#71717A',
                background: isActive ? '#18181B' : 'transparent',
                border: isActive ? '1px solid #27272A' : '1px solid transparent',
                cursor: 'pointer',
                textAlign: 'left',
                marginBottom: '1px',
                transition: 'color 0.1s, background 0.1s',
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  e.currentTarget.style.color = '#D4D4D8';
                  e.currentTarget.style.background = '#18181B';
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  e.currentTarget.style.color = '#71717A';
                  e.currentTarget.style.background = 'transparent';
                }
              }}
            >
              {isActive && (
                <div style={{
                  position: 'absolute',
                  left: '8px',
                  width: '2px',
                  height: '14px',
                  background: '#3B82F6',
                  borderRadius: '2px',
                }} />
              )}
              <Icon size={15} style={{ flexShrink: 0, marginLeft: isActive ? '8px' : '0' }} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Bottom */}
      <div style={{ padding: '8px 8px 16px', borderTop: '1px solid #1E1E24' }}>
        <button
          onClick={() => onNavigate('settings')}
          style={{
            width: '100%', display: 'flex', alignItems: 'center', gap: '10px',
            padding: '8px 10px', borderRadius: '6px', fontSize: '13px',
            color: '#52525B', background: 'transparent', border: '1px solid transparent',
            cursor: 'pointer', marginBottom: '1px',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.color = '#D4D4D8'; e.currentTarget.style.background = '#18181B'; }}
          onMouseLeave={(e) => { e.currentTarget.style.color = '#52525B'; e.currentTarget.style.background = 'transparent'; }}
        >
          <FiSettings size={15} style={{ flexShrink: 0 }} />
          Settings
        </button>
        <button
          onClick={logout}
          style={{
            width: '100%', display: 'flex', alignItems: 'center', gap: '10px',
            padding: '8px 10px', borderRadius: '6px', fontSize: '13px',
            color: '#52525B', background: 'transparent', border: '1px solid transparent',
            cursor: 'pointer',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.color = '#F87171'; e.currentTarget.style.background = 'rgba(239,68,68,0.06)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.color = '#52525B'; e.currentTarget.style.background = 'transparent'; }}
        >
          <FiLogOut size={15} style={{ flexShrink: 0 }} />
          Logout
        </button>
      </div>
    </aside>
  );
}
