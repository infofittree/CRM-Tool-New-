import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useAuth } from "@/lib/auth";
import api from "@/lib/api";

interface SalespersonContextType {
  selectedSalesperson: string | null;
  setSelectedSalesperson: (name: string | null) => void;
  salespersons: string[];
}

const SalespersonContext = createContext<SalespersonContextType>({
  selectedSalesperson: null,
  setSelectedSalesperson: () => {},
  salespersons: [],
});

export function SalespersonProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [selectedSalesperson, setSelectedSalesperson] = useState<string | null>(null);
  const [salespersons, setSalespersons] = useState<string[]>([]);

  const canViewAll = user?.role === "Admin" || user?.role === "Manager";

  useEffect(() => {
    if (!user) return;
    if (!canViewAll) {
      setSelectedSalesperson(null);
      return;
    }
    api.get("/users/salespersons").then((r) => setSalespersons(r.data || [])).catch(() => {});
  }, [user, canViewAll]);

  return (
    <SalespersonContext.Provider value={{ selectedSalesperson, setSelectedSalesperson, salespersons }}>
      {children}
    </SalespersonContext.Provider>
  );
}

export function useSalespersonFilter() {
  return useContext(SalespersonContext);
}
