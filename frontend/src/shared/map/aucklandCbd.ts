import type { PolylinePoint } from "@/shared/contracts/core";

/** Auckland city-centre window used by the dashboard store map. */
export const CBD_MAP_BOUNDS = {
  north: -36.839,
  south: -36.876,
  west: 174.741,
  east: 174.791,
} as const;

/** Commercial Bay waterfront, including the Viaduct and central wharves. */
export const CBD_LAND: readonly PolylinePoint[] = [
  [-36.8422, 174.741],
  [-36.8405, 174.746],
  [-36.8406, 174.751],
  [-36.8425, 174.754],
  [-36.8424, 174.757],
  [-36.8402, 174.758],
  [-36.8401, 174.7602],
  [-36.8432, 174.7605],
  [-36.8433, 174.763],
  [-36.8403, 174.7635],
  [-36.8402, 174.7654],
  [-36.8436, 174.766],
  [-36.8437, 174.7682],
  [-36.8413, 174.7685],
  [-36.8413, 174.7703],
  [-36.8442, 174.7708],
  [-36.8446, 174.775],
  [-36.8451, 174.781],
  [-36.8454, 174.786],
  [-36.8456, 174.791],
  [-36.876, 174.791],
  [-36.876, 174.741],
];

export interface CbdArea {
  readonly name: string;
  readonly shape: readonly PolylinePoint[];
}

export const CBD_GREEN_AREAS: readonly CbdArea[] = [
  {
    name: "Victoria Park",
    shape: [
      [-36.8467, 174.7462],
      [-36.8474, 174.752],
      [-36.8514, 174.7512],
      [-36.8509, 174.7458],
    ],
  },
  {
    name: "Albert Park",
    shape: [
      [-36.8492, 174.7685],
      [-36.8498, 174.7732],
      [-36.8535, 174.7722],
      [-36.8531, 174.767],
    ],
  },
  {
    name: "Myers Park",
    shape: [
      [-36.8546, 174.7605],
      [-36.8552, 174.7632],
      [-36.8594, 174.7616],
      [-36.859, 174.7598],
    ],
  },
  {
    name: "Western Park",
    shape: [
      [-36.8567, 174.7445],
      [-36.8575, 174.7483],
      [-36.8624, 174.7475],
      [-36.8618, 174.7433],
    ],
  },
  {
    name: "Auckland Domain",
    shape: [
      [-36.8615, 174.779],
      [-36.8618, 174.7905],
      [-36.876, 174.7905],
      [-36.876, 174.7765],
      [-36.8705, 174.7755],
    ],
  },
];

export interface CbdRoad {
  readonly name: string;
  readonly tier: "motorway" | "primary" | "secondary";
  readonly path: readonly PolylinePoint[];
}

