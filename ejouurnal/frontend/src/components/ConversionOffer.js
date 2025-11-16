/**
 * Conversion Offer Modal Component
 * Displays context-aware premium conversion offers
 */

import React from 'react';
import InteractionTracker from '../services/InteractionTracker';

const ConversionOffer = ({ offer, userId, onAccept, onDismiss, onClose }) => {
  const tracker = new InteractionTracker(userId);
  
  const handleAccept = () => {
    tracker.trackConversionOfferInteraction('clicked', offer.offerType);
    onAccept();
  };
  
  const handleDismiss = () => {
    tracker.trackConversionOfferInteraction('dismissed', offer.offerType);
    onDismiss();
  };
  
  // Background overlay
  const overlayStyle = {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: 'rgba(0, 0, 0, 0.5)',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 1000
  };
  
  // Modal container
  const modalStyle = {
    background: '#fff',
    borderRadius: '16px',
    padding: '24px',
    maxWidth: '500px',
    width: '90%',
    maxHeight: '90vh',
    overflow: 'auto',
    boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)'
  };
  
  const headlineStyle = {
    fontSize: '20px',
    fontWeight: '700',
    marginBottom: '12px',
    color: '#1f2937'
  };
  
  const messageStyle = {
    fontSize: '14px',
    color: '#6b7280',
    marginBottom: '16px',
    lineHeight: '1.6'
  };
  
  const bulletStyle = {
    fontSize: '14px',
    marginBottom: '8px',
    paddingLeft: '20px',
    position: 'relative'
  };
  
  const bulletIconStyle = {
    position: 'absolute',
    left: 0,
    color: '#8b5cf6'
  };
  
  const pricingContainerStyle = {
    background: '#f9fafb',
    borderRadius: '8px',
    padding: '16px',
    marginBottom: '20px'
  };
  
  const annualPriceStyle = {
    fontSize: '24px',
    fontWeight: '700',
    color: '#1f2937',
    marginBottom: '4px'
  };
  
  const badgeStyle = {
    display: 'inline-block',
    background: '#fef3c7',
    color: '#92400e',
    padding: '2px 8px',
    borderRadius: '4px',
    fontSize: '11px',
    fontWeight: '600',
    marginLeft: '8px'
  };
  
  const monthlyPriceStyle = {
    fontSize: '14px',
    color: '#6b7280'
  };
  
  const ctaButtonStyle = {
    width: '100%',
    background: '#8b5cf6',
    color: '#fff',
    border: 'none',
    padding: '12px',
    borderRadius: '8px',
    fontSize: '16px',
    fontWeight: '600',
    cursor: 'pointer',
    marginBottom: '8px'
  };
  
  const secondaryButtonStyle = {
    width: '100%',
    background: 'transparent',
    color: '#6b7280',
    border: 'none',
    padding: '8px',
    fontSize: '14px',
    cursor: 'pointer'
  };
  
  const urgencyStyle = {
    background: '#fef3c7',
    border: '1px solid #fbbf24',
    borderRadius: '6px',
    padding: '8px 12px',
    marginBottom: '16px',
    fontSize: '12px',
    color: '#92400e'
  };
  
  return (
    <div style={overlayStyle} onClick={onClose}>
      <div style={modalStyle} onClick={(e) => e.stopPropagation()}>
        <div style={headlineStyle}>{offer.messaging.headline}</div>
        
        {offer.messaging.urgency && (
          <div style={urgencyStyle}>
            ⚡ {offer.messaging.urgency}
          </div>
        )}
        
        <div style={messageStyle}>{offer.messaging.message}</div>
        
        <div style={{ marginBottom: '16px' }}>
          {offer.messaging.bullets.map((bullet, idx) => (
            <div key={idx} style={bulletStyle}>
              <span style={bulletIconStyle}>✓</span>
              {bullet}
            </div>
          ))}
        </div>
        
        <div style={pricingContainerStyle}>
          <div style={annualPriceStyle}>
            ${offer.pricing.annual}/year
            <span style={badgeStyle}>{offer.pricing.discount}</span>
          </div>
          <div style={monthlyPriceStyle}>
            or ${offer.pricing.monthly}/month
          </div>
        </div>
        
        <button style={ctaButtonStyle} onClick={handleAccept}>
          {offer.messaging.cta}
        </button>
        
        <button style={secondaryButtonStyle} onClick={handleDismiss}>
          Maybe later
        </button>
      </div>
    </div>
  );
};

export default ConversionOffer;

