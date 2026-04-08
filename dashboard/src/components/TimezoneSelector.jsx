import React from 'react';
import { getCurrentTimezone, setTimezone, TIMEZONES } from '../utils/timezone';

function TimezoneSelector() {
  const [currentTimezone, setCurrentTimezone] = React.useState(getCurrentTimezone());

  const handleTimezoneChange = (event) => {
    const newTimezone = event.target.value;
    setCurrentTimezone(newTimezone);
    setTimezone(newTimezone);
    // Trigger a re-render of the page to update timestamps
    window.dispatchEvent(new Event('timezone-changed'));
  };

  return (
    <div className="timezone-selector">
      <select 
        value={currentTimezone}
        onChange={handleTimezoneChange}
        className="timezone-select"
      >
        {Object.values(TIMEZONES).map(tz => (
          <option key={tz.name} value={tz.name}>
            {tz.label} ({tz.name})
          </option>
        ))}
      </select>
    </div>
  );
}

export default TimezoneSelector;
