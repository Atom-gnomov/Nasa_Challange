"use client";

import type { DashboardActivity } from "@/lib/types";
import ActivityCard from "./activity-card";
import EmptyDashboard from "./empty-dashboard";

interface DashboardProps {
  activities: DashboardActivity[];
  onRemoveActivity: (id: string) => void;
}

// This component is no longer used in the main page structure
// but is kept for potential future use or if the layout changes back.
export default function Dashboard({
  activities,
  onRemoveActivity,
}: DashboardProps) {
  if (activities.length === 0) {
    return <EmptyDashboard onAddActivity={() => {}} />;
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 2xl:grid-cols-3 gap-6">
      {activities.map((item) => (
        <ActivityCard
          key={item.id}
          item={item}
          onRemove={onRemoveActivity}
        />
      ))}
    </div>
  );
}
