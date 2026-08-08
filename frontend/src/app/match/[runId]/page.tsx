import { AgentMatchScreen } from "@/features/agent-match/AgentMatchScreen";

export default async function MatchRunPage(props: PageProps<"/match/[runId]">) {
  const { runId } = await props.params;
  return <AgentMatchScreen runId={runId} />;
}
