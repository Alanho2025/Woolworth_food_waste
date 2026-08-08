"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import {
  ArrowRight,
  Braces,
  Check,
  Clock3,
  Leaf,
  PackageOpen,
  Sparkles,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useMemo } from "react";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import type {
  CreateDonationRequest,
  StartMatchResponse,
} from "@/shared/api/client";
import { useCreateDonationMutation } from "@/shared/api/queries";

const awareDateTime = z
  .string()
  .regex(
    /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$/,
    "Use an ISO date-time with timezone, for example +12:00",
  );

const donationFormSchema = z
  .object({
    store_id: z.string().min(1, "Choose a store"),
    food_name: z.string().min(2, "Enter a clear food name"),
    category: z.enum([
      "vegetables",
      "fruit",
      "bakery",
      "dairy",
      "meat",
      "ambient_grocery",
    ]),
    quantity: z
      .number()
      .int("Use whole kilograms")
      .min(1, "Quantity must be at least 1 kg"),
    unit: z.literal("kg"),
    storage_type: z.enum(["ambient", "chilled", "frozen"]),
    pickup_start: awareDateTime,
    pickup_end: awareDateTime,
    delivery_deadline: awareDateTime,
    handling_notes: z
      .string()
      .max(240, "Keep handling notes under 240 characters"),
  })
  .superRefine((value, context) => {
    const start = Date.parse(value.pickup_start);
    const end = Date.parse(value.pickup_end);
    const deadline = Date.parse(value.delivery_deadline);
    if (Number.isFinite(start) && Number.isFinite(end) && end <= start)
      context.addIssue({
        code: "custom",
        path: ["pickup_end"],
        message: "Pickup end must follow its start",
      });
    if (Number.isFinite(end) && Number.isFinite(deadline) && deadline < end)
      context.addIssue({
        code: "custom",
        path: ["delivery_deadline"],
        message: "Deadline must follow the pickup window",
      });
  });

type DonationFormValues = z.infer<typeof donationFormSchema>;

const blankValues: DonationFormValues = {
  store_id: "WW-MT-EDEN",
  food_name: "",
  category: "vegetables",
  quantity: 60,
  unit: "kg",
  storage_type: "ambient",
  pickup_start: "2026-08-08T16:00:00+12:00",
  pickup_end: "2026-08-08T17:00:00+12:00",
  delivery_deadline: "2026-08-08T19:00:00+12:00",
  handling_notes: "",
};

const demoValues: DonationFormValues = {
  ...blankValues,
  food_name: "Fresh vegetables",
  handling_notes: "Keep shaded and deliver in stackable produce crates.",
};

function toRequest(values: DonationFormValues): CreateDonationRequest {
  return {
    donation_id: "DON-PREVIEW-001",
    store_id: values.store_id,
    pickup_window: { start: values.pickup_start, end: values.pickup_end },
    items: [
      {
        item_name: values.food_name,
        category: values.category,
        quantity: values.quantity,
        unit: values.unit,
        storage_type: values.storage_type,
        delivery_deadline: values.delivery_deadline,
      },
    ],
    handling_notes: values.handling_notes,
  };
}

interface DonateFormProps {
  readonly onStarted?: (run: StartMatchResponse) => void;
}

