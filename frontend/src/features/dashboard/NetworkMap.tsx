import { MapPin, Navigation } from "lucide-react";

import type { DashboardResponse } from "@/shared/api/client";
import {
  CBD_WOOLWORTHS_STORES,
  DEFAULT_CBD_WOOLWORTHS_STORE,
} from "@/shared/data/woolworthsStores";
import {
  CBD_GREEN_AREAS,
  CBD_LABELS,
  CBD_LAND,
  CBD_MAP_BOUNDS,
  CBD_ROADS,
} from "@/shared/map/aucklandCbd";
import { Attribution } from "@/shared/ui/Attribution";

type Location = DashboardResponse["communities"][number]["location"];

function point([latitude, longitude]: readonly [number, number]) {
  const x =
    ((longitude - CBD_MAP_BOUNDS.west) /
      (CBD_MAP_BOUNDS.east - CBD_MAP_BOUNDS.west)) *
    1000;
  const y =
    ((CBD_MAP_BOUNDS.north - latitude) /
      (CBD_MAP_BOUNDS.north - CBD_MAP_BOUNDS.south)) *
    375;
  return `${x.toFixed(1)},${y.toFixed(1)}`;
}

function position(location: Location) {
  return point([location.latitude, location.longitude]);
}

function isVisible(location: Location) {
  return (
    location.latitude <= CBD_MAP_BOUNDS.north &&
    location.latitude >= CBD_MAP_BOUNDS.south &&
    location.longitude >= CBD_MAP_BOUNDS.west &&
    location.longitude <= CBD_MAP_BOUNDS.east
  );
}

export function NetworkMap({ data }: { readonly data: DashboardResponse }) {
  const selectedStoreId =
    data.urgent_donation?.store_id ??
    data.donations[0]?.store_id ??
    DEFAULT_CBD_WOOLWORTHS_STORE.id;
  const visibleCommunities = data.communities.filter((community) =>
    isVisible(community.location),
  );
  const visibleDrivers = data.drivers.filter((driver) =>
    isVisible(driver.start_location),
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
          <h2>Auckland CBD Woolworths network</h2>
        </div>
        <span className="live-label">
          <span className="network-pulse" /> {data.communities.length} community
          partners online
        </span>
      </div>
      <div className="map-canvas">
        <svg
          viewBox="0 0 1000 375"
          role="img"
          aria-label="Auckland CBD street map showing three Woolworths stores and nearby rescue partners"
        >
          <rect width="1000" height="375" className="map-water" />
          <polygon
            points={CBD_LAND.map(point).join(" ")}
            className="cbd-land"
          />
          {CBD_GREEN_AREAS.map((area) => (
            <polygon
              key={area.name}
              points={area.shape.map(point).join(" ")}
              className="cbd-park"
            >
              <title>{area.name}</title>
            </polygon>
          ))}
          {CBD_ROADS.map((road) => (
            <g key={road.name}>
              <polyline
                points={road.path.map(point).join(" ")}
                className={`cbd-road-casing ${road.tier}`}
              />
              <polyline
                points={road.path.map(point).join(" ")}
                className={`cbd-road ${road.tier}`}
              />
            </g>
          ))}
          {CBD_LABELS.map((label) => {
            const [x, y] = point(label.at).split(",");
            return (
              <text
                key={label.name}
                x={x}
                y={y}
                className={`cbd-label ${label.kind}`}
                aria-hidden="true"
              >
                {label.name}
              </text>
            );
          })}
          {CBD_WOOLWORTHS_STORES.map((store) => {
            const [x, y] = position(store.location).split(",");
            const isSelected = store.id === selectedStoreId;
            return (
              <g
                key={store.id}
                transform={`translate(${x} ${y})`}
                role="img"
                aria-label={`${store.name}${isSelected ? " · selected donation store" : ""}`}
              >
                <circle
                  r={isSelected ? 22 : 17}
                  className={`store-halo${isSelected ? " selected" : ""}`}
                />
                <rect
                  x={isSelected ? -9 : -7}
                  y={isSelected ? -9 : -7}
                  width={isSelected ? 18 : 14}
                  height={isSelected ? 18 : 14}
                  rx="4"
                  className={`store-marker${isSelected ? " selected" : ""}`}
                />
                <text
                  x="14"
                  y={isSelected ? 4 : -10}
                  className="store-map-label"
                >
                  {store.mapLabel}
                </text>
                <title>
                  {store.name} · {store.address}
                </title>
              </g>
            );
          })}
          {visibleCommunities.map((community) => {
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
          {visibleDrivers.map((driver) => {
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
            <i className="legend-square selected" /> Selected store
          </span>
          <span>
            <i className="legend-square" /> CBD store
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
          <MapPin size={15} /> Auckland CBD store coordination
        </span>
        <strong>Simulated network · no live GPS</strong>
      </div>
    </section>
  );
}
