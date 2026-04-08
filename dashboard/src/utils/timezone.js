// Timezone utilities for AIMirror dashboard

export const TIMEZONES = {
  UTC: {
    name: 'UTC',
    offset: 0,
    label: 'Coordinated Universal Time'
  },
  IST: {
    name: 'IST',
    offset: 5.5,
    label: 'Indian Standard Time'
  }
};

export const formatTimeWithTimezone = (dateString, timezone = 'UTC') => {
  try {
    const date = new Date(dateString);
    const tz = TIMEZONES[timezone];
    
    if (!tz) {
      return formatTimeWithTimezone(dateString, 'UTC');
    }

    // Calculate IST time (UTC + 5:30 hours)
    const istOffset = 5.5 * 60 * 60 * 1000; // 5.5 hours in milliseconds
    const utcTime = date.getTime();
    const istTime = new Date(utcTime + istOffset);

    const timeString = istTime.toLocaleTimeString('en-IN', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
      timeZone: 'Asia/Kolkata'
    });

    return `${timeString} ${tz.name}`;
  } catch (error) {
    return dateString;
  }
};

export const formatDateTimeWithTimezone = (dateString, timezone = 'UTC') => {
  try {
    const date = new Date(dateString);
    const tz = TIMEZONES[timezone];
    
    if (!tz) {
      return formatDateTimeWithTimezone(dateString, 'UTC');
    }

    // Calculate IST time (UTC + 5:30 hours)
    const istOffset = 5.5 * 60 * 60 * 1000; // 5.5 hours in milliseconds
    const utcTime = date.getTime();
    const istTime = new Date(utcTime + istOffset);

    const dateTimeString = istTime.toLocaleString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
      timeZone: 'Asia/Kolkata'
    });

    return `${dateTimeString} ${tz.name}`;
  } catch (error) {
    return dateString;
  }
};

export const getCurrentTimezone = () => {
  // Get user's preference from localStorage or default to IST for Indian users
  const saved = localStorage.getItem('aimirror_timezone');
  return saved || 'IST'; // Default to IST for Indian users
};

export const setTimezone = (timezone) => {
  localStorage.setItem('aimirror_timezone', timezone);
};
