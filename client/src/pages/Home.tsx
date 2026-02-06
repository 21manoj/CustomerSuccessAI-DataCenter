import { Link } from 'react-router-dom';

function Home() {
  return (
    <div className="page">
      <div className="card">
        <h1>Welcome to the App</h1>
        <p style={{ marginTop: '1rem', color: '#6b7280' }}>
          This is a modern full-stack application with React frontend and Express backend.
        </p>
        <div style={{ marginTop: '2rem', display: 'flex', gap: '1rem' }}>
          <Link to="/register" className="btn btn-primary">
            Get Started
          </Link>
          <Link to="/login" className="btn btn-secondary">
            Login
          </Link>
        </div>
      </div>

      <div className="card">
        <h2>Features</h2>
        <ul style={{ marginTop: '1rem', listStyle: 'none', padding: 0 }}>
          <li style={{ padding: '0.5rem 0', borderBottom: '1px solid #e5e7eb' }}>
            ✅ Modern React with TypeScript
          </li>
          <li style={{ padding: '0.5rem 0', borderBottom: '1px solid #e5e7eb' }}>
            ✅ Express.js backend with TypeScript
          </li>
          <li style={{ padding: '0.5rem 0', borderBottom: '1px solid #e5e7eb' }}>
            ✅ Fast development with Vite
          </li>
          <li style={{ padding: '0.5rem 0', borderBottom: '1px solid #e5e7eb' }}>
            ✅ RESTful API endpoints
          </li>
          <li style={{ padding: '0.5rem 0' }}>
            ✅ Production-ready structure
          </li>
        </ul>
      </div>
    </div>
  );
}

export default Home;

