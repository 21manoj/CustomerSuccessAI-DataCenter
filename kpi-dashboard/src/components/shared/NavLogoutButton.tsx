import React from 'react';
import { LogOut } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useSession } from '../../contexts/SessionContext';

export type NavLogoutVariant = 'dark-sidebar' | 'light-sidebar' | 'nav-tab' | 'icon-rail' | 'inline';

const VARIANT_CLASSES: Record<NavLogoutVariant, string> = {
  'dark-sidebar':
    'flex items-center gap-2 px-2 py-2 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-white/5 transition-all group w-full text-left',
  'light-sidebar':
    'w-full flex items-center px-4 py-3 rounded-lg text-left text-gray-700 hover:bg-white hover:shadow-sm hover:text-red-600 transition-all duration-200',
  'nav-tab':
    'flex items-center gap-1.5 px-3 py-3 text-sm font-medium border-b-2 border-transparent text-gray-500 hover:text-red-600 transition',
  'icon-rail':
    'relative w-10 h-10 flex items-center justify-center rounded-lg text-gray-500 hover:text-red-400 hover:bg-gray-800/50 transition-colors',
  inline:
    'flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 hover:text-red-600 hover:bg-gray-100 rounded-lg transition-colors',
};

interface NavLogoutButtonProps {
  variant?: NavLogoutVariant;
  className?: string;
  showLabel?: boolean;
  label?: string;
}

export const useAppLogout = () => {
  const { logout } = useSession();
  const navigate = useNavigate();

  return () => {
    fetch('/api/logout', { method: 'POST' }).catch(() => {});
    logout();
    navigate('/login');
  };
};

const NavLogoutButton: React.FC<NavLogoutButtonProps> = ({
  variant = 'dark-sidebar',
  className = '',
  showLabel = true,
  label = 'Logout',
}) => {
  const handleLogout = useAppLogout();
  const iconClass =
    variant === 'dark-sidebar'
      ? 'w-4 h-4 text-gray-500 group-hover:text-gray-300'
      : variant === 'light-sidebar'
        ? 'h-5 w-5 mr-3'
        : variant === 'icon-rail'
          ? 'w-5 h-5'
          : 'w-4 h-4';

  return (
    <button
      type="button"
      onClick={handleLogout}
      className={`${VARIANT_CLASSES[variant]} ${className}`.trim()}
      title={label}
      aria-label={label}
    >
      <LogOut className={iconClass} />
      {showLabel && variant !== 'icon-rail' && (
        <span className={variant === 'dark-sidebar' ? 'flex-1 truncate' : undefined}>{label}</span>
      )}
    </button>
  );
};

export default NavLogoutButton;
