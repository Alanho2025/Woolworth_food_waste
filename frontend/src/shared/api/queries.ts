"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  confirmDelivery,
  createDonationAndStartMatch,
  getAgentRun,
  getDashboard,
  getDelivery,
  type ConfirmDeliveryRequest,
  type CreateDonationRequest,
} from "./client";

export const dashboardQueryKey = ["dashboard"] as const;

export function useDashboardQuery() {
  return useQuery({
    queryKey: dashboardQueryKey,
    queryFn: getDashboard,
    refetchInterval: 15_000,
    retry: 1,
  });
}

export function useCreateDonationMutation() {
  return useMutation({
    mutationFn: (request: CreateDonationRequest) =>
      createDonationAndStartMatch(request),
  });
}

export function useAgentRunQuery(runId: string) {
  return useQuery({
    queryKey: ["agent-run", runId],
    queryFn: () => getAgentRun(runId),
    refetchInterval: (query) =>
      query.state.data?.status === "succeeded" ||
      query.state.data?.status === "failed"
        ? false
        : 500,
  });
}

export function useDeliveryQuery(deliveryId: string, enabled = true) {
  return useQuery({
    queryKey: ["delivery", deliveryId],
    queryFn: () => getDelivery(deliveryId),
    enabled,
  });
}

export function useConfirmDeliveryMutation(deliveryId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (request: ConfirmDeliveryRequest) =>
      confirmDelivery(deliveryId, request),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: dashboardQueryKey });
      await queryClient.invalidateQueries({
        queryKey: ["delivery", deliveryId],
      });
    },
  });
}
