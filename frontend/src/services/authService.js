/**
 * Omura Auth Service
 * OAuth 2.0 handling for Google, Facebook, Instagram, TikTok, YouTube.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8003';

// ── OAuth provider configs ──
const OAUTH_PROVIDERS = {
  google: {
    authUrl: 'https://accounts.google.com/o/oauth2/v2/auth',
    scope: 'email profile https://www.googleapis.com/auth/gmail.modify https://www.googleapis.com/auth/calendar',
    clientIdKey: 'NEXT_PUBLIC_GOOGLE_CLIENT_ID',
  },
  facebook: {
    authUrl: 'https://www.facebook.com/v18.0/dialog/oauth',
    scope: 'email,pages_manage_posts,pages_read_engagement,instagram_basic',
    clientIdKey: 'NEXT_PUBLIC_FACEBOOK_APP_ID',
  },
  tiktok: {
    authUrl: 'https://www.tiktok.com/auth/authorize/',
    scope: 'user.info.basic,video.list',
    clientIdKey: 'NEXT_PUBLIC_TIKTOK_CLIENT_KEY',
  },
};

/**
 * Initiate OAuth flow for a provider.
 * Opens the provider's consent screen in a new window.
 */
export function initiateOAuth(provider) {
  const config = OAUTH_PROVIDERS[provider];
  if (!config) throw new Error(`Unknown OAuth provider: ${provider}`);

  const clientId = process.env[config.clientIdKey] || '';
  const redirectUri = `${API_BASE}/auth/${provider}/callback`;
  const state = generateState();

  sessionStorage.setItem('oauth_state', state);
  sessionStorage.setItem('oauth_provider', provider);

  const params = new URLSearchParams({
    client_id: clientId,
    redirect_uri: redirectUri,
    scope: config.scope,
    response_type: 'code',
    state,
  });

  window.location.href = `${config.authUrl}?${params.toString()}`;
}

/**
 * Handle OAuth callback — exchange code for token.
 */
export async function handleOAuthCallback(code, state) {
  const savedState = sessionStorage.getItem('oauth_state');
  const provider = sessionStorage.getItem('oauth_provider');

  if (state !== savedState) throw new Error('OAuth state mismatch — possible CSRF');

  const response = await fetch(`${API_BASE}/auth/${provider}/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code, redirect_uri: `${API_BASE}/auth/${provider}/callback` }),
  });

  if (!response.ok) throw new Error('Token exchange failed');

  const data = await response.json();
  localStorage.setItem('omura_token', data.access_token);
  localStorage.setItem('omura_user', JSON.stringify(data.user));

  sessionStorage.removeItem('oauth_state');
  sessionStorage.removeItem('oauth_provider');

  return data;
}

/**
 * Check if user is authenticated.
 */
export function isAuthenticated() {
  if (typeof window === 'undefined') return false;
  return !!localStorage.getItem('omura_token');
}

/**
 * Get current user data.
 */
export function getCurrentUser() {
  if (typeof window === 'undefined') return null;
  const user = localStorage.getItem('omura_user');
  return user ? JSON.parse(user) : null;
}

/**
 * Logout — clear stored auth data.
 */
export function logout() {
  localStorage.removeItem('omura_token');
  localStorage.removeItem('omura_user');
  window.location.href = '/login';
}

/**
 * Generate random state string for CSRF protection.
 */
function generateState() {
  const array = new Uint8Array(32);
  crypto.getRandomValues(array);
  return Array.from(array, (b) => b.toString(16).padStart(2, '0')).join('');
}

export default {
  initiateOAuth,
  handleOAuthCallback,
  isAuthenticated,
  getCurrentUser,
  logout,
};
