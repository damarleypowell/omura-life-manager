/**
 * Omura Formatting Utilities — Date, number, and display helpers.
 */

import { format, formatDistanceToNow, isToday, isYesterday, parseISO } from 'date-fns';

// ── Date formatting ──

export function formatDate(dateStr) {
  if (!dateStr) return '';
  const date = typeof dateStr === 'string' ? parseISO(dateStr) : dateStr;
  if (isToday(date)) return `Today at ${format(date, 'h:mm a')}`;
  if (isYesterday(date)) return `Yesterday at ${format(date, 'h:mm a')}`;
  return format(date, 'MMM d, yyyy h:mm a');
}

export function formatRelativeTime(dateStr) {
  if (!dateStr) return '';
  const date = typeof dateStr === 'string' ? parseISO(dateStr) : dateStr;
  return formatDistanceToNow(date, { addSuffix: true });
}

export function formatShortDate(dateStr) {
  if (!dateStr) return '';
  const date = typeof dateStr === 'string' ? parseISO(dateStr) : dateStr;
  return format(date, 'MMM d');
}

// ── Number formatting ──

export function formatCurrency(value, currency = 'USD') {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(value);
}

export function formatNumber(value) {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toLocaleString();
}

export function formatPercentage(value, decimals = 1) {
  return `${value.toFixed(decimals)}%`;
}

// ── String helpers ──

export function truncate(str, maxLength = 100) {
  if (!str || str.length <= maxLength) return str;
  return str.slice(0, maxLength) + '...';
}

export function capitalize(str) {
  if (!str) return '';
  return str.charAt(0).toUpperCase() + str.slice(1);
}

export function slugify(str) {
  return str.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
}

// ── Status helpers ──

export function getUrgencyColor(urgency) {
  const colors = { low: 'badge-info', medium: 'badge-accent', high: 'badge-warning', critical: 'badge-danger' };
  return colors[urgency] || 'badge-info';
}

export function getStatusColor(status) {
  const colors = { todo: 'badge-info', in_progress: 'badge-accent', blocked: 'badge-danger', done: 'badge-success' };
  return colors[status] || 'badge-info';
}
