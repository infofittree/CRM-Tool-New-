import { cn } from "@/lib/utils";

export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("skeleton", className)} {...props} />;
}

export function SkeletonCard() {
  return (
    <div className="rounded-xl border border-border/50 bg-card p-6 space-y-4">
      <div className="skeleton h-4 w-1/3" />
      <div className="skeleton h-8 w-1/2" />
      <div className="skeleton h-3 w-2/3" />
    </div>
  );
}

export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-2">
      <div className="skeleton h-10 w-full" />
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skeleton h-12 w-full" />
      ))}
    </div>
  );
}

export function SkeletonChart() {
  return (
    <div className="rounded-xl border border-border/50 bg-card p-6 space-y-4">
      <div className="skeleton h-4 w-1/4" />
      <div className="skeleton h-64 w-full" />
    </div>
  );
}
