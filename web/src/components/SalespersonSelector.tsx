import { useSalespersonFilter } from "@/lib/salespersonContext";
import { cn } from "@/lib/utils";
import { User, Users } from "lucide-react";

export default function SalespersonSelector() {
  const { selectedSalesperson, setSelectedSalesperson, salespersons } = useSalespersonFilter();

  if (!salespersons.length) return null;

  return (
    <div className="flex items-center gap-2">
      <span className="text-[12px] text-muted-foreground/50 font-medium whitespace-nowrap hidden sm:inline">View Analytics For</span>
      <div className="relative">
        <select
          value={selectedSalesperson || ""}
          onChange={(e) => setSelectedSalesperson(e.target.value || null)}
          className="appearance-none pl-8 pr-7 py-1.5 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 min-w-[160px] cursor-pointer"
        >
          <option value="">All Sales Team</option>
          {salespersons.map((name) => (
            <option key={name} value={name}>{name}</option>
          ))}
        </select>
        <div className="absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none">
          {selectedSalesperson ? <User className="w-3.5 h-3.5 text-muted-foreground/50" /> : <Users className="w-3.5 h-3.5 text-muted-foreground/50" />}
        </div>
      </div>
    </div>
  );
}
