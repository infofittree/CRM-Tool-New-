import { cn } from "@/lib/utils";

export function Card({
  className,
  hover,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { hover?: boolean }) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-border/50 bg-card text-card-foreground shadow-[var(--shadow-card)] transition-shadow duration-200",
        hover && "hover:-translate-y-0.5 hover:shadow-[var(--shadow-card-hover)] cursor-pointer",
        className,
      )}
      {...props}
    />
  );
}

export function CardHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex flex-col gap-1 px-6 pt-5 pb-3", className)} {...props} />;
}

export function CardTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h2 className={cn("text-[15px] font-semibold tracking-tight", className)} {...props} />;
}

export function CardDescription({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn("text-sm text-muted-foreground/60", className)} {...props} />;
}

export function CardContent({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("px-6 pb-5 pt-0", className)} {...props} />;
}

export function CardFooter({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex items-center gap-2 px-6 pb-5 pt-0", className)} {...props} />;
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
    <Card className="relative overflow-hidden group hover-lift">
      <CardContent className="p-5">
        {loading ? (
          <div className="space-y-3">
            <div className="skeleton h-4 w-20" />
            <div className="skeleton h-9 w-16" />
            <div className="skeleton h-3 w-28" />
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between mb-3">
              <span className="text-[12px] font-medium text-muted-foreground/60 uppercase tracking-wider">{title}</span>
              {icon && (
                <span className="text-muted-foreground/25 group-hover:text-primary/40 transition-colors duration-200">
                  {icon}
                </span>
              )}
            </div>
            <p className={cn("text-[28px] font-bold tracking-tight leading-none", color)}>
              {value ?? 0}
            </p>
            <div className="flex items-center gap-2 mt-2.5">
              {subtitle && (
                <span className="text-[12px] text-muted-foreground/50">{subtitle}</span>
              )}
              {trend && (
                <span className={cn(
                  "text-[11px] font-semibold inline-flex items-center gap-0.5",
                  trend.positive ? "text-emerald-600" : "text-destructive"
                )}>
                  <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <path d={trend.positive ? "M18 15l-6-6-6 6" : "M6 9l6 6 6-6"} />
                  </svg>
                  {trend.value}
                </span>
              )}
            </div>
            <div className="absolute inset-x-0 bottom-0 h-[2px] bg-gradient-to-r from-transparent via-primary/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
          </>
        )}
      </CardContent>
    </Card>
  );
}
