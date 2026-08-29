import { useEffect, useRef, useState } from "react";
import { loadGoogleMaps } from "../lib/googleMaps";

export interface MapLocation {
  label: string;
  /** A real, geocodable place name - e.g. "Hyderabad, Telangana, India".
   * Never a fabricated street address. */
  query: string;
}

interface LocationMapProps {
  locations: MapLocation[];
  /** Geocoded if no locations resolve, or used as the sole marker when
   * `locations` is empty (e.g. a service-region overview). */
  fallbackQuery: string;
  fallbackLabel: string;
  height?: number;
}

/** Renders a live Google Map with markers geocoded from real place names
 * (districts/territories already on file, or a confirmed service region) -
 * never from invented coordinates or addresses. Degrades to a plain,
 * honest placeholder when no API key is configured. */
export function LocationMap({ locations, fallbackQuery, fallbackLabel, height = 340 }: LocationMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "unavailable">("loading");

  useEffect(() => {
    let cancelled = false;

    loadGoogleMaps().then(async (maps) => {
      if (cancelled) return;
      if (!maps || !containerRef.current) {
        setStatus("unavailable");
        return;
      }

      const geocoder = new maps.maps.Geocoder();
      const geocode = (query: string) =>
        new Promise<google.maps.LatLng | null>((resolve) => {
          geocoder.geocode({ address: query }, (results, geoStatus) => {
            if (geoStatus === "OK" && results && results[0]) resolve(results[0].geometry.location);
            else resolve(null);
          });
        });

      const targets = locations.length > 0 ? locations : [{ label: fallbackLabel, query: fallbackQuery }];
      const resolved: { label: string; position: google.maps.LatLng }[] = [];
      for (const target of targets) {
        const position = await geocode(target.query);
        if (position) resolved.push({ label: target.label, position });
      }

      if (cancelled) return;
      if (resolved.length === 0) {
        setStatus("unavailable");
        return;
      }

      const map = new maps.maps.Map(containerRef.current, {
        zoom: resolved.length > 1 ? 8 : 10,
        center: resolved[0].position,
        mapTypeControl: false,
        streetViewControl: false,
        fullscreenControl: false,
      });

      const bounds = new maps.maps.LatLngBounds();
      resolved.forEach(({ label, position }) => {
        const marker = new maps.maps.Marker({ position, map, title: label });
        const info = new maps.maps.InfoWindow({ content: `<strong>${label}</strong>` });
        marker.addListener("click", () => info.open({ map, anchor: marker }));
        bounds.extend(position);
      });
      if (resolved.length > 1) map.fitBounds(bounds);

      setStatus("ready");
    });

    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (status === "unavailable") {
    return (
      <div className="empty-state" style={{ height }}>
        Map unavailable right now &mdash; try again later.
      </div>
    );
  }

  return (
    <div style={{ position: "relative", height, borderRadius: "var(--radius-md)", overflow: "hidden", border: "1px solid var(--color-border)" }}>
      {status === "loading" && <div className="loading-state">Loading map...</div>}
      <div ref={containerRef} style={{ width: "100%", height: "100%", display: status === "ready" ? "block" : "none" }} />
    </div>
  );
}
