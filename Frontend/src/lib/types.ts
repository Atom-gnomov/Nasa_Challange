
import type { LucideIcon } from "lucide-react";
import type { ImagePlaceholder } from "./placeholder-images";

export interface ActivityParameterDefinition {
  id: string;
  name: string;
  unit: string;
  range: [number, number];
}

export interface Activity {
  id: string;
  name: string;
  description: string;
  icon: LucideIcon;
  image: ImagePlaceholder;
  parameters: ActivityParameterDefinition[];
}

export interface ActivityParameter {
  name: string;
  value: string;
  unit: string;
}

export type Rating = "very poor" | "poor" | "average" | "good" | "excellent";


export interface DailyForecast {
  date: string;
  parameters: ActivityParameter[];
  summary: string;
  rating: Rating;
}

export interface DashboardActivity {
  id: string;
  activity: Activity;
  location: string;
  forecasts: DailyForecast[];
}
