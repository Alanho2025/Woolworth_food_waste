import { RematchScreen } from "@/features/rematch/RematchScreen";
export default async function RematchRunPage(props: {
  params: Promise<{ runId: string }>;
}) {
  const { runId } = await props.params;
  return <RematchScreen runId={runId} />;
}
