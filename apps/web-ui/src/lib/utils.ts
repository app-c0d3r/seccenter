import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

// Hilfsfunktion zum Kombinieren von CSS-Klassen mit Tailwind-Merge
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
