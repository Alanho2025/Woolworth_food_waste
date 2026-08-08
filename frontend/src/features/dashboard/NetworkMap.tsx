import { MapPin, Navigation } from "lucide-react";

import type { DashboardResponse } from "@/shared/api/client";
import {
  ARTERIALS,
  AUCKLAND_BOUNDS,
  ISTHMUS,
  NORTH_SHORE,
} from "@/shared/map/auckland";
import { Attribution } from "@/shared/ui/Attribution";

type Location = DashboardResponse["communities"][number]["location"];

function point([latitude, longitude]: readonly [number, number]) {
  const x =
    ((longitude - AUCKLAND_BOUNDS.west) /
      (AUCKLAND_BOUNDS.east - AUCKLAND_BOUNDS.west)) *
    1000;
  const y =
    ((AUCKLAND_BOUNDS.north - latitude) /
      (AUCKLAND_BOUNDS.north - AUCKLAND_BOUNDS.south)) *
    680;
  return `${x.toFixed(1)},${y.toFixed(1)}`;
}

function position(location: Location) {
  return point([location.latitude, location.longitude]);
}

export function NetworkMap({ data }: { readonly data: DashboardResponse }) {
  const stores = Array.from(
    new Map(
      data.donations.map((donation) => [
        donation.store_id,
        donation.store_location,
      ]),
    ).values(),
  );

  return (
    <section
      className="network-map panel"
      aria-label="Live Auckland food rescue network"
      data-testid="network-map"
    >
      <div className="panel-heading map-heading">
        <div>
          <span className="eyebrow">Network geography</span>
          <h2>Auckland food rescue network</h2>
        </div>
        <span className="live-label">
          <span className="network-pulse" /> {data.communities.length} community
          partners online
        </span>
      </div>
      <div className="map-canvas">
        <svg
          viewBox="0 0 1000 680"
          role="img"
          aria-label="Stylised map of Auckland showing stores, communities and drivers"
        >
          <rect width="1000" height="680" className="map-water" />
          <polygon
            points={NORTH_SHORE.map(point).join(" ")}
            className="map-land"
          />
          <polygon points={ISTHMUS.map(point).join(" ")} className="map-land" />
          {ARTERIALS.map((road) => (
            <polyline
              key={road.name}
              points={road.path.map(point).join(" ")}
              className={road.motorway ? "map-road motorway" : "map-road"}
            />
          ))}
          {stores.map((store) => {
            const [x, y] = position(store).split(",");
            return (
              <g key={store.name} transform={`translate(${x} ${y})`}>
                <circle r="18" className="store-halo" />
                <rect
                  x="-8"
                  y="-8"
                  width="16"
                  height="16"
                  rx="4"
                  className="store-marker"
                />
                <title>{store.name}</title>
              </g>
            );
          })}
          {data.communities.map((community) => {
            const [x, y] = position(community.location).split(",");
            return (
              <g
                key={community.community_id}
                transform={`translate(${x} ${y})`}
              >
                <circle r="16" className="community-halo" />
                <circle
                  r="7"
                  className={
                    community.is_open
                      ? "community-marker open"
                      : "community-marker"
                  }
                />
                <title>
                  {community.name} · {community.remaining_capacity_kg} kg
                  capacity
                </title>
              </g>
            );
          })}
          {data.drivers.map((driver) => {
            const [x, y] = position(driver.start_location).split(",");
            return (
              <g key={driver.driver_id} transform={`translate(${x} ${y})`}>
                <path
                  d="M -10 7 L 0 -11 L 10 7 L 0 3 Z"
                  className="driver-marker"
                />
                <title>
                  {driver.name} ·{" "}
                  {driver.is_available ? "Available" : "Assigned"}
                </title>
              </g>
            );
          })}
        </svg>
        <div className="map-legend">
          <span>
            <i className="legend-square" /> Woolworths
          </span>
          <span>
            <i className="legend-dot" /> Community
          </span>
          <span>
            <Navigation size={13} /> Driver
          </span>
        </div>
        <Attribution />
      </div>
      <div className="map-stat-row">
        <span>
          <MapPin size={15} /> Mount Eden coordination area
        </span>
        <strong>Simulated network · no live GPS</strong>
      </div>
    </section>
  );
}
