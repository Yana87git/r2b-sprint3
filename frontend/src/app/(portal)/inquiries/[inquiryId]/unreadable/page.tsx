import { UnreadableScreen } from "@/features/runs";
import { AppShell } from "@/shared/ui/AppShell";

export default async function UnreadablePage({
  params,
}: {
  params: Promise<{ inquiryId: string }>;
}) {
  const { inquiryId } = await params;
  return (
    <AppShell>
      <UnreadableScreen inquiryId={inquiryId} />
    </AppShell>
  );
}
