
"use client";

import { useState } from "react";
import { X, Info, ChevronDown, ChevronUp, Thermometer, Wind, Umbrella, Moon } from "lucide-react";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import type { DashboardActivity, DailyForecast, ActivityParameter, Rating } from "@/lib/types";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";


interface ActivityCardProps {
  item: DashboardActivity;
  onRemove: (id: string) => void;
}

const getParameterIcon = (parameterName: string) => {
    switch (parameterName.toLowerCase()) {
      case "temperature":
      case "air temp":
      case "water temp":
        return <Thermometer className="h-6 w-6 text-gray-500" />;
      case "wind":
      case "wind speed":
        return <Wind className="h-6 w-6 text-gray-500" />;
      case "precipitation":
      case "cloud cover":
      case "snowfall":
      case "pressure":
        return <Umbrella className="h-6 w-6 text-gray-500" />;
      case "moon phase":
        return <Moon className="h-6 w-6 text-gray-500" />;
      default:
        return null;
    }
  };
  

const ParameterWidget = ({ parameter }: { parameter: ActivityParameter }) => {
    return (
        <Card className="bg-gray-50 border-gray-200 flex-1 min-w-[120px] shadow-sm">
            <CardContent className="p-4 flex flex-col items-center justify-center text-center gap-2">
                <p className="text-sm text-gray-600">{parameter.name}</p>
                <p className="text-2xl font-bold text-gray-900">{parameter.value}{parameter.unit}</p>
                {getParameterIcon(parameter.name)}
            </CardContent>
        </Card>
    )
}

const getRatingStyles = (rating: Rating) => {
    switch (rating) {
      case "excellent":
        return {
          textColor: "text-green-800",
          bgColor: "bg-green-100",
          message: "EXCELLENT DAY FOR YOUR ACTIVITY",
        };
      case "good":
        return {
          textColor: "text-lime-800", 
          bgColor: "bg-lime-100",
          message: "GOOD DAY FOR YOUR ACTIVITY",
        };
      case "average":
        return {
          textColor: "text-yellow-800",
          bgColor: "bg-yellow-100",
          message: "AVERAGE DAY FOR YOUR ACTIVITY",
        };
      case "poor":
        return {
          textColor: "text-orange-800",
          bgColor: "bg-orange-100",
          message: "POOR DAY FOR YOUR ACTIVITY",
        };
      case "very poor":
        return {
          textColor: "text-red-800",
          bgColor: "bg-red-100",
          message: "VERY POOR DAY FOR YOUR ACTIVITY",
        };
      default:
        return {
          textColor: "text-gray-800",
          bgColor: "bg-gray-100",
          message: "CONDITIONS SUMMARY UNAVAILABLE",
        };
    }
  };


const ForecastTile = ({ forecast }: { forecast: DailyForecast }) => {
  const [showSummary, setShowSummary] = useState(false);
  const ratingStyles = getRatingStyles(forecast.rating);

  return (
    <Card className={cn("flex flex-col h-full overflow-hidden", "bg-gray-100")}>
      <CardContent className="p-4 flex flex-col flex-grow">
        <div className="flex justify-between items-center mb-4">
          <h4 className="text-xl font-bold text-gray-800">{forecast.date}</h4>
          <div className="flex items-center gap-2">
              <span className="font-bold text-lg text-gray-800">Recommendations</span>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-cyan-700 hover:bg-cyan-100/50 hover:text-cyan-900"
                onClick={() => setShowSummary(!showSummary)}
              >
                <Info className="h-5 w-5" />
              </Button>
          </div>
        </div>
        
        <div className="flex flex-col gap-4">
            <div className="flex flex-row gap-4 flex-wrap">
                {forecast.parameters.map((param) => (
                <ParameterWidget key={param.name} parameter={param} />
                ))}
            </div>
            <Card className={cn("mt-4 p-4 text-center", ratingStyles.bgColor)}>
                <p className={cn("text-lg font-bold", ratingStyles.textColor)}>{ratingStyles.message}</p>
            </Card>
            {showSummary && (
                <Card className="bg-white/80 border-cyan-200 p-4 mt-4">
                     <h4 className="font-medium leading-none text-cyan-800 mb-2">Recommendations</h4>
                     <p className="text-sm text-gray-700 mb-4">
                        {forecast.summary}
                    </p>
                </Card>
            )}
        </div>
      </CardContent>
    </Card>
  );
};


export default function ActivityCard({ item, onRemove }: ActivityCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!item) return null;

  const { activity, location, forecasts, id } = item;
  const visibleForecasts = isExpanded ? forecasts : forecasts.slice(0, 1);

  return (
    <Card className={cn(
      "bg-white border-none p-6 rounded-2xl shadow-xl relative text-gray-900 w-full max-w-6xl",
      isExpanded && "mb-6"
    )}>
      <Button
        variant="ghost"
        size="icon"
        className="absolute top-4 right-4 h-8 w-8 rounded-full text-gray-400 hover:bg-gray-200 hover:text-gray-900"
        onClick={() => onRemove(id)}
        aria-label="Remove activity"
      >
        <X className="h-5 w-5" />
      </Button>

      <CardContent className="p-0 grid grid-cols-1 md:grid-cols-3 gap-8 items-start">
        {/* Left Column */}
        <div className="md:col-span-1 flex flex-col gap-4">
          <div className="flex items-center gap-3">
            <h2 className="text-4xl font-bold">{activity.name}</h2>
          </div>
          <Image
            src={activity.image.imageUrl}
            alt={activity.name}
            width={400}
            height={250}
            className="rounded-lg object-contain w-full"
            data-ai-hint={activity.image.imageHint}
          />
          <p className="text-gray-600">Location: {location}</p>
          <Separator className="my-2" />
        </div>

        {/* Right Column */}
        <div className="md:col-span-2 flex flex-col gap-6">
          <h3 className="text-4xl font-bold text-gray-800">
              FORECAST
          </h3>
          <div className="grid grid-cols-1 gap-4">
            {visibleForecasts.map((forecast, index) => (
              <ForecastTile key={index} forecast={forecast} />
            ))}
          </div>
          {forecasts.length > 1 && (
            <Button
              variant="outline"
              onClick={() => setIsExpanded(!isExpanded)}
              className="w-full"
            >
              {isExpanded ? (
                <>
                  <ChevronUp className="mr-2 h-4 w-4" />
                  Show Less
                </>
              ) : (
                <>
                  <ChevronDown className="mr-2 h-4 w-4" />
                  Show 7 more days
                </>
              )}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
