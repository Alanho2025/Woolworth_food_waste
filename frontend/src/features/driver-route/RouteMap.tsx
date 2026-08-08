import type { DeliveryDetailResponse } from "@/shared/api/client";
import type { PolylinePoint } from "@/shared/contracts/core";
import { ARTERIALS, ISTHMUS, NORTH_SHORE } from "@/shared/map/auckland";
import {
  CBD_GREEN_AREAS,
  CBD_LABELS,
  CBD_LAND,
  CBD_ROADS,
} from "@/shared/map/aucklandCbd";
import { Attribution } from "@/shared/ui/Attribution";

const MAP_WIDTH = 1000;
const MAP_HEIGHT = 680;
const DRIVER_PROGRESS = 0.62;

interface RouteBounds {
  readonly north: number;
  readonly south: number;
  readonly west: number;
  readonly east: number;
}

function routeBounds(points: readonly PolylinePoint[]): RouteBounds {
  const latitudes = points.map(([latitude]) => latitude);
  const longitudes = points.map(([, longitude]) => longitude);
  const maxLatitude = Math.max(...latitudes);
  const minLatitude = Math.min(...latitudes);
  const maxLongitude = Math.max(...longitudes);
  const minLongitude = Math.min(...longitudes);
  const latitudeSpan = Math.max(maxLatitude - minLatitude, 0.006);
  const longitudeSpan = Math.max(maxLongitude - minLongitude, 0.01);
  const centreLatitude = (maxLatitude + minLatitude) / 2;
  const centreLongitude = (maxLongitude + minLongitude) / 2;
  let framedLatitudeSpan = latitudeSpan * 1.34;
  let framedLongitudeSpan = longitudeSpan * 1.34;

  // One degree of longitude is shorter than one degree of latitude in Auckland.
  // Account for that before fitting the route to the SVG aspect ratio.
  const longitudeScale = Math.cos((centreLatitude * Math.PI) / 180);
  const targetGeoAspect = MAP_WIDTH / MAP_HEIGHT / longitudeScale;
  if (framedLongitudeSpan / framedLatitudeSpan < targetGeoAspect) {
    framedLongitudeSpan = framedLatitudeSpan * targetGeoAspect;
  } else {
    framedLatitudeSpan = framedLongitudeSpan / targetGeoAspect;
  }

  return {
    north: centreLatitude + framedLatitudeSpan / 2,
    south: centreLatitude - framedLatitudeSpan / 2,
    west: centreLongitude - framedLongitudeSpan / 2,
    east: centreLongitude + framedLongitudeSpan / 2,
  };
}

function project([latitude, longitude]: PolylinePoint, bounds: RouteBounds) {
  return {
    x: ((longitude - bounds.west) / (bounds.east - bounds.west)) * MAP_WIDTH,
    y: ((bounds.north - latitude) / (bounds.north - bounds.south)) * MAP_HEIGHT,
  };
}

function point(coordinate: PolylinePoint, bounds: RouteBounds) {
  const { x, y } = project(coordinate, bounds);
  return `${x.toFixed(1)},${y.toFixed(1)}`;
}

function locationPoint(
  location: { readonly latitude: number; readonly longitude: number },
  bounds: RouteBounds,
) {
  return project([location.latitude, location.longitude], bounds);
}

function contains(bounds: RouteBounds, coordinate: PolylinePoint) {
  const [latitude, longitude] = coordinate;
  return (
    latitude <= bounds.north &&
    latitude >= bounds.south &&
    longitude >= bounds.west &&
    longitude <= bounds.east
  );
}

function positionAlongRoute(
  points: readonly PolylinePoint[],
  progress: number,
): PolylinePoint {
  if (points.length === 1) return points[0]!;
  const segmentLengths = points.slice(1).map(([latitude, longitude], index) => {
    const previous = points[index]!;
    const latitudeDelta = latitude - previous[0];
    const longitudeDelta =
      (longitude - previous[1]) *
      Math.cos((((latitude + previous[0]) / 2) * Math.PI) / 180);
    return Math.hypot(latitudeDelta, longitudeDelta);
  });
  const totalLength = segmentLengths.reduce((sum, length) => sum + length, 0);
  let remaining = totalLength * progress;

  for (let index = 0; index < segmentLengths.length; index += 1) {
    const segmentLength = segmentLengths[index]!;
    if (remaining <= segmentLength) {
      const start = points[index]!;
      const end = points[index + 1]!;
      const ratio = segmentLength === 0 ? 0 : remaining / segmentLength;
      return [
        start[0] + (end[0] - start[0]) * ratio,
        start[1] + (end[1] - start[1]) * ratio,
      ];
    }
    remaining -= segmentLength;
  }

  return points.at(-1)!;
}

