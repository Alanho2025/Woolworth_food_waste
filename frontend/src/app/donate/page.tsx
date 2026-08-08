import type { Metadata } from "next";

import { DonateForm } from "@/features/donate/DonateForm";

export const metadata: Metadata = { title: "Create donation" };

export default function DonatePage() {
  return <DonateForm />;
}
