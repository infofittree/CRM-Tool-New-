import { cn } from "@/lib/utils";

function Spinner({ className }: { className?: string }) {
  return (
    <svg className={cn("animate-spin", className || "h-4 w-4")} viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-20" />
      <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" className="opacity-80" />
    </svg>
  );
}

const variants: Record<string, string> = {
  default:
    "bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm hover:shadow-md active:shadow-sm",
  destructive:
    "bg-destructive text-destructive-foreground hover:bg-destructive/90 shadow-sm",
  outline:
    "border border-border bg-background hover:bg-muted/60 hover:border-muted-foreground/20",
  secondary:
    "bg-secondary text-secondary-foreground hover:bg-secondary/80",
  ghost:
    "hover:bg-muted/60 hover:text-foreground",
  link:
    "text-primary underline-offset-4 hover:underline",
};

const sizes: Record<string, string> = {
  default: "h-10 px-4 py-2 text-sm",
  sm: "h-9 rounded-md px-3 text-xs",
  lg: "h-11 rounded-lg px-6 text-base",
  icon: "h-10 w-10",
};

export function Button({
  className,
  variant = "default",
  size = "default",
  loading,
  children,
  disabled,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: keyof typeof variants;
  size?: keyof typeof sizes;
  loading?: boolean;
}) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg font-medium",
        "transition-all duration-150 ease-out",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
        "disabled:pointer-events-none disabled:opacity-50",
        "active:scale-[0.97]",
        variants[variant],
        sizes[size],
        className,
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <Spinner />}
      {children}
    </button>
  );
}
