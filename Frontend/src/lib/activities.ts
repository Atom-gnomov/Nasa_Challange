
import {
  Fish,
  Tent,
  Wind, // Using Wind as a placeholder for Drone
  Bike,
  PartyPopper,
  type LucideIcon,
  Footprints,
  Moon,
  Thermometer,
} from "lucide-react";
import type { Activity } from "./types";
import { PlaceHolderImages } from "./placeholder-images";

const findImage = (id: string) => {
  const image = PlaceHolderImages.find((img) => img.id === id);
  if (!image) {
    return {
      id: "default",
      imageUrl: "https://picsum.photos/seed/default/200/200",
      description: "Default activity image",
      imageHint: "placeholder",
    };
  }
  return image;
};

export const ACTIVITIES: Activity[] = [
  {
    id: "fishing",
    name: "FISHING",
    description: "Relax by the water and try to catch some fish.",
    icon: Fish,
    image: findImage("fishing"),
     parameters: [
        { id: "air_temp_C", name: "Air Temp", unit: "°C", range: [5, 30] },
        { id: "pressure_kPa", name: "Pressure", unit: "kPa", range: [99, 103] },
        { id: "wind_speed_m_s", name: "Wind Speed", unit: "m/s", range: [0, 5] },
        { id: "moon_phase", name: "Moon Phase", unit: "", range: [0, 1] },
        { id: "estimated_water_temp_C", name: "Water Temp", unit: "°C", range: [10, 25] },
    ],
  },
  {
    id: "camping",
    name: "CAMPING",
    description: "Set up a tent and enjoy the great outdoors.",
    icon: Tent,
    image: findImage("camping"),
    parameters: [
        { id: "temperature", name: "Temperature", unit: "°C", range: [5, 25] },
        { id: "wind", name: "Wind", unit: "km/h", range: [0, 20] },
        { id: "precipitation", name: "Precipitation", unit: "%", range: [0, 40] },
    ],
  },
  {
    id: "drone_flight",
    name: "DRONE FLIGHT",
    description: "Fly a drone and capture stunning aerial views.",
    icon: Wind,
    image: findImage("drone_flight"),
    parameters: [
        { id: "wind", name: "Wind", unit: "km/h", range: [0, 25] },
        { id: "visibility", name: "Visibility", unit: "km", range: [5, 50] },
        { id: "precipitation", name: "Precipitation", unit: "%", range: [0, 10] },
    ],
  },
  {
    id: "running",
    name: "RUNNING",
    description: "Go for a run to stay fit.",
    icon: Footprints,
    image: findImage("running"),
    parameters: [
        { id: "temperature", name: "Temperature", unit: "°C", range: [10, 30] },
        { id: "wind", name: "Wind", unit: "km/h", range: [0, 25] },
        { id: "precipitation", name: "Precipitation", unit: "%", range: [0, 20] },
    ],
  },
  {
    id: "cycling",
    name: "CYCLING",
    description: "Go for a bike ride.",
    icon: Bike,
    image: findImage("cycling"),
    parameters: [
        { id: "temperature", name: "Temperature", unit: "°C", range: [10, 30] },
        { id: "wind", name: "Wind", unit: "km/h", range: [0, 25] },
        { id: "precipitation", name: "Precipitation", unit: "%", range: [0, 20] },
    ],
  },
  {
    id: "festivals",
    name: "FESTIVALS",
    description: "Enjoy live music, food, and fun at an outdoor festival.",
    icon: PartyPopper,
    image: findImage("festivals"),
    parameters: [
        { id: "temperature", name: "Temperature", unit: "°C", range: [15, 30] },
        { id: "precipitation", name: "Precipitation", unit: "%", range: [0, 30] },
        { id: "wind", name: "Wind", unit: "km/h", range: [0, 20] },
    ],
  },
];
