export interface WoolworthsStore {
  readonly id: string;
  readonly name: string;
  readonly mapLabel: string;
  readonly address: string;
  readonly location: {
    readonly name: string;
    readonly latitude: number;
    readonly longitude: number;
  };
}

export const CBD_WOOLWORTHS_STORES: readonly WoolworthsStore[] = [
  {
    id: "WW-VICTORIA-ST-WEST",
    name: "Woolworths Victoria Street West",
    mapLabel: "Victoria Street West",
    address: "19–25 Victoria Street West, Auckland CBD",
    location: {
      name: "Woolworths Victoria Street West",
      latitude: -36.8486838,
      longitude: 174.7646849,
    },
  },
  {
    id: "WW-AUCKLAND-CITY",
    name: "Woolworths Auckland City",
    mapLabel: "Auckland City · Quay Street",
    address: "76 Quay Street, Auckland CBD",
    location: {
      name: "Woolworths Auckland City",
      latitude: -36.84525,
      longitude: 174.77281,
    },
  },
  {
    id: "WW-METRO-ALBERT-ST",
    name: "Woolworths Metro Albert Street",
    mapLabel: "Metro Albert Street",
    address: "29 Customs Street West, Auckland CBD",
    location: {
      name: "Woolworths Metro Albert Street",
      latitude: -36.8439,
      longitude: 174.76523,
    },
  },
] as const;

export const DEFAULT_CBD_WOOLWORTHS_STORE = CBD_WOOLWORTHS_STORES[0]!;

export function findWoolworthsStore(storeId: string | undefined) {
  return (
    CBD_WOOLWORTHS_STORES.find((store) => store.id === storeId) ??
    DEFAULT_CBD_WOOLWORTHS_STORE
  );
}
