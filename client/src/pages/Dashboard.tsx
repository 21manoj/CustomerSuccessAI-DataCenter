import { useState, useEffect } from 'react';
import axios from 'axios';

function Dashboard() {
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchUsers = async () => {
      try {
        const token = localStorage.getItem('token');
        const response = await axios.get('/api/users', {
          headers: token ? { Authorization: `Bearer ${token}` } : {}
        });
        setUsers(response.data.users || []);
      } catch (err: any) {
        setError(err.response?.data?.message || 'Failed to fetch users');
      } finally {
        setLoading(false);
      }
    };

    fetchUsers();
  }, []);

  return (
    <div className="page">
      <div className="card">
        <h1>Dashboard</h1>
        <p style={{ marginTop: '1rem', color: '#6b7280' }}>
          Welcome to your dashboard!
        </p>
      </div>

      <div className="card">
        <h2>Users</h2>
        {loading && <p>Loading...</p>}
        {error && <div className="error">{error}</div>}
        {!loading && !error && (
          <div style={{ marginTop: '1rem' }}>
            {users.length > 0 ? (
              <ul style={{ listStyle: 'none', padding: 0 }}>
                {users.map((user) => (
                  <li
                    key={user.id}
                    style={{
                      padding: '1rem',
                      marginBottom: '0.5rem',
                      background: '#f9fafb',
                      borderRadius: '8px',
                      border: '1px solid #e5e7eb'
                    }}
                  >
                    <strong>{user.name || user.email}</strong>
                    <br />
                    <small style={{ color: '#6b7280' }}>{user.email}</small>
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
}

export default Dashboard;

