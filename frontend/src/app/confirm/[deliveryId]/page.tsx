import { DeliveryConfirmationScreen } from "@/features/delivery-confirmation/DeliveryConfirmationScreen";
export default async function ConfirmationPage(props: {
  params: Promise<{ deliveryId: string }>;
}) {
  const { deliveryId } = await props.params;
  return <DeliveryConfirmationScreen deliveryId={deliveryId} />;
}
