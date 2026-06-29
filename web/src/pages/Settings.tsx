import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import api from "@/lib/api";
import { Settings2, UserPlus, Shield, CheckCircle, XCircle } from "lucide-react";

const ROLE_BADGES: Record<string, string> = {
  Admin: "bg-primary/10 text-primary border-primary/20",
  Manager: "bg-purple-50 text-purple-700 border-purple-200",
  Salesperson: "bg-cyan-50 text-cyan-700 border-cyan-200",
};

export default function Settings() {
  const { data: users, isLoading } = useQuery({
    queryKey: ["settings", "users"],
    queryFn: () => api.get("/users").then((r) => r.data),
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  });

  return (
    <div className="p-6 space-y-6">
      <div>
        <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
          <Settings2 className="w-4 h-4" />
          <span>Administration</span>
        </div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground mt-1">User management and CRM configuration</p>
      </div>

      <Card>
        <CardHeader className="pb-3 flex flex-row items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <Shield className="w-4 h-4 text-primary" />
            Users ({users?.length || 0})
          </CardTitle>
          <Button size="sm" disabled className="gap-1.5">
            <UserPlus className="w-4 h-4" />
            Add User
          </Button>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="flex items-center gap-3">
                  <div className="skeleton h-10 w-10 rounded-full" />
                  <div className="flex-1 space-y-1">
                    <div className="skeleton h-4 w-28" />
                    <div className="skeleton h-3 w-36" />
                  </div>
                </div>
              ))}
            </div>
          ) : users?.length > 0 ? (
            <div className="divide-y divide-border">
              {users.map((u: any) => (
                <div key={u.username} className="py-3.5 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary/60 to-primary flex items-center justify-center text-sm font-bold text-white">
                      {u.full_name?.charAt(0) || "U"}
                    </div>
                    <div>
                      <p className="font-medium">{u.full_name}</p>
                      <p className="text-xs text-muted-foreground">{u.username}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={cn(
                      "text-xs font-medium px-2 py-0.5 rounded-full border",
                      ROLE_BADGES[u.role] || "bg-muted text-muted-foreground border-border"
                    )}>
                      {u.role}
                    </span>
                    <span className="flex items-center gap-1 text-xs">
                      {u.is_active ? (
                        <>
                          <CheckCircle className="w-3.5 h-3.5 text-green-500" />
                          <span className="text-green-600">Active</span>
                        </>
                      ) : (
                        <>
                          <XCircle className="w-3.5 h-3.5 text-destructive" />
                          <span className="text-destructive">Inactive</span>
                        </>
                      )}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12">
              <Settings2 className="w-10 h-10 text-muted-foreground/30 mx-auto mb-3" />
              <p className="text-muted-foreground font-medium">No users found</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}


