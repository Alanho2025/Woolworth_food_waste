import { DriverRouteScreen } from "@/features/driver-route/DriverRouteScreen";
export default async function DeliveryPage(props: {
  params: Promise<{ deliveryId: string }>;
}) {
  const { deliveryId } = await props.params;
  return <DriverRouteScreen deliveryId={deliveryId} />;
}
