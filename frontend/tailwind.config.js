/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        omura: {
          bg: '#050507',
          dark: '#0A0B14',
          darker: '#030408',
          surface: 'rgba(255,255,255,0.05)',
          'surface-hover': 'rgba(255,255,255,0.08)',
          accent: '#3B82F6',
          'accent-light': '#60A5FA',
          'accent-deep': '#2563EB',
          purple: '#7C3AED',
          'purple-light': '#A78BFA',
          cyan: '#06B6D4',
          pink: '#EC4899',
          success: '#10B981',
          warning: '#F59E0B',
          danger: '#EF4444',
          info: '#3B82F6',
          text: '#FFFFFF',
          'text-secondary': '#94A3B8',
          'text-muted': '#475569',
          border: 'rgba(255,255,255,0.08)',
          'border-hover': 'rgba(255,255,255,0.15)',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      borderRadius: {
        '2xl': '16px',
        '3xl': '20px',
        '4xl': '24px',
      },
      boxShadow: {
        'glow-blue': '0 0 24px rgba(59, 130, 246, 0.2)',
        'glow-blue-md': '0 0 36px rgba(59, 130, 246, 0.25)',
        'glow-blue-lg': '0 0 60px rgba(59, 130, 246, 0.3)',
        'glow-purple': '0 0 24px rgba(124, 58, 237, 0.2)',
        'glow-purple-md': '0 0 36px rgba(124, 58, 237, 0.25)',
        'glow-cyan': '0 0 24px rgba(6, 182, 212, 0.2)',
        'glass': '0 8px 32px rgba(0, 0, 0, 0.5)',
        'glass-lg': '0 16px 48px rgba(0, 0, 0, 0.6)',
        'card-hover': '0 16px 48px rgba(0, 0, 0, 0.4), 0 0 30px rgba(59, 130, 246, 0.08)',
        'elevated': '0 24px 64px rgba(0, 0, 0, 0.5), 0 0 1px rgba(255, 255, 255, 0.08)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'pulse-glow': 'pulseGlow 2s ease-in-out infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
        'float': 'float 8s ease-in-out infinite',
        'float-slow': 'float 12s ease-in-out infinite',
        'float-reverse': 'float 10s ease-in-out infinite reverse',
        'slide-up': 'slideUp 0.5s cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-down': 'slideDown 0.3s ease-out',
        'fade-in': 'fadeIn 0.4s ease-out',
        'fade-in-up': 'fadeInUp 0.5s cubic-bezier(0.16, 1, 0.3, 1)',
        'fade-in-up-1': 'fadeInUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.05s both',
        'fade-in-up-2': 'fadeInUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.1s both',
        'fade-in-up-3': 'fadeInUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.15s both',
        'fade-in-up-4': 'fadeInUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.2s both',
        'shimmer': 'shimmer 1.5s linear infinite',
        'spin-slow': 'spin 3s linear infinite',
        'gradient': 'gradientShift 6s ease infinite',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(59, 130, 246, 0.2)' },
          '100%': { boxShadow: '0 0 30px rgba(59, 130, 246, 0.4)' },
        },
        pulseGlow: {
          '0%, 100%': { opacity: '0.5' },
          '50%': { opacity: '1' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-20px)' },
        },
        slideUp: {
          '0%': { transform: 'translateY(16px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        slideDown: {
          '0%': { transform: 'translateY(-12px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        fadeInUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        gradientShift: {
          '0%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
          '100%': { backgroundPosition: '0% 50%' },
        },
      },
    },
  },
  plugins: [],
}