export function RouteMap({
  detail,
}: {
  readonly detail: DeliveryDetailResponse;
}) {
  const route = detail.order.route;
  const routePoints: readonly PolylinePoint[] =
    route.polyline.length > 1
      ? route.polyline
      : [
          [route.origin.latitude, route.origin.longitude],
          [route.destination.latitude, route.destination.longitude],
        ];
  const bounds = routeBounds(routePoints);
  const origin = locationPoint(route.origin, bounds);
  const destination = locationPoint(route.destination, bounds);
  const driver = project(
    positionAlongRoute(routePoints, DRIVER_PROGRESS),
    bounds,
  );
  const roads = [
    ...ARTERIALS.map((road) => ({
      ...road,
      tier: road.motorway ? ("motorway" as const) : ("primary" as const),
    })),
    ...CBD_ROADS,
  ];

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
          viewBox={`0 0 ${MAP_WIDTH} ${MAP_HEIGHT}`}
          role="img"
          aria-label="Simulated Auckland delivery route"
          data-testid="delivery-route-map"
        >
          <rect width={MAP_WIDTH} height={MAP_HEIGHT} className="map-water" />
          <polygon
            points={NORTH_SHORE.map((coordinate) =>
              point(coordinate, bounds),
            ).join(" ")}
            className="map-land"
          />
          <polygon
            points={ISTHMUS.map((coordinate) => point(coordinate, bounds)).join(
              " ",
            )}
            className="map-land"
          />
          <polygon
            points={CBD_LAND.map((coordinate) =>
              point(coordinate, bounds),
            ).join(" ")}
            className="map-land route-cbd-land"
          />
          {CBD_GREEN_AREAS.map((area) => (
            <polygon
              key={area.name}
              points={area.shape
                .map((coordinate) => point(coordinate, bounds))
                .join(" ")}
              className="cbd-park"
            >
              <title>{area.name}</title>
            </polygon>
          ))}
          {roads.map((road, index) => (
            <g key={`${road.name}-${index}`}>
              <polyline
                points={road.path
                  .map((coordinate) => point(coordinate, bounds))
                  .join(" ")}
                className={`cbd-road-casing ${road.tier}`}
              />
              <polyline
                points={road.path
                  .map((coordinate) => point(coordinate, bounds))
                  .join(" ")}
                className={`cbd-road ${road.tier}`}
              />
            </g>
          ))}
          {CBD_LABELS.filter((label) => contains(bounds, label.at)).map(
            (label) => {
              const labelPoint = project(label.at, bounds);
              return (
                <text
                  key={label.name}
                  x={labelPoint.x}
                  y={labelPoint.y}
                  className={`cbd-label ${label.kind}`}
                  aria-hidden="true"
                >
                  {label.name}
                </text>
              );
            },
          )}
          <polyline
            points={routePoints
              .map((coordinate) => point(coordinate, bounds))
              .join(" ")}
            className="active-route"
          />
          <circle
            cx={origin.x}
            cy={origin.y}
            r="13"
            className="route-origin"
            data-testid="route-origin-marker"
          >
            <title>Pickup · {route.origin.name}</title>
          </circle>
          <text
            x={origin.x + (origin.x > MAP_WIDTH * 0.72 ? -20 : 20)}
            y={origin.y - 20}
            textAnchor={origin.x > MAP_WIDTH * 0.72 ? "end" : "start"}
            className="route-place-label"
            aria-hidden="true"
          >
            Pickup
          </text>
          <circle
            cx={destination.x}
            cy={destination.y}
            r="13"
            className="route-destination"
            data-testid="route-destination-marker"
          >
            <title>Recipient · {route.destination.name}</title>
          </circle>
          <text
            x={destination.x + (destination.x > MAP_WIDTH * 0.72 ? -20 : 20)}
            y={destination.y - 20}
            textAnchor={destination.x > MAP_WIDTH * 0.72 ? "end" : "start"}
            className="route-place-label"
            aria-hidden="true"
          >
            Recipient
          </text>
          <g
            transform={`translate(${driver.x} ${driver.y})`}
            role="img"
            aria-label="Simulated driver position · 62%"
          >
            <circle r="23" className="route-driver-halo" />
            <path
              d="M -11 8 L 0 -13 L 11 8 L 0 4 Z"
              className="route-driver-marker"
            />
          </g>
        </svg>
        <Attribution />
      </div>
      <div className="map-stat-row">
        <span>
          {route.distance_km.toFixed(1)} km · {route.duration_minutes} min
        </span>
        <strong>Driver position is simulated</strong>
      </div>
    </section>
  );
}
