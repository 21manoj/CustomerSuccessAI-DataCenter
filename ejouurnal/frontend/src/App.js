import React, { useState } from 'react';

function App() {
  const [health, setHealth] = useState(null);

  const checkBackend = async () => {
    try {
      const response = await fetch('http://localhost:3005/health');
      const data = await response.json();
      setHealth(data);
    } catch (error) {
      setHealth({ error: error.message });
    }
  };

  return (
    <div style={{ fontFamily: 'Arial, sans-serif', padding: '40px', maxWidth: '800px', margin: '0 auto' }}>
      <h1 style={{ color: '#2563eb' }}>🌱 Fulfillment App</h1>
      <p style={{ color: '#666' }}>Production-ready backend testing</p>
      
      <div style={{ marginTop: '30px' }}>
        <button 
          onClick={checkBackend}
          style={{
            background: '#2563eb',
            color: 'white',
            border: 'none',
            padding: '12px 24px',
            borderRadius: '8px',
            cursor: 'pointer',
            fontSize: '16px',
            fontWeight: 'bold'
          }}
        >
          Test Backend Connection
        </button>
        
        {health && (
          <div style={{
            marginTop: '20px',
            padding: '20px',
            background: health.error ? '#fee' : '#efe',
            borderRadius: '8px',
            border: `2px solid ${health.error ? '#fcc' : '#cfc'}`
          }}>
            <h3>Backend Response:</h3>
            <pre style={{ fontSize: '12px', overflow: 'auto' }}>
              {JSON.stringify(health, null, 2)}
            </pre>
          </div>
        )}
      </div>

      <div style={{ marginTop: '40px', padding: '20px', background: '#f9fafb', borderRadius: '8px' }}>
        <h2>📊 API Endpoints Ready:</h2>
        <ul style={{ lineHeight: '1.8' }}>
          <li><code>GET /health</code> - Health check</li>
          <li><code>POST /api/users</code> - Create user</li>
          <li><code>POST /api/check-ins</code> - Log check-in</li>
          <li><code>POST /api/journals/generate</code> - ✨ Generate AI journal</li>
          <li><code>POST /api/journals/:id/regenerate</code> - Regenerate with new tone</li>
        </ul>
      </div>

      <div style={{ marginTop: '20px', padding: '20px', background: '#fef3c7', borderRadius: '8px' }}>
        <h3>🧪 Test AI Journal Generation:</h3>
        <p style={{ fontSize: '14px', color: '#666' }}>
          Open terminal and run:
        </p>
        <pre style={{ background: '#1f2937', color: '#10b981', padding: '15px', borderRadius: '6px', fontSize: '12px', overflowX: 'auto' }}>
{`curl -X POST http://localhost:3005/api/journals/generate \\
  -H "Content-Type: application/json" \\
  -d '{
    "userId": "test_001",
    "tone": "reflective"
  }'`}
        </pre>
      </div>
    </div>
  );
}

export default App;

