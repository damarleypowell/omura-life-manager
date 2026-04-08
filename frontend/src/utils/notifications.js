/**
 * Omura Push Notification Utilities
 * Browser push notification helpers for real-time alerts.
 */

// ── Permission handling ──

export async function requestNotificationPermission() {
  if (!('Notification' in window)) {
    console.warn('Browser does not support push notifications');
    return false;
  }
  if (Notification.permission === 'granted') return true;
  if (Notification.permission === 'denied') return false;

  const permission = await Notification.requestPermission();
  return permission === 'granted';
}

// ── Send push notification ──

export function sendPushNotification(title, options = {}) {
  if (!('Notification' in window) || Notification.permission !== 'granted') return;

  const defaults = {
    icon: '/omura-icon.png',
    badge: '/omura-badge.png',
    vibrate: [100, 50, 100],
    tag: 'omura-notification',
    ...options,
  };

  return new Notification(title, defaults);
}

// ── Pre-built notification types ──

export function notifyUrgentMessage(sender, preview) {
  sendPushNotification(`Urgent from ${sender}`, {
    body: preview,
    tag: 'urgent-message',
    requireInteraction: true,
  });
}

export function notifyTaskDue(taskTitle) {
  sendPushNotification('Task Due', {
    body: taskTitle,
    tag: 'task-due',
  });
}

export function notifyAIAction(agentName, action) {
  sendPushNotification(`${agentName} completed`, {
    body: action,
    tag: 'ai-action',
  });
}

export function notifyMetricAlert(metric, message) {
  sendPushNotification(`Alert: ${metric}`, {
    body: message,
    tag: 'metric-alert',
    requireInteraction: true,
  });
}
