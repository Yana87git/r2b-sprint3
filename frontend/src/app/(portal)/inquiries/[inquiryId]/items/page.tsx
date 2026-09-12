import { ItemListScreen } from "@/features/items";
import { AppShell } from "@/shared/ui/AppShell";

export default async function ItemsPage({
  params,
}: {
  params: Promise<{ inquiryId: string }>;
}) {
  const { inquiryId } = await params;
  return (
    <AppShell>
      <ItemListScreen inquiryId={inquiryId} />
    </AppShell>
  );
}
