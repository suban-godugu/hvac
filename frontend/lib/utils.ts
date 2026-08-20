import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatTemp(val: number | undefined | null, unit: string = "°C"): string {
  if (val === undefined || val === null || isNaN(val)) return `-- ${unit}`;
  return `${val.toFixed(1)}${unit}`;
}

export function formatKW(val: number | undefined | null): string {
  if (val === undefined || val === null || isNaN(val)) return "-- kW";
  return `${val.toFixed(1)} kW`;
}

export function formatPct(val: number | undefined | null): string {
  if (val === undefined || val === null || isNaN(val)) return "-- %";
  return `${val.toFixed(1)}%`;
}
