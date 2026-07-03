import { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import Sidebar from "./Sidebar";
import SalespersonSelector from "@/components/SalespersonSelector";
import { useAuth } from "@/lib/auth";

const routeLabels: Record<string, string> = {
  "/": "Dashboard",
  "/leads": "Lead Management",
  "/tasks": "Tasks & Follow-ups",
  "/analytics": "Analytics",
  "/team": "Analytics & Team",
  "/weekly-review": "Weekly Review",
  "/data-entry": "Data Entry",
  "/settings": "Settings",
};

export default function AppShell() {
  const { user } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();
  const basePath = "/" + location.pathname.split("/")[1];
  const currentLabel = routeLabels[basePath] || "";
  const showSelector = user && (user.role === "Admin" || user.role === "Manager");

  return (
    <div className="flex h-screen overflow-hidden bg-[radial-gradient(ellipse_at_top_right,_hsl(152_20%_97%)_0%,_transparent_60%),_radial-gradient(ellipse_at_bottom_left,_hsl(210_20%_96%)_0%,_transparent_50%)]">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/10 backdrop-blur-sm z-20 lg:hidden animate-fade-in"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="flex-1 flex flex-col min-w-0">
        {/* Desktop header */}
        <header className="hidden lg:flex h-14 items-center justify-end gap-4 px-6 bg-white/60 backdrop-blur-md border-b border-border/50 shrink-0">
        </header>
        {/* Mobile header */}
        <header className="h-14 lg:hidden flex items-center gap-3 px-4 bg-white/80 backdrop-blur-md border-b border-border/50 shrink-0">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 -ml-1 rounded-lg hover:bg-muted/60 transition-colors"
            aria-label="Toggle sidebar"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <div>
            <span className="font-bold text-[15px] text-primary">FitTree</span>
            {currentLabel && (
              <span className="text-xs text-muted-foreground/60 ml-2 font-medium">{currentLabel}</span>
            )}
          </div>
        </header>
        <main className="flex-1 overflow-y-auto">
          <div className="page-enter">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
