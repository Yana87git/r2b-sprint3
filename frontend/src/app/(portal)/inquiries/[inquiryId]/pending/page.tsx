import { NeedsConfirmationScreen } from "@/features/items";
import { AppShell } from "@/shared/ui/AppShell";

export default async function PendingPage({
  params,
}: {
  params: Promise<{ inquiryId: string }>;
}) {
  const { inquiryId } = await params;
  return (
    <AppShell>
      <NeedsConfirmationScreen inquiryId={inquiryId} />
    </AppShell>
  );
}
