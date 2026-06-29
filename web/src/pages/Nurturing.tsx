import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import api from "@/lib/api";
import { cn, scoreBand } from "@/lib/utils";
import { Sprout, ChevronRight, User, Globe, Target } from "lucide-react";

const AVATAR_GRADIENTS = [
  "from-primary/70 to-primary",
  "from-purple-500 to-purple-600",
  "from-amber-500 to-orange-600",
  "from-cyan-500 to-blue-600",
];

export default function Nurturing() {
  const navigate = useNavigate();
  const { data, isLoading } = useQuery({
    queryKey: ["nurturing"],
    queryFn: () =>
      api.get("/dashboard/leads?limit=500").then((r) =>
        (r.data.items as any[]).filter((l: any) => l.status === "Nurturing" || l.status === "Sample Sent")
      ),
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  });

  return (
    <div className="p-6 space-y-6">
      <div>
        <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
          <Sprout className="w-4 h-4" />
          <span>Long-term prospects</span>
        </div>
        <h1 className="text-3xl font-bold tracking-tight">Nurturing Leads</h1>
        <p className="text-muted-foreground mt-1">
          {data ? `${data.length} leads in nurture pipeline` : "Loading..."}
        </p>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="rounded-xl border border-border/60 p-5 space-y-3">
              <div className="skeleton h-5 w-2/3" />
              <div className="skeleton h-4 w-1/2" />
              <div className="skeleton h-3 w-3/4" />
            </div>
          ))}
        </div>
      ) : data && data.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.map((lead: any, idx: number) => {
            const band = scoreBand(lead.lead_score ?? 0);
            const gradientIdx = idx % AVATAR_GRADIENTS.length;
            return (
              <Card
                key={lead.lead_id}
                className="cursor-pointer hover:shadow-md transition-all duration-200 group border-border/60 overflow-hidden"
                onClick={() => navigate(`/leads/${lead.lead_id}`)}
              >
                <div className={cn("h-1 w-full", gradientIdx === 0 ? "bg-primary" : gradientIdx === 1 ? "bg-purple-500" : gradientIdx === 2 ? "bg-amber-500" : "bg-cyan-500")} />
                <CardContent className="p-5">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className={cn(
                        "w-8 h-8 rounded-lg bg-gradient-to-br flex items-center justify-center text-sm font-bold text-white",
                        AVATAR_GRADIENTS[gradientIdx]
                      )}>
                        {(lead.company_name || "?").charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <p className="font-semibold truncate group-hover:text-primary transition-colors">
                          {lead.company_name || "Untitled"}
                        </p>
                        <span className={cn("text-xs font-semibold", band.color)}>
                          {band.label}
                        </span>
                      </div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-muted-foreground/30 group-hover:text-primary/50 transition-colors shrink-0" />
                  </div>
                  <div className="space-y-1.5 text-sm text-muted-foreground">
                    {lead.country && (
                      <p className="flex items-center gap-1.5">
                        <Globe className="w-3.5 h-3.5 text-muted-foreground/50" />
                        {lead.country}
                      </p>
                    )}
                    {lead.contact_person && (
                      <p className="flex items-center gap-1.5">
                        <User className="w-3.5 h-3.5 text-muted-foreground/50" />
                        {lead.contact_person}
                      </p>
                    )}
                    {lead.product_interest && (
                      <p className="flex items-center gap-1.5">
                        <Target className="w-3.5 h-3.5 text-muted-foreground/50" />
                        {lead.product_interest}
                      </p>
                    )}
                  </div>
                  {lead.next_action_plan && (
                    <p className="text-xs text-muted-foreground mt-3 italic border-t border-border/40 pt-3">
                      {lead.next_action_plan}
                    </p>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      ) : (
        <Card>
          <CardContent className="py-16 text-center">
            <Sprout className="w-10 h-10 text-muted-foreground/30 mx-auto mb-3" />
            <p className="text-muted-foreground font-medium">No nurturing leads</p>
            <p className="text-xs text-muted-foreground/60 mt-1">Leads in the Nurture stage will appear here</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
