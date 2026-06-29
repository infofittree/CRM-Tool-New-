import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { format, parseISO, differenceInDays } from "date-fns";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: string | Date | null | undefined): string {
  if (!date) return "—";
  const d = typeof date === "string" ? parseISO(date) : date;
  return format(d, "MMM d, yyyy");
}

export function formatDateTime(date: string | Date | null | undefined): string {
  if (!date) return "—";
  const d = typeof date === "string" ? parseISO(date) : date;
  return format(d, "MMM d, yyyy h:mm a");
}

export function daysFromNow(date: string | Date | null | undefined): number | null {
  if (!date) return null;
  const d = typeof date === "string" ? parseISO(date) : date;
  return differenceInDays(d, new Date());
}

export function scoreBand(score: number): { label: string; color: string } {
  if (score >= 80) return { label: "HOT", color: "text-band-hot" };
  if (score >= 55) return { label: "WARM", color: "text-band-warm" };
  return { label: "COLD", color: "text-band-cold" };
}
