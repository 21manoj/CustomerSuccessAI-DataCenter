import React, { createContext, useContext, useState } from 'react';

type Session = {
  customer_id: number;
  user_id: string;
  user_name: string;
  email: string;
  vertical?: string;
};

const SessionContext = createContext<{
  session: Session | null;
  login: (session: Session) => void;
  logout: () => void;
}>({
  session: null,
  login: () => {},
  logout: () => {}
    });

export const useSession = () => useContext(SessionContext);

export const SessionProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [session, setSessionState] = useState<Session | null>(() => {
    const stored = localStorage.getItem('session');
    const parsed = stored ? JSON.parse(stored) : null;
    // Ensure vertical is loaded from localStorage if not in session
    if (parsed && !parsed.vertical) {
      const vertical = localStorage.getItem('vertical') || 'saas';
      parsed.vertical = vertical;
    }
    return parsed;
  });

  const login = (newSession: Session) => {
    setSessionState(newSession);
    localStorage.setItem('session', JSON.stringify(newSession));
    // Also store vertical separately for easy access
    if (newSession.vertical) {
      localStorage.setItem('vertical', newSession.vertical);
    }
  };

  const logout = () => {
    setSessionState(null);
    localStorage.removeItem('session');
    localStorage.removeItem('vertical');
  };

  return (
    <SessionContext.Provider value={{ session, login, logout }}>
      {children}
    </SessionContext.Provider>
  );
}; 