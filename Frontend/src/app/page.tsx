"use client";

import { useState } from "react";
import { format } from "date-fns";

import type { DashboardActivity, Activity, DailyForecast, Rating } from "@/lib/types";
import Header from "@/components/layout/header";
import AddActivityDialog from "@/components/dashboard/add-activity-dialog";
import { useToast } from "@/hooks/use-toast";
import ActivityCard from "@/components/dashboard/activity-card";
import EmptyDashboard from "@/components/dashboard/empty-dashboard";
import Sidebar from "@/components/layout/sidebar";
import LoadingSpinner from "@/components/dashboard/loading-spinner";

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000").replace(/\/$/, "");

export default function Home() {
  const [activities, setActivities] = useState<DashboardActivity[]>([]);
  const [selectedActivityId, setSelectedActivityId] = useState<string | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();


  const handleAddActivity = async (
    activity: Activity,
    location: string,
    coordinates: { latitude: number; longitude: number } | null
  ) => {
    if (!coordinates) {
      toast({
        variant: "destructive",
        title: "Error",
        description:
          "Could not get location coordinates. Please use geolocation or enter a valid location.",
      });
      return;
    }

    setIsLoading(true);

    try {
      const url = `${API_BASE}/api/predict/fishing`;

      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          lat: coordinates.latitude,
          lon: coordinates.longitude, // backend also accepts "lng"
          // Optionally include a specific date:
          // date: "2025-10-20"
        }),
      });

      const data = await response
        .json()
        .catch(() => ({ ok: false, error: "InvalidJSON", message: "Response was not JSON" }));

      if (!response.ok || (data && data.ok === false)) {
        const msg =
          (data && (data.message || data.error)) ||
          `API request failed with status ${response.status}`;
        throw new Error(msg);
      }

      // Support both shapes: { rows: [...] } or { results: [...] }
      const rows: any[] = Array.isArray(data?.rows)
        ? data.rows
        : Array.isArray(data?.results)
        ? data.results
        : [];

      if (rows.length === 0) {
        throw new Error("Backend returned no forecast rows (expected `rows` or `results`).");
      }

      const forecastsWithSummaries: DailyForecast[] = rows.map((result: any) => {
        const d = new Date(result.date);

        // Normalize rating to the union type if present; default to "unknown"
        const rating = String(result.rating ?? "unknown").toLowerCase() as Rating;

        return {
          date: format(d, "EEE, MMM d"),
          rating,
          summary: result.recommendations ?? result.justification ?? "No summary",
          parameters: [
            { name: "Air Temp",   value: Number(result.air_temp_C).toFixed(1),     unit: "°C" },
            { name: "Pressure",   value: Number(result.pressure_kPa).toFixed(1),   unit: "kPa" },
            { name: "Wind Speed", value: Number(result.wind_speed_m_s).toFixed(1), unit: "m/s" },
            { name: "Moon Phase", value: String(result.moon_phase ?? ""),          unit: ""    },
            { name: "Water Temp", value: Number(result.water_temp_C).toFixed(1),   unit: "°C" },
          ],
        };
      });

      const newActivity: DashboardActivity = {
        id: crypto.randomUUID(),
        activity,
        location,
        forecasts: forecastsWithSummaries,
      };

      setActivities((prev) => [...prev, newActivity]);
      setSelectedActivityId(newActivity.id);
      setIsDialogOpen(false);
    } catch (error: any) {
      console.error("Failed to add activity:", error);
      toast({
        variant: "destructive",
        title: "Error",
        description: `Failed to fetch forecast. ${error?.message || error}`,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleRemoveActivity = (id: string) => {
    setActivities((prev) => {
      const newActivities = prev.filter((act) => act.id !== id);
      if (selectedActivityId === id) {
        setSelectedActivityId(newActivities.length > 0 ? newActivities[0].id : null);
      }
      return newActivities;
    });
  };

  const selectedActivity =
    activities.find((act) => act.id === selectedActivityId) ??
    (activities.length > 0 ? activities[0] : null);

  return (
    <div className="flex flex-col h-screen bg-transparent text-foreground">
      <div className="absolute inset-0 bg-black/30 z-[-1]" />
      <Header />
      {isLoading ? (
        <LoadingSpinner />
      ) : (
        <div className="flex flex-1 overflow-hidden">
          <Sidebar
            activities={activities}
            selectedActivityId={selectedActivityId}
            onSelectActivity={setSelectedActivityId}
            onAddActivity={() => setIsDialogOpen(true)}
          />
          <main className="flex-1 p-6 overflow-y-auto">
            <div className="flex justify-center items-start h-full">
              {selectedActivity ? (
                <ActivityCard item={selectedActivity} onRemove={handleRemoveActivity} />
              ) : (
                <EmptyDashboard onAddActivity={() => setIsDialogOpen(true)} />
              )}
            </div>
          </main>
        </div>
      )}

      <AddActivityDialog
        isOpen={isDialogOpen}
        onOpenChange={setIsDialogOpen}
        onAddActivity={handleAddActivity}
      />
    </div>
  );
}
