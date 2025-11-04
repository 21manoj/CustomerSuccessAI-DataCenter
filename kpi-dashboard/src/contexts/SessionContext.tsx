import React, { createContext, useContext, useState } from 'react';

type Session = {
  customer_id: number;
  user_id: string;
  user_name: string;
  email: string;
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
    return stored ? JSON.parse(stored) : null;
  });

  const login = (newSession: Session) => {
    setSessionState(newSession);
    localStorage.setItem('session', JSON.stringify(newSession));
  };

  const logout = () => {
    setSessionState(null);
    localStorage.removeItem('session');
  };

  return (
    <SessionContext.Provider value={{ session, login, logout }}>
      {children}
    </SessionContext.Provider>
  );
}; 