export function DonateForm({ onStarted }: DonateFormProps) {
  const router = useRouter();
  const mutation = useCreateDonationMutation();
  const form = useForm<DonationFormValues>({
    resolver: zodResolver(donationFormSchema),
    defaultValues: blankValues,
    mode: "onChange",
  });
  const values = useWatch({ control: form.control });
  const preview = useMemo(
    () => toRequest({ ...blankValues, ...values }),
    [values],
  );

  async function submit(validValues: DonationFormValues) {
    const { run } = await mutation.mutateAsync(toRequest(validValues));
    if (onStarted) onStarted(run);
    else router.push(`/match/${run.run_id}`);
  }

  return (
    <main className="page-shell donate-page">
      <header className="page-header donate-header">
        <div>
          <span className="eyebrow">New rescue operation</span>
          <h1>Create a food donation</h1>
          <p>
            Structure the surplus once. FoodFlow checks live need, capacity and
            delivery feasibility next.
          </p>
        </div>
        <button
          className="button demo-button"
          type="button"
          onClick={() => form.reset(demoValues)}
          data-testid="prefill-demo"
        >
          <Sparkles size={17} /> Prefill 60 kg demo
        </button>
      </header>

      <ol className="stepper" aria-label="Donation journey">
        <li className="current">
          <span>1</span>
          <div>
            <strong>Donation</strong>
            <small>Describe surplus</small>
          </div>
        </li>
        <li>
          <span>2</span>
          <div>
            <strong>Agent match</strong>
            <small>Assess options</small>
          </div>
        </li>
        <li>
          <span>3</span>
          <div>
            <strong>Delivery</strong>
            <small>Track handoff</small>
          </div>
        </li>
      </ol>

      <div className="donate-grid">
        <form
          className="donation-form panel"
          onSubmit={form.handleSubmit(submit)}
          noValidate
          data-testid="donation-form"
        >
          <section className="form-section">
            <div className="form-section-title">
              <span>
                <PackageOpen size={19} />
              </span>
              <div>
                <h2>Surplus details</h2>
                <p>What is ready for redistribution?</p>
              </div>
            </div>
            <div className="field-grid two">
              <Field
                label="Woolworths store"
                error={form.formState.errors.store_id?.message}
              >
                <select {...form.register("store_id")}>
                  <option value="WW-MT-EDEN">Woolworths Mount Eden</option>
                </select>
              </Field>
              <Field
                label="Food name"
                error={form.formState.errors.food_name?.message}
              >
                <input
                  placeholder="e.g. Fresh vegetables"
                  {...form.register("food_name")}
                />
              </Field>
              <Field
                label="Category"
                error={form.formState.errors.category?.message}
              >
                <select {...form.register("category")}>
                  <option value="vegetables">Vegetables</option>
                  <option value="fruit">Fruit</option>
                  <option value="bakery">Bakery</option>
                  <option value="dairy">Dairy</option>
                  <option value="meat">Meat</option>
                  <option value="ambient_grocery">Ambient grocery</option>
                </select>
              </Field>
              <div className="quantity-row">
                <Field
                  label="Quantity"
                  error={form.formState.errors.quantity?.message}
                >
                  <input
                    type="number"
                    min="1"
                    step="1"
                    {...form.register("quantity", { valueAsNumber: true })}
                  />
                </Field>
                <Field label="Unit">
                  <input value="kg" readOnly {...form.register("unit")} />
                </Field>
              </div>
              <Field
                label="Storage requirement"
                error={form.formState.errors.storage_type?.message}
              >
                <select {...form.register("storage_type")}>
                  <option value="ambient">Ambient</option>
                  <option value="chilled">Chilled</option>
                  <option value="frozen">Frozen</option>
                </select>
              </Field>
            </div>
          </section>

          <section className="form-section">
            <div className="form-section-title">
              <span>
                <Clock3 size={19} />
              </span>
              <div>
                <h2>Collection window</h2>
                <p>Timezone-aware Auckland operating times</p>
              </div>
            </div>
            <div className="field-grid two">
              <Field
                label="Pickup starts"
                hint="ISO 8601 · NZ offset"
                error={form.formState.errors.pickup_start?.message}
              >
                <input {...form.register("pickup_start")} />
              </Field>
              <Field
                label="Pickup ends"
                hint="ISO 8601 · NZ offset"
                error={form.formState.errors.pickup_end?.message}
              >
                <input {...form.register("pickup_end")} />
              </Field>
              <Field
                label="Delivery deadline"
                error={form.formState.errors.delivery_deadline?.message}
              >
                <input {...form.register("delivery_deadline")} />
              </Field>
            </div>
          </section>

          <section className="form-section compact">
            <div className="form-section-title">
              <span>
                <Leaf size={19} />
              </span>
              <div>
                <h2>Handling notes</h2>
                <p>Short operational guidance for the driver</p>
              </div>
            </div>
            <Field
              label="Notes"
              hint={`${values.handling_notes?.length ?? 0}/240 characters`}
              error={form.formState.errors.handling_notes?.message}
            >
              <textarea
                rows={3}
                placeholder="Crate, temperature or access instructions"
                {...form.register("handling_notes")}
              />
            </Field>
          </section>

          {mutation.isError && (
            <div className="inline-error" role="alert">
              <strong>Donation not submitted.</strong>
              <span>
                {mutation.error.message} No success has been simulated.
              </span>
            </div>
          )}
          <div className="form-submit">
            <div>
              <Check size={16} />
              <span>
                {form.formState.isValid
                  ? "Request is ready for the Agent"
                  : "Complete the highlighted fields"}
              </span>
            </div>
            <button
              className="button primary submit-button"
              type="submit"
              disabled={mutation.isPending}
            >
              {mutation.isPending ? "Starting Agent…" : "Submit to AI Agent"}
              <ArrowRight size={18} />
            </button>
          </div>
        </form>

        <aside
          className="json-panel panel"
          aria-label="Live JSON request preview"
        >
          <div className="json-heading">
            <div>
              <span className="json-icon">
                <Braces size={19} />
              </span>
              <div>
                <span className="eyebrow">Live contract preview</span>
                <h2>Donation request</h2>
              </div>
            </div>
            <span className="valid-dot">P2 contract</span>
          </div>
          <pre data-testid="json-preview">
            <code>{JSON.stringify(preview, null, 2)}</code>
          </pre>
          <div className="json-foot">
            <span>
              <i /> Updates as you type
            </span>
            <strong>POST /donations → /match</strong>
          </div>
        </aside>
      </div>
    </main>
  );
}

function Field({
  label,
  hint,
  error,
  children,
}: {
  readonly label: string;
  readonly hint?: string;
  readonly error?: string;
  readonly children: React.ReactNode;
}) {
  return (
    <label className={`field ${error ? "has-error" : ""}`}>
      <span>
        {label}
        {hint && <small>{hint}</small>}
      </span>
      {children}
      {error && <em>{error}</em>}
    </label>
  );
}
