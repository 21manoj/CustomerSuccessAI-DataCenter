/**
 * Insight Card Component
 * Displays insights with lock preview for free users
 */

import React from 'react';
import InteractionTracker from '../services/InteractionTracker';

const InsightCard = ({ insight, isPremium, userId, onUpgrade }) => {
  const tracker = new InteractionTracker(userId);
  
  const handleClick = () => {
    if (insight.preview && !isPremium) {
      // Track interaction
      tracker.trackLockedInsightClick(
        insight.id,
        insight.type,
        insight.description
      );
      
      // Show upgrade modal
      onUpgrade(insight);
    }
  };
  
  const cardStyle = {
    background: '#fff',
    borderRadius: '12px',
    padding: '16px',
    marginBottom: '12px',
    border: insight.preview ? '2px solid #e5e7eb' : '1px solid #e5e7eb',
    position: 'relative',
    cursor: insight.preview && !isPremium ? 'pointer' : 'default',
    transition: 'all 0.2s ease'
  };
  
  const titleStyle = {
    fontSize: '16px',
    fontWeight: '600',
    marginBottom: '8px',
    color: insight.preview && !isPremium ? '#6b7280' : '#1f2937'
  };
  
  const descriptionStyle = {
    fontSize: '14px',
    color: insight.preview && !isPremium ? '#9ca3af' : '#4b5563',
    lineHeight: '1.5'
  };
  
  const previewOverlayStyle = {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: 'rgba(255, 255, 255, 0.95)',
    backdropFilter: 'blur(4px)',
    display: insight.preview && !isPremium ? 'flex' : 'none',
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: '12px',
    gap: '8px'
  };
  
  const lockIconStyle = {
    fontSize: '32px'
  };
  
  const unlockMessageStyle = {
    fontSize: '12px',
    fontWeight: '600',
    color: '#8b5cf6',
    textAlign: 'center',
    padding: '0 16px'
  };
  
  const confidenceStyle = {
    display: 'inline-block',
    background: '#f3f4f6',
    padding: '2px 8px',
    borderRadius: '12px',
    fontSize: '11px',
    fontWeight: '500',
    color: '#6b7280'
  };
  
  return (
    <div style={cardStyle} onClick={handleClick}>
      <div style={titleStyle}>
        {insight.title}
      </div>
      
      <div style={descriptionStyle}>
        {insight.description}
      </div>
      
      {insight.confidence && (
        <div style={{ marginTop: '8px' }}>
          <span style={confidenceStyle}>
            {Math.round(insight.confidence * 100)}% confidence
          </span>
        </div>
      )}
      
      {insight.preview && !isPremium && (
        <div style={previewOverlayStyle}>
          <div style={lockIconStyle}>🔒</div>
          <div style={unlockMessageStyle}>
            {insight.unlockMessage || 'Tap to unlock with Premium'}
          </div>
        </div>
      )}
    </div>
  );
};

export default InsightCard;

