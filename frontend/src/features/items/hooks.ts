"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  checkRow,
  confirmInquiry,
  fetchItems,
  type ConfirmResult,
  fetchValueSource,
  type ItemList,
  type ValueSourceDetail,
} from "./api";

export const itemsKey = (inquiryId: string) => ["items", inquiryId] as const;

export function useItems(inquiryId: string) {
  return useQuery<ItemList>({
    queryKey: itemsKey(inquiryId),
    queryFn: () => fetchItems(inquiryId),
  });
}

export function useCheckRow(inquiryId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (rowId: string) => checkRow(inquiryId, rowId),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: itemsKey(inquiryId) }),
  });
}

export function useConfirmInquiry(
  inquiryId: string,
  onConfirmed: (result: ConfirmResult) => void,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => confirmInquiry(inquiryId),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: itemsKey(inquiryId) });
      onConfirmed(result);
    },
  });
}

export function useValueSource(inquiryId: string, valueId: string) {
  const queryClient = useQueryClient();
  return useQuery<ValueSourceDetail>({
    queryKey: ["value-source", inquiryId, valueId],
    queryFn: async () => {
      const result = await fetchValueSource(inquiryId, valueId);
      // 抜き取りとして記録されたら、一覧の集計（読み取り元を開いた行）も更新する
      if (result.sampling.opened_now) {
        queryClient.invalidateQueries({ queryKey: itemsKey(inquiryId) });
      }
      return result;
    },
    staleTime: 0,
  });
}
