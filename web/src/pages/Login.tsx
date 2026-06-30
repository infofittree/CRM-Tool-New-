import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { User, Lock, ChevronRight, ArrowUpRight, TrendingUp, Users, CheckCircle2 } from "lucide-react";

const DECORATIVE_CIRCLES = [
  { size: 320, top: "10%", right: "-5%", opacity: 0.07, blur: "80px" },
  { size: 200, bottom: "15%", left: "-3%", opacity: 0.05, blur: "60px" },
  { size: 150, top: "40%", left: "20%", opacity: 0.04, blur: "50px" },
];

export default function Login() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => { setMounted(true); }, []);

  useEffect(() => {
    if (user) navigate("/", { replace: true });
  }, [user, navigate]);

  if (user) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    const err = await login(username, password);
    setLoading(false);
    if (err) {
      setError(err);
    } else {
      navigate("/", { replace: true });
    }
  };

  return (
    <div className="min-h-screen flex relative overflow-hidden bg-[radial-gradient(ellipse_at_top_right,hsl(152_30%_97%)_0%,transparent_60%),radial-gradient(ellipse_at_bottom_left,hsl(152_20%_95%)_0%,transparent_50%)]">
      {/* ── Left Panel (60%) ── */}
      <div className="hidden lg:flex lg:w-[60%] relative overflow-hidden">
        {/* Deep green gradient background */}
        <div className="absolute inset-0 bg-gradient-to-br from-[hsl(152_55%_22%)] via-[hsl(152_50%_26%)] to-[hsl(152_55%_18%)]" />

        {/* Layered abstract shapes */}
        <div className="absolute inset-0 opacity-[0.04]">
          <svg className="w-full h-full" viewBox="0 0 1200 900" preserveAspectRatio="none">
            <defs>
              <pattern id="dots" width="40" height="40" patternUnits="userSpaceOnUse">
                <circle cx="20" cy="20" r="1" fill="white" />
              </pattern>
              <linearGradient id="glowGrad" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="white" stopOpacity="0.08" />
                <stop offset="100%" stopColor="white" stopOpacity="0" />
              </linearGradient>
            </defs>
            <rect width="100%" height="100%" fill="url(#dots)" />
          </svg>
        </div>

        {/* Floating decorative circles */}
        {DECORATIVE_CIRCLES.map((c, i) => (
          <div
            key={i}
            className="absolute rounded-full bg-white"
            style={{
              width: c.size,
              height: c.size,
              top: c.top,
              right: c.right,
              bottom: c.bottom,
              left: c.left,
              opacity: c.opacity,
              filter: `blur(${c.blur})`,
            }}
          />
        ))}

        {/* Geometric accent lines */}
        <div className="absolute top-1/3 right-0 w-64 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent rotate-45" />
        <div className="absolute bottom-1/3 left-0 w-48 h-px bg-gradient-to-r from-transparent via-white/8 to-transparent -rotate-12" />

        {/* Subtle data-inspired grid accent */}
        <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-white/[0.03] to-transparent" />

        {/* Content */}
        <div className="relative z-10 flex flex-col justify-center px-16 xl:px-20 py-24 w-full">
          {/* Brand + Tagline */}
          <div className={`transition-all duration-700 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-6"}`}>
            <div className="flex items-center gap-3 mb-10">
              <div className="w-11 h-11 rounded-xl bg-white/15 backdrop-blur-sm flex items-center justify-center shadow-lg shadow-black/10">
                <svg className="w-6 h-6 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                </svg>
              </div>
              <span className="text-white/70 text-sm font-medium tracking-widest uppercase">FitTree CRM</span>
            </div>

            <h1 className="text-5xl xl:text-6xl font-bold text-white leading-[1.1] tracking-tight mb-6">
              Grow Relationships.
              <br />
              <span className="text-white/90">Close More Deals.</span>
            </h1>

            <p className="text-lg text-white/60 leading-relaxed max-w-lg mb-12">
              Track leads, manage follow-ups, and monitor team performance from a single intelligent workspace.
            </p>
          </div>

          {/* Mini CRM Dashboard Mockup */}
          <div className={`transition-all duration-700 delay-200 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-6"}`}>
            <div className="relative">
              {/* Glass card container */}
              <div className="bg-white/[0.06] backdrop-blur-xl rounded-2xl border border-white/10 p-5 shadow-2xl shadow-black/20 max-w-2xl">
                {/* Mockup header */}
                <div className="flex items-center justify-between mb-5">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-emerald-400" />
                    <div className="w-2 h-2 rounded-full bg-amber-400" />
                    <div className="w-2 h-2 rounded-full bg-white/20" />
                  </div>
                  <span className="text-[11px] text-white/30 font-medium tracking-wider uppercase">Dashboard Overview</span>
                </div>

                {/* Mock KPI row */}
                <div className="grid grid-cols-3 gap-3 mb-5">
                  {[
                    { label: "Active Leads", value: "248", icon: Users, color: "text-emerald-400" },
                    { label: "Conversion", value: "23.5%", icon: TrendingUp, color: "text-amber-400" },
                    { label: "Closed", value: "58", icon: CheckCircle2, color: "text-blue-400" },
                  ].map((kpi, i) => (
                    <div key={i} className="bg-white/[0.05] rounded-xl p-3 border border-white/[0.06]">
                      <div className="flex items-center gap-2 mb-2">
                        <kpi.icon className={`w-3.5 h-3.5 ${kpi.color}`} />
                        <span className="text-[10px] text-white/40 font-medium">{kpi.label}</span>
                      </div>
                      <p className="text-xl font-bold text-white">{kpi.value}</p>
                    </div>
                  ))}
                </div>

                {/* Mock mini chart */}
                <div className="bg-white/[0.04] rounded-xl p-4 border border-white/[0.06] mb-4">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-[11px] text-white/50 font-medium">Weekly Engagement</span>
                    <ArrowUpRight className="w-3 h-3 text-emerald-400" />
                  </div>
                  <div className="flex items-end gap-2 h-20">
                    {[35, 48, 42, 65, 58, 72, 88].map((h, i) => (
                      <div key={i} className="flex-1 flex flex-col items-center gap-1">
                        <div
                          className="w-full rounded-t-md bg-gradient-to-t from-emerald-500/60 to-emerald-400/30"
                          style={{ height: `${h}%` }}
                        />
                        <span className="text-[9px] text-white/20">M{i + 1}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Mock team row */}
                <div className="flex items-center gap-3">
                  {["RK", "SP", "VJ", "PS"].map((initials, i) => (
                    <div
                      key={i}
                      className="w-8 h-8 rounded-full bg-gradient-to-br flex items-center justify-center text-[10px] font-bold text-white shadow-sm"
                      style={{
                        backgroundImage: i === 0
                          ? "linear-gradient(to bottom right, hsl(152, 60%, 40%), hsl(152, 60%, 32%))"
                          : i === 1
                          ? "linear-gradient(to bottom right, #a855f7, #7c3aed)"
                          : i === 2
                          ? "linear-gradient(to bottom right, #f59e0b, #d97706)"
                          : "linear-gradient(to bottom right, #06b6d4, #0891b2)",
                      }}
                    >
                      {initials}
                    </div>
                  ))}
                  <div className="flex-1" />
                  <span className="text-[10px] text-white/30">4 team members active</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Right Panel (40%) ── */}
      <div className="flex-1 flex items-center justify-center p-6 lg:p-10">
        <div className={`w-full max-w-sm transition-all duration-700 delay-100 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"}`}>
          {/* Mobile brand */}
          <div className="lg:hidden mb-10 text-center">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary to-primary/70 flex items-center justify-center mx-auto mb-4 shadow-lg shadow-primary/20">
              <svg className="w-7 h-7 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
              </svg>
            </div>
            <h1 className="text-xl font-bold text-foreground">FitTree CRM</h1>
          </div>

          {/* Login Card */}
          <div className="bg-white dark:bg-card rounded-2xl border border-border/40 shadow-[var(--shadow-elevated)] p-8 lg:p-10">
            {/* Welcome */}
            <div className="mb-8">
              <h2 className="text-2xl font-bold tracking-tight text-foreground">Welcome back</h2>
              <p className="text-[13px] text-muted-foreground/55 mt-1.5">Sign in to continue to FitTree CRM</p>
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-5">
              {error && (
                <div className="p-3.5 rounded-xl bg-destructive/8 border border-destructive/15 text-destructive text-sm flex items-center gap-2.5 animate-in fade-in slide-in-from-top-2 duration-200">
                  <svg className="w-4 h-4 shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10" />
                    <path d="M12 8v4m0 4h.01" />
                  </svg>
                  <span>{error}</span>
                </div>
              )}

              <div className="space-y-1.5">
                <label className="text-[13px] font-medium text-foreground/70">Username</label>
                <div className="relative">
                  <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground/35 pointer-events-none" />
                  <input
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="Enter your username"
                    required
                    autoFocus
                    className="w-full h-12 pl-10 pr-4 rounded-xl border border-input bg-background text-sm transition-all duration-180 placeholder:text-muted-foreground/35 hover:border-muted-foreground/25 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/15 focus-visible:border-primary/40"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-[13px] font-medium text-foreground/70">Password</label>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground/35 pointer-events-none" />
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your password"
                    required
                    className="w-full h-12 pl-10 pr-4 rounded-xl border border-input bg-background text-sm transition-all duration-180 placeholder:text-muted-foreground/35 hover:border-muted-foreground/25 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/15 focus-visible:border-primary/40"
                  />
                </div>
              </div>

              <Button
                type="submit"
                className="w-full h-12 text-[15px] font-semibold rounded-xl bg-gradient-to-r from-primary to-[hsl(152_55%_28%)] hover:from-[hsl(152_55%_28%)] hover:to-primary shadow-lg shadow-primary/20 hover:shadow-xl hover:shadow-primary/25 active:scale-[0.98] transition-all duration-200"
                loading={loading}
              >
                {loading ? "Signing in..." : "Sign in"}
              </Button>
            </form>
          </div>

          {/* Security message */}
          <p className="text-xs text-muted-foreground/50 text-center mt-6 flex items-center justify-center gap-1.5">
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0110 0v4" />
            </svg>
            Secure company access &mdash; data encrypted in transit
          </p>
        </div>
      </div>
    </div>
  );
}
