import { request } from "@/shared/api/client";

export type InquiryListItem = {
  inquiry_id: string;
  title: string;
  status: string;
  unreadable_reason: string | null;
  submitted_at: string;
  submitted_by_name: string;
  formats: string[];
  total_rows: number;
  unchecked_rows: number;
  unreadable_input_count: number;
  pending_row_count: number | null;
  latest_run_id: string | null;
};

export type InquiryList = {
  counts: Record<string, number>;
  inquiries: InquiryListItem[];
};

export type AcceptedInput = {
  input_id: string;
  display_name: string;
  format: string;
  message: string;
};

export type InquiryCreated = {
  inquiry_id: string;
  inputs: AcceptedInput[];
  run_id: string;
};

/** ⑤ #5。投入日時の新しい順に全件返る（ページネーションなし）。 */
export function fetchInquiries(status?: string): Promise<InquiryList> {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  return request<InquiryList>(`/api/v1/inquiries${query}`);
}

/** ⑤ #4。202 が返り、サーバー側でエージェントが動き出す。 */
export function createInquiry(
  files: File[],
  mailBody: string,
): Promise<InquiryCreated> {
  const form = new FormData();
  for (const file of files) form.append("files", file);
  if (mailBody.trim()) form.append("mail_body", mailBody);
  return request<InquiryCreated>("/api/v1/inquiries", {
    method: "POST",
    body: form,
  });
}
