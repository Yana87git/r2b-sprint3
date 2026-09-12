import { ConfirmedScreen } from "@/features/items";
import { AppShell } from "@/shared/ui/AppShell";

export default async function DonePage({
  params,
}: {
  params: Promise<{ inquiryId: string }>;
}) {
  const { inquiryId } = await params;
  return (
    <AppShell>
      <ConfirmedScreen inquiryId={inquiryId} />
    </AppShell>
  );
}
