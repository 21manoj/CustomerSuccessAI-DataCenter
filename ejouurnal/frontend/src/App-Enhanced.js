import React, { useState } from 'react';
import InsightCard from './components/InsightCard';
import ConversionOffer from './components/ConversionOffer';
import InteractionTracker from './services/InteractionTracker';

function App() {
  const [health, setHealth] = useState(null);
  const [userId, setUserId] = useState('test_user_001');
  const [isPremium, setIsPremium] = useState(false);
  const [insights, setInsights] = useState([]);
  const [showOffer, setShowOffer] = useState(false);
  const [currentOffer, setCurrentOffer] = useState(null);
  const [analytics, setAnalytics] = useState(null);

  const checkBackend = async () => {
    try {
      const response = await fetch('http://localhost:3005/health');
      const data = await response.json();
      setHealth(data);
      setAnalytics(data);
    } catch (error) {
      setHealth({ error: error.message });
    }
  };

  const loadInsights = async () => {
    try {
      const response = await fetch(`http://localhost:3005/api/insights/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId })
      });
      const data = await response.json();
      if (data.insights) {
        setInsights(data.insights);
      }
    } catch (error) {
      console.error('Error loading insights:', error);
    }
  };

  const handleUpgradeClick = async (insight) => {
    // Get conversion offer
    try {
      const response = await fetch(`http://localhost:3005/api/conversion/offer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId })
      });
      const data = await response.json();
      if (data.offer) {
        setCurrentOffer(data);
        setShowOffer(true);
      }
    } catch (error) {
      console.error('Error getting offer:', error);
    }
  };

  const handleAcceptOffer = async () => {
    try {
      const response = await fetch(`http://localhost:3005/api/users/${userId}/premium`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tier: 'premium', plan: 'monthly' })
      });
      const data = await response.json();
      if (data.success) {
        setIsPremium(true);
        setShowOffer(false);
        alert('🎉 Welcome to Premium!');
      }
    } catch (error) {
      console.error('Error upgrading:', error);
    }
  };

  const handleDismissOffer = () => {
    setShowOffer(false);
  };

  return (
    <div style={{ fontFamily: 'Arial, sans-serif', padding: '40px', maxWidth: '900px', margin: '0 auto' }}>
      <h1 style={{ color: '#8b5cf6' }}>🌱 Fulfillment App</h1>
      <p style={{ color: '#666' }}>Enhanced with Interaction Tracking</p>
      
      {isPremium && (
        <div style={{
          background: '#ecfdf5',
          border: '2px solid #10b981',
          borderRadius: '8px',
          padding: '12px',
          marginBottom: '20px',
          textAlign: 'center'
        }}>
          💎 Premium Member
        </div>
      )}
      
      <div style={{ marginTop: '30px', display: 'flex', gap: '12px' }}>
        <button 
          onClick={checkBackend}
          style={{
            background: '#8b5cf6',
            color: 'white',
            border: 'none',
            padding: '12px 24px',
            borderRadius: '8px',
            cursor: 'pointer',
            fontSize: '16px',
            fontWeight: 'bold'
          }}
        >
          Test Backend
        </button>
        
        <button 
          onClick={loadInsights}
          style={{
            background: '#10b981',
            color: 'white',
            border: 'none',
            padding: '12px 24px',
            borderRadius: '8px',
            cursor: 'pointer',
            fontSize: '16px',
            fontWeight: 'bold'
          }}
        >
          Load Insights
        </button>
      </div>

      {analytics && (
        <div style={{
          marginTop: '20px',
          padding: '20px',
          background: '#f9fafb',
          borderRadius: '8px'
        }}>
          <h3>📊 Analytics:</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px', marginTop: '12px' }}>
            <div>
              <div style={{ fontSize: '24px', fontWeight: 'bold' }}>{analytics.totalUsers}</div>
              <div style={{ fontSize: '12px', color: '#6b7280' }}>Total Users</div>
            </div>
            <div>
              <div style={{ fontSize: '24px', fontWeight: 'bold' }}>{analytics.totalCheckIns}</div>
              <div style={{ fontSize: '12px', color: '#6b7280' }}>Check-ins</div>
            </div>
            <div>
              <div style={{ fontSize: '24px', fontWeight: 'bold' }}>{analytics.totalJournals}</div>
              <div style={{ fontSize: '12px', color: '#6b7280' }}>Journals</div>
            </div>
            <div>
              <div style={{ fontSize: '24px', fontWeight: 'bold' }}>{analytics.totalInsights}</div>
              <div style={{ fontSize: '12px', color: '#6b7280' }}>Insights</div>
            </div>
            <div>
              <div style={{ fontSize: '24px', fontWeight: 'bold' }}>{analytics.premiumUsers}</div>
              <div style={{ fontSize: '12px', color: '#6b7280' }}>Premium</div>
            </div>
          </div>
        </div>
      )}

      {insights.length > 0 && (
        <div style={{
          marginTop: '30px',
          background: '#fef3c7',
          borderRadius: '8px',
          padding: '20px'
        }}>
          <h2>💡 Your Insights:</h2>
          {insights.map((insight, idx) => (
            <InsightCard
              key={idx}
              insight={insight}
              isPremium={isPremium}
              userId={userId}
              onUpgrade={handleUpgradeClick}
            />
          ))}
        </div>
      )}

      {showOffer && currentOffer && (
        <ConversionOffer
          offer={currentOffer}
          userId={userId}
          onAccept={handleAcceptOffer}
          onDismiss={handleDismissOffer}
          onClose={handleDismissOffer}
        />
      )}
    </div>
  );
}

export default App;

