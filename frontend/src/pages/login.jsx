/**
 * Omura Login Page — OAuth authentication for all platforms.
 * Cryptix dark glass theme with ambient background.
 */

import React, { useEffect } from 'react';
import { useRouter } from 'next/router';
import { FiMail, FiFacebook } from 'react-icons/fi';
import { isAuthenticated, initiateOAuth, handleOAuthCallback } from '../services/authService';

const PROVIDERS = [
  { id: 'google', label: 'Continue with Google', icon: FiMail, color: 'from-red-600 to-red-500' },
  { id: 'facebook', label: 'Continue with Facebook', icon: FiFacebook, color: 'from-blue-600 to-blue-500' },
];

export default function Login() {
  const router = useRouter();

  useEffect(() => {
    // If already authenticated, redirect to dashboard
    if (isAuthenticated()) {
      router.push('/');
      return;
    }
    // Handle OAuth callback
    const { code, state } = router.query;
    if (code && state) {
      handleOAuthCallback(code, state)
        .then(() => router.push('/'))
        .catch((err) => console.error('OAuth failed:', err));
    }
  }, [router.query]);

  return (
    <div className="min-h-screen bg-omura-bg flex items-center justify-center relative overflow-hidden">
      {/* Ambient background */}
      <div className="ambient-bg" />

      <div className="w-full max-w-md relative z-10 animate-fade-in">
        {/* Logo */}
        <div className="text-center mb-10">
          <h1 className="text-6xl font-bold mb-3 tracking-tight">
            <span className="gradient-text">O</span>
            <span className="text-white">mura</span>
          </h1>
          <p className="text-slate-500 text-sm tracking-wide">Personal & Business Operating System</p>
        </div>

        {/* Login Card */}
        <div className="glass-card p-8">
          <h2 className="text-lg font-semibold mb-6 text-center text-white">Welcome, Sir</h2>

          <div className="space-y-3">
            {PROVIDERS.map((provider) => {
              const Icon = provider.icon;
              return (
                <button
                  key={provider.id}
                  onClick={() => initiateOAuth(provider.id)}
                  className={`w-full flex items-center justify-center gap-3 px-4 py-3.5 rounded-xl
                    text-white font-medium transition-all duration-300
                    bg-gradient-to-r ${provider.color}
                    hover:shadow-lg hover:translate-y-[-1px]
                    border border-white/10`}
                >
                  <Icon size={20} />
                  {provider.label}
                </button>
              );
            })}
          </div>

          <div className="flex items-center gap-3 my-8">
            <div className="flex-1 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />
            <span className="text-xs text-slate-500 uppercase tracking-wider">or</span>
            <div className="flex-1 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />
          </div>

          {/* Direct access (for development) */}
          <button
            onClick={() => {
              localStorage.setItem('omura_token', 'dev-token');
              localStorage.setItem('omura_user', JSON.stringify({ name: 'Sir', role: 'admin' }));
              router.push('/');
            }}
            className="w-full flex items-center justify-center gap-2 py-3.5 rounded-xl
              font-semibold text-white transition-all duration-300
              gradient-blue-purple hover:shadow-glow-blue-lg hover:translate-y-[-1px]"
          >
            Enter Omura (Dev Mode)
          </button>

          <p className="text-xs text-slate-600 text-center mt-5">
            Connect your accounts to unlock full functionality.
          </p>
        </div>

        <p className="text-xs text-slate-600 text-center mt-6 tracking-wide">
          Secured with OAuth 2.0 &middot; AES-256 encrypted storage
        </p>
      </div>
    </div>
  );
}
