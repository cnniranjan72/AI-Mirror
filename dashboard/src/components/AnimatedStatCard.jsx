import React from 'react';

const AnimatedStatCard = ({ label, value, description, icon, color = 'primary' }) => {
  const colorGradients = {
    primary: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
    secondary: 'linear-gradient(135deg, #8b5cf6 0%, #ec4899 100%)',
    success: 'linear-gradient(135deg, #10b981 0%, #06b6d4 100%)',
    warning: 'linear-gradient(135deg, #f59e0b 0%, #ef4444 100%)',
    info: 'linear-gradient(135deg, #3b82f6 0%, #6366f1 100%)',
    accent: 'linear-gradient(135deg, #ec4899 0%, #f59e0b 100%)'
  };

  return (
    <div className="stat-card" style={{ animationDelay: `${Math.random() * 0.3}s` }}>
      <div className="stat-header">
        <span className="stat-label">{label}</span>
        <span className="stat-icon" style={{ background: colorGradients[color], WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
          {icon}
        </span>
      </div>
      <div className="stat-value">{value}</div>
      <div className="stat-description">{description}</div>
      
      {/* Subtle glow effect */}
      <div 
        className="absolute inset-0 rounded-xl opacity-20 pointer-events-none"
        style={{
          background: colorGradients[color],
          filter: 'blur(20px)',
          transform: 'scale(1.1)',
        }}
      />
    </div>
  );
};

export default AnimatedStatCard;
