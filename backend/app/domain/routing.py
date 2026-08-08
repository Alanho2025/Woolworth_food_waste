"""Pure deterministic route calculation for the P1 domain.

The MVP does not claim commercial routing. A caller may provide a hand-traced
polyline; otherwise the route is the deterministic two-point fallback. Every
result is explicitly marked simulated. Infrastructure may supply seeded road
geometry through the same ``RouteSimulator`` port without changing policy code.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from math import asin, cos, radians, sin, sqrt

from backend.app.contracts.core import Location, RouteLeg
from backend.app.domain.clock import Clock

EARTH_RADIUS_KM = 6371.0088
SIMULATED_SPEED_KMH = 30.0
MINIMUM_DURATION_MINUTES = 5

Coordinate = tuple[float, float]
PolylineKey = tuple[str, str]


def haversine_km(start: Coordinate, end: Coordinate) -> float:
    """Return the great-circle distance between two latitude/longitude points."""
    start_lat, start_lon = radians(start[0]), radians(start[1])
    end_lat, end_lon = radians(end[0]), radians(end[1])
    delta_lat = end_lat - start_lat
    delta_lon = end_lon - start_lon
    haversine = sin(delta_lat / 2) ** 2 + cos(start_lat) * cos(end_lat) * sin(delta_lon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(haversine))


def polyline_length_km(points: Sequence[Coordinate]) -> float:
    """Return the summed distance of all segments in a polyline."""
    if len(points) < 2:
        raise ValueError("a route polyline requires at least two coordinates")
    return sum(haversine_km(points[index], points[index + 1]) for index in range(len(points) - 1))


def calculate_route(
    origin: Location,
    destination: Location,
    departure: datetime,
    *,
    polyline: Sequence[Coordinate] | None = None,
) -> RouteLeg:
    """Calculate one deterministic simulated leg from explicit facts."""
    if departure.tzinfo is None:
        raise ValueError("route departure must be timezone-aware")
    points = (
        tuple(polyline)
        if polyline is not None
        else (
            (origin.latitude, origin.longitude),
            (destination.latitude, destination.longitude),
        )
    )
    distance_km = round(polyline_length_km(points), 2)
    duration_minutes = max(
        MINIMUM_DURATION_MINUTES,
        round(distance_km / SIMULATED_SPEED_KMH * 60),
    )
    return RouteLeg(
        origin=origin,
        destination=destination,
        polyline=list(points),
        distance_km=distance_km,
        duration_minutes=duration_minutes,
        eta=departure + timedelta(minutes=duration_minutes),
        simulated=True,
    )


simulate_route = calculate_route


class DeterministicRouteSimulator:
    """``RouteSimulator`` implementation backed by injected clock and geometry."""

    def __init__(
        self,
        clock: Clock,
        polylines: Mapping[PolylineKey, Sequence[Coordinate]] | None = None,
    ) -> None:
        self._clock = clock
        self._polylines = polylines if polylines is not None else {}

    def route(self, origin: Location, destination: Location) -> RouteLeg:
        return calculate_route(
            origin,
            destination,
            self._clock.now(),
            polyline=self._polylines.get((origin.name, destination.name)),
        )
