import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useRef,
  type ReactNode,
} from "react";
import { useNavigate, Navigate } from "react-router-dom";
import api, { type User, type LoginResponse } from "@/lib/api";

const INACTIVITY_TIMEOUT_MS = 20 * 60 * 1000; // 20 minutes

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<string | null>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const logout = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    sessionStorage.removeItem("access_token");
    sessionStorage.removeItem("user");
    setUser(null);
    navigate("/login");
  }, [navigate]);

  // Restore session from sessionStorage on mount so page refresh keeps user logged in
  useEffect(() => {
    const savedToken = sessionStorage.getItem("access_token");
    const savedUser = sessionStorage.getItem("user");
    if (savedToken && savedUser) {
      try {
        setUser(JSON.parse(savedUser));
      } catch {
        sessionStorage.removeItem("access_token");
        sessionStorage.removeItem("user");
      }
    }
    setLoading(false);
  }, []);

  // Inactivity timer — logout after 20 minutes of no activity
  const resetTimer = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    if (user) {
      timerRef.current = setTimeout(() => {
        logout();
      }, INACTIVITY_TIMEOUT_MS);
    }
  }, [user, logout]);

  useEffect(() => {
    if (!user) return;

    const events = ["mousedown", "mousemove", "keydown", "scroll", "touchstart"];
    const handler = () => resetTimer();

    events.forEach((e) => document.addEventListener(e, handler, { passive: true }));
    resetTimer();

    return () => {
      events.forEach((e) => document.removeEventListener(e, handler));
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [user, resetTimer]);

  const login = useCallback(
    async (username: string, password: string): Promise<string | null> => {
      try {
        const res = await api.post<LoginResponse>("/auth/login", {
          username,
          password,
        });
        const { access_token, user: userData } = res.data;
        sessionStorage.setItem("access_token", access_token);
        sessionStorage.setItem("user", JSON.stringify(userData));
        setUser(userData);
        return null;
      } catch (err: any) {
        return "Invalid credentials. Please try again.";
      }
    },
    []
  );

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full" />
      </div>
    );
  }
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

export function hasAccess(user: User | null, requiredRoles: string[]) {
  if (!user) return false;
  return requiredRoles.includes(user.role);
}

export function RoleGuard({ children, roles }: { children: ReactNode; roles: string[] }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user || !roles.includes(user.role)) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}
