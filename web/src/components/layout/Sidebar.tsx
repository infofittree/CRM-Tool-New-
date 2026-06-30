import { NavLink, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface NavItem {
  href: string;
  label: string;
  icon: string;
  roles: string[];
}

const navItems: NavItem[] = [
  { href: "/", label: "Dashboard", icon: "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-4 0a1 1 0 01-1-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 01-1 1", roles: ["Admin", "Manager", "Salesperson", "Procurement"] },
  { href: "/leads", label: "Leads", icon: "M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z", roles: ["Admin", "Manager", "Salesperson"] },
  { href: "/tasks", label: "Tasks", icon: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4", roles: ["Salesperson"] },
  { href: "/analytics", label: "Analytics", icon: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z", roles: ["Salesperson"] },
  { href: "/team", label: "Team", icon: "M13 7h8m0 0v8m0-8l-8 8-4-4-6 6", roles: ["Admin", "Manager"] },
  { href: "/weekly-review", label: "Weekly Review", icon: "M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z", roles: ["Admin", "Manager", "Salesperson"] },
  { href: "/data-entry", label: "Data Entry", icon: "M12 4v16m8-8H4", roles: ["Admin", "Manager", "Salesperson"] },
  { href: "/settings", label: "Settings", icon: "M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z", roles: ["Admin", "Manager"] },
  { href: "/inquiries", label: "Inquiries", icon: "M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z", roles: ["Admin", "Manager", "Salesperson", "Procurement"] },
];

export default function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const visibleItems = navItems.filter((item) => user && item.roles.includes(user.role));

  return (
    <aside
      className={cn(
        "fixed lg:static inset-y-0 left-0 z-30 flex flex-col",
        "w-60 bg-white border-r border-border/40",
        "transition-transform duration-200 ease-out",
        open ? "translate-x-0" : "-translate-x-full lg:translate-x-0",
      )}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 h-16 border-b border-border/30 shrink-0">
        <div className="relative flex items-center justify-center w-8 h-8 rounded-xl bg-gradient-to-br from-primary to-primary/80 shadow-sm">
          <svg className="w-4.5 h-4.5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
          </svg>
        </div>
        <div className="leading-tight">
          <span className="font-bold text-[15px] text-primary tracking-tight">FitTree</span>
          <span className="text-[10px] text-muted-foreground/50 block font-semibold tracking-widest uppercase">CRM</span>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-3 px-2.5 space-y-0.5 overflow-y-auto">
        {visibleItems.map((item) => {
          const isActive = item.href === "/"
            ? location.pathname === "/"
            : location.pathname.startsWith(item.href);
          return (
            <NavLink
              key={item.href}
              to={item.href}
              end={item.href === "/"}
              onClick={onClose}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-xl text-[13px] font-medium",
                "transition-all duration-180 ease-out",
                isActive
                  ? "bg-primary/[0.07] text-primary shadow-sm"
                  : "text-muted-foreground/60 hover:text-foreground hover:bg-muted/40",
              )}
            >
              <svg
                className={cn("w-[18px] h-[18px] shrink-0 transition-colors duration-180", isActive ? "text-primary" : "text-muted-foreground/35")}
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth={isActive ? 2 : 1.8}
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d={item.icon} />
              </svg>
              <span>{item.label}</span>
              {isActive && (
                <span className="ml-auto w-1.5 h-1.5 rounded-full bg-primary/50" />
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* User area */}
      <div className="p-3 border-t border-border/30 shrink-0">
        <div className="flex items-center gap-3 px-2 py-2.5 rounded-xl hover:bg-muted/30 transition-colors duration-150 cursor-default">
          <div className="relative flex items-center justify-center w-9 h-9 rounded-full bg-gradient-to-br from-primary to-primary/70 text-sm font-semibold text-white shadow-sm shrink-0">
            {user?.full_name?.charAt(0) || "U"}
            <span className="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-white bg-emerald-500" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-[13px] font-medium truncate leading-tight">{user?.full_name}</p>
            <p className="text-[11px] text-muted-foreground/50 truncate font-medium">{user?.role}</p>
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="w-full mt-1 justify-start gap-2.5 text-muted-foreground/50 hover:text-foreground text-[13px] font-normal h-9 rounded-xl"
          onClick={() => { logout(); navigate("/login"); }}
        >
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" />
            <polyline points="16 17 21 12 16 7" />
            <line x1="21" y1="12" x2="9" y2="12" />
          </svg>
          Sign out
        </Button>
      </div>
    </aside>
  );
}
