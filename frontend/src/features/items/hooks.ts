"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { checkRow, fetchItems, type ItemList } from "./api";

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
