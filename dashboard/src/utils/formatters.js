import { format, formatDistanceToNow } from 'date-fns';
import { formatDateTimeWithTimezone, getCurrentTimezone } from './timezone';

export const formatDuration = (seconds) => {
  if (seconds < 60) {
    return `${Math.round(seconds)}s`;
  } else if (seconds < 3600) {
    const minutes = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return `${minutes}m ${secs}s`;
  } else {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  }
};

export const formatDateTime = (dateString) => {
  try {
    const timezone = getCurrentTimezone();
    return formatDateTimeWithTimezone(dateString, timezone);
  } catch (error) {
    return dateString;
  }
};

export const formatRelativeTime = (dateString) => {
  try {
    return formatDistanceToNow(new Date(dateString), { addSuffix: true });
  } catch (error) {
    return dateString;
  }
};

export const formatNumber = (num) => {
  return new Intl.NumberFormat().format(num);
};

export const formatPercentage = (num, decimals = 1) => {
  return `${num.toFixed(decimals)}%`;
};
