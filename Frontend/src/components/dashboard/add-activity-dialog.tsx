
"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Loader2, MapPin, Crosshair } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { useToast } from "@/hooks/use-toast";

import { ACTIVITIES } from "@/lib/activities";
import type { Activity } from "@/lib/types";
import ActivityTile from "./activity-tile";

interface AddActivityDialogProps {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  onAddActivity: (activity: Activity, location: string, coordinates: { latitude: number; longitude: number } | null) => Promise<void>;
}

const formSchema = z.object({
  location: z.string().min(2, {
    message: "Location must be at least 2 characters.",
  }),
});

type Coordinates = {
  latitude: number;
  longitude: number;
} | null;

export default function AddActivityDialog({
  isOpen,
  onOpenChange,
  onAddActivity,
}: AddActivityDialogProps) {
  const [step, setStep] = useState<"select" | "configure">("select");
  const [selectedActivity, setSelectedActivity] = useState<Activity | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isGeolocating, setIsGeolocating] = useState(false);
  const [coordinates, setCoordinates] = useState<Coordinates>(null);
  const { toast } = useToast();

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      location: "",
    },
  });

  const handleGeolocate = () => {
    if (!navigator.geolocation) {
      toast({
        variant: "destructive",
        title: "Geolocation is not supported by your browser.",
      });
      return;
    }

    setIsGeolocating(true);
    setCoordinates(null); // Reset coordinates on new request

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        setCoordinates({ latitude, longitude });
        form.setValue("location", `Lat: ${latitude.toFixed(4)}, Lon: ${longitude.toFixed(4)}`);
        toast({
          title: "Location found!",
          description: "Coordinates have been set.",
        });
        setIsGeolocating(false);
      },
      (error) => {
        console.error("Geolocation error:", error);
        toast({
          variant: "destructive",
          title: "Geolocation failed.",
          description: "Please ensure you've granted location permissions.",
        });
        setIsGeolocating(false);
      }
    );
  };


  const handleActivitySelect = (activity: Activity) => {
    setSelectedActivity(activity);
    setStep("configure");
  };

  const handleBack = () => {
    setStep("select");
    form.reset();
    setCoordinates(null);
  };

  const handleClose = () => {
    onOpenChange(false);
    // Reset state after a short delay to allow closing animation
    setTimeout(() => {
      setStep("select");
      setSelectedActivity(null);
      form.reset();
      setIsSubmitting(false);
      setCoordinates(null);
    }, 300);
  };

  const onSubmit = async (values: z.infer<typeof formSchema>) => {
    if (!selectedActivity) return;

    // If coordinates are not set by geolocation, we don't proceed
    // The parent component will handle the null coordinates case.
    if (!coordinates) {
      toast({
        variant: 'destructive',
        title: 'Missing Coordinates',
        description: 'Please use the geolocation button to set your location.',
      });
      return;
    }

    setIsSubmitting(true);
    await onAddActivity(selectedActivity, values.location, coordinates);
    setIsSubmitting(false);
    if (form.formState.isSubmitSuccessful) {
        handleClose();
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[600px] transition-all duration-300 bg-white">
        {step === "select" && (
          <>
            <DialogHeader>
              <DialogTitle className="text-2xl font-headline text-gray-900">Choose an Activity</DialogTitle>
              <DialogDescription className="text-gray-500">
                Select an activity you want to plan. Hover over the '?' for more info.
              </DialogDescription>
            </DialogHeader>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 py-4 max-h-[60vh] overflow-y-auto">
              {ACTIVITIES.map((activity) => (
                <ActivityTile
                  key={activity.id}
                  activity={activity}
                  onSelect={handleActivitySelect}
                />
              ))}
            </div>
          </>
        )}
        {step === "configure" && selectedActivity && (
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)}>
              <DialogHeader>
                <DialogTitle className="text-2xl font-headline text-gray-900">{selectedActivity.name}</DialogTitle>
                <DialogDescription className="text-gray-500">
                  Enter the location for your activity. The forecast will be based on this location.
                </DialogDescription>
              </DialogHeader>
              <div className="py-4">
                <FormField
                  control={form.control}
                  name="location"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="flex items-center gap-2 text-gray-700">
                        <MapPin className="h-4 w-4" /> Location
                      </FormLabel>
                      <FormControl>
                        <div className="relative">
                            <Input placeholder="e.g., San Francisco, CA" {...field} className="bg-gray-100 border-gray-300 text-gray-900 pr-10" />
                            <Button
                                type="button"
                                variant="ghost"
                                size="icon"
                                className="absolute right-1 top-1/2 -translate-y-1/2 h-8 w-8 text-gray-500 hover:bg-gray-200"
                                onClick={handleGeolocate}
                                disabled={isGeolocating}
                                aria-label="Use my current location"
                            >
                                {isGeolocating ? <Loader2 className="h-5 w-5 animate-spin"/> :<Crosshair className="h-5 w-5" />}
                            </Button>
                        </div>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={handleBack} disabled={isSubmitting}>
                  Back
                </Button>
                <Button type="submit" disabled={isSubmitting} className="bg-blue-600 hover:bg-blue-700 text-white">
                  {isSubmitting ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Adding...
                    </>
                  ) : (
                    "Add Activity"
                  )}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        )}
      </DialogContent>
    </Dialog>
  );
}
