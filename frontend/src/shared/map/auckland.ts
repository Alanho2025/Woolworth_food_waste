/**
 * A stylised basemap of the Auckland isthmus, held as local coordinates.
 *
 * WHY NOT TILES (docs/phase_review_findings.md R-7, docs/assumption_audit.md D-3):
 * the OSM Foundation Tile Usage Policy explicitly prohibits offline use and
 * prefetch/bulk download of `tile.openstreetmap.org`, so bundling a raster
 * subset is a licence violation, and fetching tiles live makes the two most
 * important pitch screens dependent on a venue network. Everything below is
 * hand-traced geometry rendered as inline SVG from these arrays: it makes zero
 * network requests, works with Wi-Fi off, and renders identically in jsdom so
 * the map is testable.
 *
 * The shapes are a schematic derived from OpenStreetMap geography, not a survey
 * — the coastline is simplified to a few dozen points. `Attribution` is
 * rendered wherever this basemap appears, which the ODbL requires
 * (docs/phase_review_findings.md R-20).
 *
 * Coordinates are `[latitude, longitude]` throughout, matching `RouteLeg.polyline`
 * in `backend/app/contracts/core.py`.
 */

import type { PolylinePoint } from "@/shared/contracts/core";

/** The drawn window over the Auckland isthmus. */
export const AUCKLAND_BOUNDS = {
  north: -36.755,
  south: -36.985,
  west: 174.615,
  east: 174.925,
} as const;

/** North Shore landmass, across the Waitematā. */
export const NORTH_SHORE: PolylinePoint[] = [
  [-36.755, 174.615],
  [-36.755, 174.925],
  [-36.788, 174.925],
  [-36.797, 174.892],
  [-36.804, 174.862],
  [-36.798, 174.836],
  [-36.812, 174.818],
  [-36.819, 174.796],
  [-36.826, 174.777],
  [-36.823, 174.759],
  [-36.816, 174.744],
  [-36.806, 174.727],
  [-36.799, 174.706],
  [-36.792, 174.681],
  [-36.786, 174.652],
  [-36.779, 174.615],
];

/**
 * The isthmus itself — Waitematā Harbour along the north, Manukau Harbour along
 * the south, with the Tāmaki Estuary notched into the east.
 */
export const ISTHMUS: PolylinePoint[] = [
  // North coast, west to east.
  [-36.872, 174.615],
  [-36.861, 174.641],
  [-36.855, 174.663],
  [-36.849, 174.686],
  [-36.846, 174.709],
  [-36.844, 174.731],
  [-36.841, 174.752],
  [-36.842, 174.768],
  [-36.848, 174.781],
  [-36.859, 174.788],
  [-36.851, 174.797],
  [-36.845, 174.809],
  [-36.844, 174.823],
  // Tāmaki Estuary notch, running inland to the south-east.
  [-36.851, 174.838],
  [-36.869, 174.848],
  [-36.888, 174.856],
  [-36.906, 174.869],
  [-36.897, 174.878],
  [-36.879, 174.869],
  [-36.861, 174.86],
  [-36.849, 174.866],
  [-36.846, 174.886],
  [-36.852, 174.907],
  [-36.866, 174.925],
  // East edge down to the Manukau.
  [-36.925, 174.925],
  [-36.949, 174.902],
  [-36.958, 174.874],
  [-36.951, 174.848],
  [-36.94, 174.826],
  [-36.93, 174.808],
  // Māngere Inlet notch.
  [-36.919, 174.796],
  [-36.93, 174.784],
  [-36.941, 174.772],
  [-36.938, 174.752],
  [-36.943, 174.73],
  [-36.952, 174.707],
  [-36.958, 174.682],
  [-36.962, 174.652],
  [-36.964, 174.615],
];

/** Waiheke-side and Hauraki Gulf water is simply the background. */
export interface Arterial {
  readonly name: string;
  readonly path: PolylinePoint[];
  /** Motorways draw slightly heavier than surface arterials. */
  readonly motorway: boolean;
}

