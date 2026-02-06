import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

interface User {
  user_id: number;
  customer_id: number;
  user_name: string;
  email: string;
}

const Dashboard: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [user, setUser] = useState<User | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    // Get current user from localStorage
    const userStr = localStorage.getItem('user');
    if (userStr) {
      setUser(JSON.parse(userStr));
    } else {
      navigate('/login');
      return;
    }

    // Fetch users
    const fetchUsers = async () => {
      try {
        const customerId = localStorage.getItem('customer_id');
        const response = await fetch('/api/users', {
          headers: {
            'X-Customer-ID': customerId || '',
          },
        });

        if (!response.ok) {
          throw new Error('Failed to fetch users');
        }

        const data = await response.json();
        setUsers(data.users || []);
      } catch (err: any) {
        setError(err.message || 'Failed to fetch users');
      } finally {
        setLoading(false);
      }
    };

    fetchUsers();
  }, [navigate]);

  const handleLogout = () => {
    localStorage.removeItem('user');
    localStorage.removeItem('customer_id');
    localStorage.removeItem('user_id');
    navigate('/login');
  };

  return (
    <div className="page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h1>Dashboard</h1>
        <button onClick={handleLogout} className="btn btn-primary">
          Logout
        </button>
      </div>

      {user && (
        <div className="card">
          <h2>Welcome, {user.user_name}!</h2>
          <p style={{ marginTop: '0.5rem', color: '#6b7280' }}>
            Email: {user.email}
          </p>
          <p style={{ marginTop: '0.5rem', color: '#6b7280' }}>
            Customer ID: {user.customer_id}
          </p>
        </div>
      )}

      <div className="card">
        <h2>Users</h2>
        {loading && <p>Loading...</p>}
        {error && <div className="error">{error}</div>}
        {!loading && !error && (
          <div style={{ marginTop: '1rem' }}>
            {users.length > 0 ? (
              <ul style={{ listStyle: 'none', padding: 0 }}>
                {users.map((u) => (
                  <li
                    key={u.user_id}
                    style={{
                      padding: '1rem',
                      marginBottom: '0.5rem',
                      background: '#f9fafb',
                      borderRadius: '8px',
                      border: '1px solid #e5e7eb'
                    }}
                  >
                    <strong>{u.user_name}</strong>
                    <br />
                    <small style={{ color: '#6b7280' }}>{u.email}</small>
                  </li>
                ))}
              </ul>
            ) : (
              <p style={{ color: '#6b7280' }}>No users found</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;

