export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'user';
  createdAt: string;
  customer_id?: number; // Add customer_id for backend API calls
}

export interface ChartData {
  name: string;
  value: number;
  date?: string;
}

export interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
}

export interface ChartProps {
  data: ChartData[];
  title: string;
  color?: string;
  height?: number;
} 