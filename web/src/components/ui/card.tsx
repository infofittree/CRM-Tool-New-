import { cn } from "@/lib/utils";

export function Card({
  className,
  hover,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { hover?: boolean }) {
  return (
    <div
      className={cn(
        "rounded-xl border border-border/60 bg-card text-card-foreground card-elevated",
        hover && "hover:-translate-y-0.5 hover:shadow-card-hover cursor-pointer transition-all duration-200",
        className,
      )}
      {...props}
    />
  );
}

export function CardHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex flex-col gap-1 p-5 pb-3", className)} {...props} />;
}

export function CardTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h2 className={cn("text-[15px] font-semibold tracking-tight", className)} {...props} />;
}

export function CardDescription({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn("text-sm text-muted-foreground/70", className)} {...props} />;
}

export function CardContent({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("p-5 pt-0", className)} {...props} />;
}

export function CardFooter({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex items-center gap-2 p-5 pt-0", className)} {...props} />;
}

export function MetricCard({
  title,
  value,
  subtitle,
  color = "text-foreground",
  trend,
  icon,
  loading,
}: {
  title: string;
  value?: string | number;
  subtitle?: string;
  color?: string;
  trend?: { value: string; positive: boolean };
  icon?: React.ReactNode;
  loading?: boolean;
}) {
  return (
    <Card className="relative overflow-hidden group">
      <CardContent className="p-5">
        {loading ? (
          <div className="space-y-3">
            <div className="skeleton h-4 w-20" />
            <div className="skeleton h-9 w-16" />
            <div className="skeleton h-3 w-28" />
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between mb-2.5">
              <span className="text-[13px] font-medium text-muted-foreground/70">{title}</span>
              {icon && (
                <span className="text-muted-foreground/20 group-hover:text-muted-foreground/40 transition-colors">
                  {icon}
                </span>
              )}
            </div>
            <p className={cn("text-[28px] font-bold tracking-tight leading-none", color)}>
              {value ?? 0}
            </p>
            <div className="flex items-center gap-2 mt-2">
              {subtitle && (
                <span className="text-[13px] text-muted-foreground/60">{subtitle}</span>
              )}
              {trend && (
                <span className={cn(
                  "text-[12px] font-medium inline-flex items-center gap-0.5",
                  trend.positive ? "text-emerald-600" : "text-destructive"
                )}>
                  <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <path d={trend.positive ? "M18 15l-6-6-6 6" : "M6 9l6 6 6-6"} />
                  </svg>
                  {trend.value}
                </span>
              )}
            </div>
            <div className="absolute inset-x-0 bottom-0 h-[2px] bg-gradient-to-r from-transparent via-primary/15 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
          </>
        )}
      </CardContent>
    </Card>
  );
}
