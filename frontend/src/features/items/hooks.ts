"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  checkRow,
  confirmInquiry,
  fetchItems,
  type ConfirmResult,
  type ItemList,
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
