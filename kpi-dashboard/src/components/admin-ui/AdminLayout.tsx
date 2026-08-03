import React, { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useSession } from '../../contexts/SessionContext';
import {
  LayoutDashboard,
  Users,
  Layers,
  Key,
  Activity,
  Menu,
  X,
  LogOut,
  ChevronLeft,
  PlusCircle,
} from 'lucide-react';

// ---------------------------------------------------------------------------
// Sidebar navigation items
// ---------------------------------------------------------------------------

interface NavItem {
  label: string;
  to: string;
  icon: React.ReactNode;
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', to: '/admin', icon: <LayoutDashboard size={18} /> },
  { label: 'Customers', to: '/admin/customers', icon: <Users size={18} /> },
  { label: 'Verticals', to: '/admin/verticals', icon: <Layers size={18} /> },
  { label: 'Custom Vertical', to: '/admin/custom-vertical', icon: <PlusCircle size={18} /> },
  { label: 'Licenses', to: '/admin/licenses', icon: <Key size={18} /> },
  { label: 'Activity Log', to: '/admin/activity', icon: <Activity size={18} /> },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const AdminLayout: React.FC = () => {
  const { session, logout } = useSession();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleBackToDashboard = () => {
    navigate('/dc-dashboard');
  };

  // Shared link classes
  const baseLinkClasses =
    'flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors';
  const activeLinkClasses = 'bg-indigo-700 text-white';
  const inactiveLinkClasses = 'text-indigo-100 hover:bg-indigo-600 hover:text-white';

  // ---------------------------------------------------------------------------
  // Sidebar content (shared between mobile overlay and desktop column)
  // ---------------------------------------------------------------------------
  const sidebarContent = (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-5 border-b border-indigo-600">
        <div>
          <h1 className="text-lg font-bold text-white tracking-tight">CS Pulse Admin</h1>
          <p className="text-xs text-indigo-200 mt-0.5">Management Console</p>
        </div>
        {/* Mobile close button */}
        <button
          className="lg:hidden text-indigo-200 hover:text-white"
          onClick={() => setSidebarOpen(false)}
          aria-label="Close sidebar"
        >
          <X size={20} />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/admin'}
            onClick={() => setSidebarOpen(false)}
            className={({ isActive }) =>
              `${baseLinkClasses} ${isActive ? activeLinkClasses : inactiveLinkClasses}`
            }
          >
            {item.icon}
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-3 py-4 border-t border-indigo-600 space-y-2">
        <button
          onClick={handleBackToDashboard}
          className={`${baseLinkClasses} ${inactiveLinkClasses} w-full`}
        >
          <ChevronLeft size={18} />
          <span>Back to Dashboard</span>
        </button>
        <div className="px-4 py-2 text-xs text-indigo-200 truncate">
          {session?.user_name ?? 'Admin'} &middot; {session?.email ?? ''}
        </div>
        <button
          onClick={handleLogout}
          className={`${baseLinkClasses} text-indigo-200 hover:bg-red-600 hover:text-white w-full`}
        >
          <LogOut size={18} />
          <span>Logout</span>
        </button>
      </div>
    </div>
  );

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      {/* ------------------------------------------------------------------ */}
      {/* Mobile backdrop */}
      {/* ------------------------------------------------------------------ */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Sidebar - mobile (slide-over) */}
      {/* ------------------------------------------------------------------ */}
      <aside
        className={`
          fixed inset-y-0 left-0 z-40 w-64 bg-indigo-800 transform transition-transform duration-200 ease-in-out
          lg:hidden
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        {sidebarContent}
      </aside>

      {/* ------------------------------------------------------------------ */}
      {/* Sidebar - desktop (static) */}
      {/* ------------------------------------------------------------------ */}
      <aside className="hidden lg:flex lg:flex-col lg:w-64 bg-indigo-800 flex-shrink-0">
        {sidebarContent}
      </aside>

      {/* ------------------------------------------------------------------ */}
      {/* Main content area */}
      {/* ------------------------------------------------------------------ */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar (mobile hamburger + breadcrumb area) */}
        <header className="flex items-center h-14 px-4 bg-white border-b border-gray-200 flex-shrink-0 lg:px-6">
          <button
            className="lg:hidden mr-3 text-gray-500 hover:text-gray-700"
            onClick={() => setSidebarOpen(true)}
            aria-label="Open sidebar"
          >
            <Menu size={22} />
          </button>
          <span className="text-sm font-medium text-gray-700">Admin Console</span>
        </header>

        {/* Page content (scrollable) */}
        <main className="flex-1 overflow-y-auto p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default AdminLayout;
