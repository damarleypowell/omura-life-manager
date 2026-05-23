import React from 'react';
import { FiUser } from 'react-icons/fi';

export default function Header({ title, onNavigate }) {
  return (
    <header style={{
      position: 'sticky', top: 0, zIndex: 40,
      background: '#09090B',
      borderBottom: '1px solid #1E1E24',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '0 24px', height: '52px',
    }}>
      <h2 style={{
        fontSize: '15px', fontWeight: 600, color: '#FAFAFA', letterSpacing: '-0.01em',
      }}>
        {title}
      </h2>

      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <div style={{ fontSize: '13px', color: '#71717A' }}>Damarley</div>
        <div style={{
          width: '30px', height: '30px', borderRadius: '6px',
          background: 'linear-gradient(135deg, #2563EB, #7C3AED)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <FiUser size={13} color="white" />
        </div>
      </div>
    </header>
  );
}
