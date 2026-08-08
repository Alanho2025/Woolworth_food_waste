import type { DeliveryDetailResponse } from "@/shared/api/client";
import {
  ARTERIALS,
  AUCKLAND_BOUNDS,
  ISTHMUS,
  NORTH_SHORE,
} from "@/shared/map/auckland";
import { Attribution } from "@/shared/ui/Attribution";

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

function locationPoint(location: {
  readonly latitude: number;
  readonly longitude: number;
}) {
  return point([location.latitude, location.longitude]);
}

export function RouteMap({
  detail,
}: {
  readonly detail: DeliveryDetailResponse;
}) {
  const route = detail.order.route;
  return (
    <section className="route-map panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">Auckland route</span>
          <h2>
            {route.origin.name} → {route.destination.name}
          </h2>
        </div>
        <span className="simulated-badge">Simulated route</span>
      </div>
      <div className="map-canvas route-canvas">
        <svg
          viewBox="0 0 1000 680"
          role="img"
          aria-label="Simulated Auckland delivery route"
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
          <polyline
            points={route.polyline.map(point).join(" ")}
            className="active-route"
          />
          <circle
            cx={locationPoint(route.origin).split(",")[0]}
            cy={locationPoint(route.origin).split(",")[1]}
            r="11"
            className="route-origin"
          />
          <circle
            cx={locationPoint(route.destination).split(",")[0]}
            cy={locationPoint(route.destination).split(",")[1]}
            r="11"
            className="route-destination"
          />
        </svg>
        <div className="driver-progress">
          <span style={{ width: "62%" }} />
          <i style={{ left: "62%" }} />
        </div>
        <Attribution />
      </div>
      <div className="map-stat-row">
        <span>
          {route.distance_km.toFixed(1)} km · {route.duration_minutes} min
        </span>
        <strong>Progress animation is illustrative</strong>
      </div>
    </section>
  );
}
