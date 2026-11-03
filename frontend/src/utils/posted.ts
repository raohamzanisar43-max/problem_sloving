export type PostedWindow = 'today' | 'week' | 'month' | 'older';

export const POSTED_OPTIONS: { value: '' | PostedWindow; label: string }[] = [
  { value: '', label: 'Any time' },
  { value: 'today', label: 'Today' },
  { value: 'week', label: 'Last 7 days' },
  { value: 'month', label: 'Last 30 days' },
  { value: 'older', label: 'Older than 30 days' },
];

export function isPostedWindow(value: string | null): value is PostedWindow {
  return value === 'today' || value === 'week' || value === 'month' || value === 'older';
}

/** "Today", "Yesterday", "5 days ago", "3 weeks ago", "2 months ago" — or '' when there is no date. */
export function formatPosted(iso?: string | null, now: Date = new Date()): string {
  if (!iso) return '';
  const posted = new Date(iso);
  if (Number.isNaN(posted.getTime())) return '';

  const startOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const days = Math.round((startOfDay(now) - startOfDay(posted)) / 86_400_000);

  if (days <= 0) return 'Today';
  if (days === 1) return 'Yesterday';
  if (days < 7) return `${days} days ago`;
  if (days < 30) {
    const weeks = Math.floor(days / 7);
    return weeks === 1 ? '1 week ago' : `${weeks} weeks ago`;
  }
  const months = Math.floor(days / 30);
  return months === 1 ? '1 month ago' : `${months} months ago`;
}
