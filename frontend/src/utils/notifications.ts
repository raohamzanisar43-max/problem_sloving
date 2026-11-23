/** Fired on window when notifications were read or new ones may have arrived. */
export const NOTIFICATIONS_CHANGED = 'novu-notifications-changed';

export function announceNotificationsChanged() {
  window.dispatchEvent(new Event(NOTIFICATIONS_CHANGED));
}