/** Street centre-lines follow the recognisable CBD grid and motorway edges. */
export const CBD_ROADS: readonly CbdRoad[] = [
  {
    name: "State Highway 1",
    tier: "motorway",
    path: [
      [-36.8452, 174.782],
      [-36.8505, 174.7805],
      [-36.856, 174.781],
      [-36.862, 174.7835],
      [-36.869, 174.786],
      [-36.876, 174.788],
    ],
  },
  {
    name: "State Highway 16",
    tier: "motorway",
    path: [
      [-36.8442, 174.758],
      [-36.8462, 174.753],
      [-36.849, 174.747],
      [-36.852, 174.741],
    ],
  },
  {
    name: "Quay Street",
    tier: "primary",
    path: [
      [-36.8447, 174.751],
      [-36.8447, 174.758],
      [-36.8449, 174.766],
      [-36.845, 174.775],
      [-36.8456, 174.786],
    ],
  },
  {
    name: "Customs Street",
    tier: "primary",
    path: [
      [-36.8463, 174.7535],
      [-36.8463, 174.761],
      [-36.8465, 174.769],
      [-36.8466, 174.778],
    ],
  },
  {
    name: "Fanshawe Street",
    tier: "primary",
    path: [
      [-36.8439, 174.741],
      [-36.845, 174.747],
      [-36.8464, 174.753],
      [-36.8476, 174.759],
    ],
  },
  {
    name: "Victoria Street",
    tier: "primary",
    path: [
      [-36.8488, 174.742],
      [-36.8485, 174.752],
      [-36.8487, 174.761],
      [-36.8488, 174.7705],
      [-36.8484, 174.778],
    ],
  },
  {
    name: "Wellesley Street",
    tier: "primary",
    path: [
      [-36.8523, 174.746],
      [-36.8521, 174.755],
      [-36.8524, 174.764],
      [-36.8525, 174.774],
    ],
  },
  {
    name: "Karangahape Road",
    tier: "primary",
    path: [
      [-36.8573, 174.742],
      [-36.8572, 174.751],
      [-36.8575, 174.761],
      [-36.8575, 174.7705],
    ],
  },
  {
    name: "Newton Road",
    tier: "primary",
    path: [
      [-36.8613, 174.741],
      [-36.8605, 174.749],
      [-36.8596, 174.7565],
      [-36.8585, 174.763],
    ],
  },
  {
    name: "Queen Street",
    tier: "primary",
    path: [
      [-36.8436, 174.7665],
      [-36.848, 174.7657],
      [-36.8525, 174.7648],
      [-36.8575, 174.7637],
      [-36.8645, 174.763],
    ],
  },
  {
    name: "Ponsonby Road",
    tier: "primary",
    path: [
      [-36.849, 174.746],
      [-36.855, 174.7462],
      [-36.861, 174.7464],
      [-36.869, 174.747],
    ],
  },
  {
    name: "Symonds Street",
    tier: "primary",
    path: [
      [-36.851, 174.7705],
      [-36.857, 174.769],
      [-36.8635, 174.7715],
      [-36.8705, 174.774],
      [-36.876, 174.777],
    ],
  },
  {
    name: "Grafton Bridge",
    tier: "primary",
    path: [
      [-36.8585, 174.764],
      [-36.8602, 174.769],
      [-36.861, 174.775],
      [-36.8615, 174.7805],
    ],
  },
  {
    name: "Albert Street",
    tier: "secondary",
    path: [
      [-36.8433, 174.7642],
      [-36.848, 174.763],
      [-36.8535, 174.7618],
    ],
  },
  {
    name: "Hobson Street",
    tier: "secondary",
    path: [
      [-36.8445, 174.7588],
      [-36.849, 174.7578],
      [-36.8545, 174.7562],
      [-36.8585, 174.7545],
    ],
  },
  {
    name: "Nelson Street",
    tier: "secondary",
    path: [
      [-36.8448, 174.7555],
      [-36.8495, 174.754],
      [-36.8545, 174.7525],
      [-36.858, 174.751],
    ],
  },
  {
    name: "Federal Street",
    tier: "secondary",
    path: [
      [-36.846, 174.761],
      [-36.8505, 174.7598],
      [-36.854, 174.7588],
    ],
  },
  {
    name: "Elliott Street",
    tier: "secondary",
    path: [
      [-36.847, 174.764],
      [-36.8505, 174.7632],
      [-36.853, 174.7626],
    ],
  },
  {
    name: "High Street",
    tier: "secondary",
    path: [
      [-36.8465, 174.768],
      [-36.849, 174.7675],
      [-36.851, 174.767],
    ],
  },
  {
    name: "Kitchener Street",
    tier: "secondary",
    path: [
      [-36.8473, 174.7705],
      [-36.8495, 174.7695],
      [-36.853, 174.768],
    ],
  },
  {
    name: "Wyndham Street",
    tier: "secondary",
    path: [
      [-36.847, 174.758],
      [-36.8475, 174.764],
      [-36.8474, 174.7705],
    ],
  },
  {
    name: "Cook Street",
    tier: "secondary",
    path: [
      [-36.8539, 174.747],
      [-36.8542, 174.754],
      [-36.8548, 174.761],
    ],
  },
  {
    name: "Mayoral Drive",
    tier: "secondary",
    path: [
      [-36.8535, 174.757],
      [-36.8552, 174.7605],
      [-36.8553, 174.766],
      [-36.8538, 174.7705],
    ],
  },
  {
    name: "Pitt Street",
    tier: "secondary",
    path: [
      [-36.8545, 174.755],
      [-36.858, 174.7565],
      [-36.862, 174.758],
    ],
  },
  {
    name: "Parnell Rise",
    tier: "secondary",
    path: [
      [-36.848, 174.776],
      [-36.852, 174.781],
      [-36.857, 174.786],
    ],
  },
  {
    name: "New North Road",
    tier: "secondary",
    path: [
      [-36.859, 174.758],
      [-36.865, 174.753],
      [-36.872, 174.747],
    ],
  },
  {
    name: "Khyber Pass Road",
    tier: "secondary",
    path: [
      [-36.866, 174.768],
      [-36.868, 174.776],
      [-36.869, 174.785],
    ],
  },
];

export interface CbdLabel {
  readonly name: string;
  readonly at: PolylinePoint;
  readonly kind: "water" | "district" | "landmark" | "road";
}

export const CBD_LABELS: readonly CbdLabel[] = [
  { name: "Waitematā Harbour", at: [-36.8416, 174.776], kind: "water" },
  { name: "Viaduct Harbour", at: [-36.8422, 174.749], kind: "water" },
  { name: "Commercial Bay", at: [-36.8458, 174.7678], kind: "district" },
  { name: "Ponsonby", at: [-36.8635, 174.744], kind: "district" },
  { name: "Grafton", at: [-36.864, 174.773], kind: "district" },
  { name: "Newmarket", at: [-36.8735, 174.779], kind: "district" },
  { name: "Sky Tower", at: [-36.8485, 174.761], kind: "landmark" },
  { name: "Aotea Square", at: [-36.8529, 174.762], kind: "landmark" },
  { name: "Albert Park", at: [-36.8515, 174.7705], kind: "landmark" },
  { name: "Auckland Domain", at: [-36.869, 174.783], kind: "landmark" },
  { name: "Queen Street", at: [-36.855, 174.7658], kind: "road" },
  { name: "Karangahape Road", at: [-36.8582, 174.7515], kind: "road" },
];
