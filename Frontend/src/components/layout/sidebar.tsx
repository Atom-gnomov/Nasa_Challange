
"use client";

import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { DashboardActivity } from "@/lib/types";
import { cn } from "@/lib/utils";

interface SidebarProps {
  activities: DashboardActivity[];
  selectedActivityId: string | null;
  onSelectActivity: (id: string) => void;
  onAddActivity: () => void;
}

const ActivityIcon = ({ activity, isSelected }: { activity: DashboardActivity, isSelected: boolean }) => {
    const Icon = activity.activity.icon;
    return (
        <div className={cn(
            "w-12 h-12 rounded-lg flex items-center justify-center cursor-pointer transition-all duration-200",
            isSelected ? "bg-blue-600 text-white" : "bg-gray-200 text-gray-600 hover:bg-gray-300"
        )}>
           <Icon className="w-6 h-6" />
        </div>
    )
};

export default function Sidebar({ activities, selectedActivityId, onSelectActivity, onAddActivity }: SidebarProps) {
  const getInitialSelectedId = () => {
    if (selectedActivityId) return selectedActivityId;
    if (activities.length > 0) return activities[0].id;
    return null;
  };
  const currentSelectedId = getInitialSelectedId();

  if (activities.length === 0) {
    return null;
  }

  return (
    <aside className="relative z-10 flex flex-col items-center py-4">
      <div className="bg-gray-100 p-2 rounded-r-2xl shadow-lg flex flex-col items-center gap-4">
        {activities.length > 0 && (
          <div className="flex justify-center">
              <Button
              size="icon"
              className="w-12 h-12 bg-white text-black hover:bg-gray-200 rounded-lg shadow-md"
              onClick={onAddActivity}
              >
              <Plus className="w-8 h-8" />
              </Button>
          </div>
        )}

        {activities.length > 0 && <div className="w-full h-px bg-gray-300 my-2"></div>}

        <div className="flex flex-col gap-3 overflow-y-auto no-scrollbar max-h-[calc(100vh-12rem)]">
          {activities.map(activity => (
               <div key={activity.id} onClick={() => onSelectActivity(activity.id)}>
                  <ActivityIcon
                      activity={activity}
                      isSelected={activity.id === currentSelectedId}
                   />
              </div>
          ))}
        </div>
      </div>
    </aside>
  );
}
