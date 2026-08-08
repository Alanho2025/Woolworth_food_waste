import createClient from "openapi-fetch";

import type { components, paths } from "./generated/schema";

const baseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "http://127.0.0.1:8000";

export const apiClient = createClient<paths>({ baseUrl });

export type DashboardResponse =
  components["schemas"]["GlobalDashboardResponse"];
export type CreateDonationRequest =
  components["schemas"]["CreateDonationRequest"];
export type CreateDonationResponse =
  components["schemas"]["CreateDonationResponse"];
export type StartMatchResponse = components["schemas"]["StartMatchResponse"];
export type AgentRunResponse = components["schemas"]["AgentRunResponse"];
export type DeliveryDetailResponse =
  components["schemas"]["DeliveryDetailResponse"];
export type ConfirmDeliveryRequest =
  components["schemas"]["ConfirmDeliveryRequest"];
export type ConfirmDeliveryResponse =
  components["schemas"]["ConfirmDeliveryResponse"];

export class ApiRequestError extends Error {
  readonly code: string;

  constructor(message: string, code = "API_UNAVAILABLE") {
    super(message);
    this.name = "ApiRequestError";
    this.code = code;
  }
}

function errorMessage(error: unknown): string {
  if (typeof error === "object" && error !== null && "detail" in error) {
    const detail = Reflect.get(error, "detail");
    if (typeof detail === "string") return detail;
  }
  return "The live coordination service did not respond.";
}

export async function getDashboard(): Promise<DashboardResponse> {
  const { data, error } = await apiClient.GET("/dashboard");
  if (!data) throw new ApiRequestError(errorMessage(error));
  return data;
}

export async function createDonationAndStartMatch(
  body: CreateDonationRequest,
): Promise<{ created: CreateDonationResponse; run: StartMatchResponse }> {
  const createdResult = await apiClient.POST("/donations", { body });
  if (!createdResult.data) {
    throw new ApiRequestError(errorMessage(createdResult.error));
  }

  const runResult = await apiClient.POST("/donations/{donation_id}/match", {
    params: { path: { donation_id: createdResult.data.donation.donation_id } },
  });
  if (!runResult.data) {
    throw new ApiRequestError(errorMessage(runResult.error));
  }

  return { created: createdResult.data, run: runResult.data };
}

export async function getAgentRun(runId: string): Promise<AgentRunResponse> {
  const { data, error } = await apiClient.GET("/agent-runs/{run_id}", {
    params: { path: { run_id: runId } },
  });
  if (!data) throw new ApiRequestError(errorMessage(error));
  return data;
}

export async function getDelivery(
  deliveryId: string,
): Promise<DeliveryDetailResponse> {
  const { data, error } = await apiClient.GET("/deliveries/{delivery_id}", {
    params: { path: { delivery_id: deliveryId } },
  });
  if (!data) throw new ApiRequestError(errorMessage(error));
  return data;
}

export async function confirmDelivery(
  deliveryId: string,
  body: ConfirmDeliveryRequest,
): Promise<ConfirmDeliveryResponse> {
  const { data, error } = await apiClient.POST(
    "/deliveries/{delivery_id}/confirm",
    {
      params: { path: { delivery_id: deliveryId } },
      body,
    },
  );
  if (!data) throw new ApiRequestError(errorMessage(error));
  return data;
}
