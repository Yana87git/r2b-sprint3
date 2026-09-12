import { RunStatusScreen } from "@/features/runs";
import { AppShell } from "@/shared/ui/AppShell";

export default async function RunPage({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  const { runId } = await params;
  return (
    <AppShell>
      <RunStatusScreen runId={runId} />
    </AppShell>
  );
}
