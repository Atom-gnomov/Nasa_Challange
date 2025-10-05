"use client";

import { useEffect, useMemo, useState } from "react";
import { MapContainer, TileLayer, Marker, useMapEvents } from "react-leaflet";
import type { LatLngExpression } from "leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

type Coords = { latitude: number; longitude: number };

const LEAFLET_ASSETS = "https://unpkg.com/leaflet@1.9.4/dist/images/";
const icon = L.icon({
  iconUrl: `${LEAFLET_ASSETS}marker-icon.png`,
  iconRetinaUrl: `${LEAFLET_ASSETS}marker-icon-2x.png`,
  shadowUrl: `${LEAFLET_ASSETS}marker-shadow.png`,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});
L.Marker.prototype.options.icon = icon;

function ClickHandler({ onClick }: { onClick: (coords: Coords) => void }) {
  useMapEvents({
    click(e) {
      onClick({ latitude: e.latlng.lat, longitude: e.latlng.lng });
    },
  });
  return null;
}

export default function MapPicker({
  value,
  onChange,
  height = 340,
  zoom = 10,
}: {
  value?: Coords | null;
  onChange: (coords: Coords) => void;
  height?: number;
  zoom?: number;
}) {
  // Kyiv default center
  const defaultCenter: Coords = { latitude: 50.4501, longitude: 30.5234 };
  const [pos, setPos] = useState<Coords>(value || defaultCenter);

  useEffect(() => {
    if (value) setPos(value);
  }, [value?.latitude, value?.longitude]);

  const center = useMemo<LatLngExpression>(() => [pos.latitude, pos.longitude], [pos]);

  return (
    <div className="w-full rounded-2xl overflow-hidden border border-border shadow-sm">
      <div style={{ height }} className="relative">
        <MapContainer center={center} zoom={zoom} style={{ height: "100%", width: "100%" }}>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/">OSM</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <ClickHandler
            onClick={(c) => {
              setPos(c);
              onChange(c);
            }}
          />
          <Marker
            position={center}
            draggable={true}
            eventHandlers={{
              dragend(e) {
                const m = e.target as L.Marker;
                const ll = m.getLatLng();
                const c = { latitude: ll.lat, longitude: ll.lng };
                setPos(c);
                onChange(c);
              },
            }}
          />
        </MapContainer>
      </div>
      <div className="flex items-center justify-between p-3 text-sm bg-muted/30">
        <div className="font-mono">
          lat: {pos.latitude.toFixed(5)} | lon: {pos.longitude.toFixed(5)}
        </div>
        <button
          className="px-3 py-1 rounded-md bg-primary text-primary-foreground hover:opacity-90"
          onClick={() => onChange(pos)}
        >
          Use this point
        </button>
      </div>
    </div>
  );
}
