"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import {
  createInquiry,
  fetchInquiries,
  type InquiryCreated,
  type InquiryList,
} from "./api";

export function useInquiries(status?: string) {
  return useQuery<InquiryList>({
    queryKey: ["inquiries", status ?? "all"],
    queryFn: () => fetchInquiries(status),
  });
}

export function useCreateInquiry(onCreated: (created: InquiryCreated) => void) {
  return useMutation({
    mutationFn: ({ files, mailBody }: { files: File[]; mailBody: string }) =>
      createInquiry(files, mailBody),
    onSuccess: onCreated,
  });
}
