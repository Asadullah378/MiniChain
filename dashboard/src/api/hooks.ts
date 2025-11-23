import { useQuery, UseQueryOptions, UseQueryResult } from "@tanstack/react-query";
import { api } from "./client";
import {
  AccountsResponse,
  BlockDetail,
  BlocksResponse,
  NodeOverview,
  TransactionsResponse,
} from "./types";

export const useNodeOverview = (): UseQueryResult<NodeOverview[]> =>
  useQuery<NodeOverview[]>({
    queryKey: ["nodes"],
    queryFn: async () => {
      const { data } = await api.get<NodeOverview[]>("/nodes");
      return data;
    },
    refetchInterval: 5000,
  });

export const useBlocks = (
  params: { node_id?: string; limit?: number; offset?: number }
): UseQueryResult<BlocksResponse> =>
  useQuery<BlocksResponse>({
    queryKey: ["blocks", params],
    queryFn: async () => {
      const { data } = await api.get<BlocksResponse>("/blocks", { params });
      return data;
    },
  });

export const useBlockDetail = (
  height: number,
  params: { node_id?: string },
  options?: Pick<UseQueryOptions<BlockDetail>, "enabled">
): UseQueryResult<BlockDetail> =>
  useQuery<BlockDetail>({
    queryKey: ["block", height, params],
    queryFn: async () => {
      const { data } = await api.get<BlockDetail>(`/blocks/${height}`, { params });
      return data;
    },
    enabled: options?.enabled ?? true,
  });

export const useAccounts = (
  params: { node_id?: string; q?: string; limit?: number; offset?: number }
): UseQueryResult<AccountsResponse> =>
  useQuery<AccountsResponse>({
    queryKey: ["accounts", params],
    queryFn: async () => {
      const { data } = await api.get<AccountsResponse>("/accounts", { params });
      return data;
    },
  });

export const useTransactions = (
  params: { node_id?: string; limit?: number }
): UseQueryResult<TransactionsResponse> =>
  useQuery<TransactionsResponse>({
    queryKey: ["transactions", params],
    queryFn: async () => {
      const { data } = await api.get<TransactionsResponse>("/transactions", { params });
      return data;
    },
    refetchInterval: 7000,
  });
