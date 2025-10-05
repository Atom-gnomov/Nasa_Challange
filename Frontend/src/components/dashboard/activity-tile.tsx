
"use client";

import Image from "next/image";
import { HelpCircle } from "lucide-react";
import type { Activity } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface ActivityTileProps {
  activity: Activity;
  onSelect: (activity: Activity) => void;
}

export default function ActivityTile({
  activity,
  onSelect,
}: ActivityTileProps) {
  return (
    <TooltipProvider delayDuration={200}>
      <Card
        onClick={() => onSelect(activity)}
        className="cursor-pointer hover:shadow-lg hover:border-primary transition-all duration-200 group relative bg-gray-100 border-gray-200"
      >
        <CardContent className="p-4 flex flex-col items-center justify-center text-center">
          <Image
            src={activity.image.imageUrl}
            alt={activity.name}
            width={128}
            height={128}
            className="rounded-full mb-4 border-4 border-transparent group-hover:border-blue-400/50 transition-colors"
            data-ai-hint={activity.image.imageHint}
          />
          <CardTitle className="text-lg font-semibold flex items-center gap-2 text-gray-800">
            {activity.name}
          </CardTitle>
        </CardContent>
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="absolute top-2 right-2">
              <HelpCircle className="h-5 w-5 text-gray-400 hover:text-gray-600" />
            </div>
          </TooltipTrigger>
          <TooltipContent className="bg-gray-800 text-white border-gray-700">
            <p>{activity.description}</p>
          </TooltipContent>
        </Tooltip>
      </Card>
    </TooltipProvider>
  );
}