export const ARTERIALS: readonly Arterial[] = [
  {
    name: "State Highway 1 (Southern Motorway)",
    motorway: true,
    path: [
      [-36.845, 174.764],
      [-36.858, 174.771],
      [-36.87, 174.776],
      [-36.888, 174.786],
      [-36.905, 174.797],
      [-36.921, 174.809],
      [-36.94, 174.822],
    ],
  },
  {
    name: "State Highway 1 (Harbour Bridge)",
    motorway: true,
    path: [
      [-36.845, 174.764],
      [-36.842, 174.749],
      [-36.833, 174.744],
      [-36.822, 174.742],
      [-36.808, 174.744],
    ],
  },
  {
    name: "State Highway 16 (North-Western Motorway)",
    motorway: true,
    path: [
      [-36.846, 174.762],
      [-36.855, 174.742],
      [-36.864, 174.722],
      [-36.872, 174.699],
      [-36.874, 174.673],
      [-36.871, 174.645],
    ],
  },
  {
    name: "State Highway 20 (South-Western Motorway)",
    motorway: true,
    path: [
      [-36.897, 174.741],
      [-36.91, 174.755],
      [-36.921, 174.774],
      [-36.929, 174.795],
      [-36.938, 174.815],
    ],
  },
  {
    name: "Mount Eden Road",
    motorway: false,
    path: [
      [-36.855, 174.766],
      [-36.868, 174.765],
      [-36.879, 174.764],
      [-36.893, 174.761],
      [-36.906, 174.757],
    ],
  },
  {
    name: "Dominion Road",
    motorway: false,
    path: [
      [-36.858, 174.759],
      [-36.872, 174.752],
      [-36.888, 174.747],
      [-36.904, 174.743],
      [-36.918, 174.741],
    ],
  },
  {
    name: "Manukau Road",
    motorway: false,
    path: [
      [-36.869, 174.777],
      [-36.883, 174.777],
      [-36.897, 174.78],
      [-36.911, 174.783],
      [-36.923, 174.784],
    ],
  },
  {
    name: "New North Road",
    motorway: false,
    path: [
      [-36.86, 174.757],
      [-36.87, 174.74],
      [-36.878, 174.72],
      [-36.884, 174.698],
    ],
  },
  {
    name: "Great South Road",
    motorway: false,
    path: [
      [-36.871, 174.78],
      [-36.886, 174.793],
      [-36.902, 174.806],
      [-36.919, 174.818],
    ],
  },
  {
    name: "Tāmaki Drive",
    motorway: false,
    path: [
      [-36.847, 174.78],
      [-36.845, 174.798],
      [-36.847, 174.816],
      [-36.851, 174.833],
    ],
  },
  {
    name: "Remuera Road",
    motorway: false,
    path: [
      [-36.87, 174.777],
      [-36.874, 174.797],
      [-36.878, 174.818],
      [-36.881, 174.838],
    ],
  },
  {
    name: "Onehunga Mall",
    motorway: false,
    path: [
      [-36.912, 174.786],
      [-36.921, 174.786],
      [-36.929, 174.788],
    ],
  },
];

/** Suburb labels — enough context for an Auckland judge to orient. */
export interface PlaceLabel {
  readonly name: string;
  readonly at: PolylinePoint;
}

export const PLACE_LABELS: readonly PlaceLabel[] = [
  { name: "Waitematā Harbour", at: [-36.828, 174.7] },
  { name: "Manukau Harbour", at: [-36.945, 174.688] },
  { name: "Hauraki Gulf", at: [-36.8, 174.905] },
  { name: "North Shore", at: [-36.775, 174.76] },
  { name: "City Centre", at: [-36.849, 174.766] },
  { name: "Mount Eden", at: [-36.879, 174.756] },
  { name: "Mount Roskill", at: [-36.912, 174.732] },
  { name: "Onehunga", at: [-36.927, 174.795] },
  { name: "Glen Innes", at: [-36.872, 174.86] },
  { name: "Ponsonby", at: [-36.853, 174.74] },
];
