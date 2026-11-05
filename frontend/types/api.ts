export type Translatable = { uz: string; en: string; ru: string };

export type User = {
  id: number; email: string; full_name: string; phone: string | null; company: string | null; language: "uz" | "en" | "ru"; timezone: string;
  email_verified: boolean; mfa_enabled: boolean; roles: string[]; is_staff: boolean; created_at: string; notification_prefs: Record<string, Record<string, boolean>>;
};
export type Me = { user: User; mfa_pending: boolean; mfa_enrollment_required: boolean; permissions: string[] };

export type Category = { id: number; slug: string; name: string; description: string; icon: string; service_count?: number };
export type RequiredField = { key: string; label: string; type: "text" | "textarea" | "number" | "url" | "select"; required: boolean; options?: string[] };
export type Pricing = {
  pricing_type: "FIXED" | "PER_UNIT" | "QUANTITY_TIERED" | "STARTING_FROM" | "CUSTOM_QUOTE"; currency: string; base_price_minor: number; unit_label: string;
  min_quantity: number; max_quantity: number; tiers: { min_qty: number; unit_price_minor: number }[]; addons: { key: string; label: string; price_minor: number }[];
  deposit_type: "PERCENT" | "FIXED"; deposit_value: number;
};
export type Service = {
  id: number; slug: string; category: Category; name: string; short_description: string; description?: string; icon: string; image_url: string | null; image_credit?: string | null;
  estimated_delivery: string; estimated_hours: number | null; allows_attachments: boolean; is_active: boolean; is_featured: boolean; ai_eligible: boolean;
  revision_limit: number; pricing: Pricing | null; required_fields?: RequiredField[]; examples?: { title: string; text: string }[];
  mode: ServiceMode; requires_file: boolean; availability_status: "ACTIVE" | "PAUSED" | "FUTURE" | "ARCHIVED"; service_area: Area | null; available_in_area?: boolean;
};
export type ServiceMode = "ONLINE" | "REMOTE" | "LOCAL" | "FUTURE" | "DISABLED";
export type Area = { slug: string; kind: "REGION" | "DISTRICT" | "LOCALITY" | "OTHER"; name: string; region: string; district: string; locality: string; local_services_enabled: boolean; rules: string };
export type AdminArea = Omit<Area, "name" | "rules"> & { id: number; name: Translatable; rules: Translatable; is_active: boolean; provider_id: number | null; pickup_address?: string; sort_order: number; service_count: number };
export type HandoverProposal = { place: string; time: string; note: string; by: "customer" | "admin"; at: string };
export type Handover = {
  method: "PICKUP" | "MEETUP"; status: "WAITING" | "PROPOSED_BY_CUSTOMER" | "PROPOSED_BY_ADMIN" | "CONFIRMED" | "READY_FOR_PICKUP" | "HANDED_OVER";
  proposal: HandoverProposal | null; agreed: HandoverProposal | null; handed_over_at: string | null; pickup_address: string | null; history?: HandoverProposal[];
};
export type PriceResult = {
  currency: string; line_items: LineItem[]; subtotal_minor: number; discount_minor: number; extra_charges_minor: number; total_minor: number;
  deposit_minor: number; remaining_minor: number; requires_quote: boolean; is_starting_price: boolean; notes: string[];
};
export type LineItem = { description: string; quantity: number; unit_price_minor: number; total_minor: number };
export type Quotation = {
  id: number; status: string; currency: string; line_items: LineItem[]; subtotal_minor: number; discount_minor: number; extra_charges_minor: number; total_minor: number;
  deposit_minor: number; remaining_minor: number; estimated_delivery_days: number | null; note: string; source: string; valid_until: string | null; created_at: string; rejection_reason: string | null;
};
export type Attachment = { id: number; name: string; mime_type: string; size_bytes: number; purpose: string; scan_status: string; created_at: string };
export type Deliverable = { id: number; title: string; note: string; attachment: Attachment | null; released_at: string | null; revision_round: number; created_at: string; source?: string; approved_at?: string | null };
export type OrderEvent = { id: number; type: string; from_status: string | null; to_status: string | null; message: string; created_at: string; actor_type: string; customer_visible?: boolean; data?: Record<string, unknown> };
export type Payment = { id: number; reference: string; kind: string; provider: string; status: string; amount_minor: number; currency: string; created_at: string; confirmed_at: string | null; order_id: number; provider_transaction_id?: string | null; customer_email?: string; order_number?: string };
export type OrderSummary = {
  id: number; order_number: string; title: string; status: string; is_custom: boolean; service_name: string | null; currency: string; total_minor: number; deposit_minor: number;
  paid_minor: number; remaining_minor: number; payment_status: string; deadline: string | null; created_at: string; updated_at: string; customer_email?: string; execution_method?: string; ai_status?: string | null;
  is_local: boolean; handover_method: "PICKUP" | "MEETUP" | null; handover_status: Handover["status"] | null;
};
export type OrderDetail = OrderSummary & {
  description: string; requirements: Record<string, string>; preferred_language: string; customer_notes: string; revision_count: number; items: { description: string; quantity: number; unit_price_minor: number; total_minor: number }[];
  quotations: Quotation[]; events: OrderEvent[]; attachments: Attachment[]; deliverables: Deliverable[]; payments: Payment[];
  invoices: { invoice_number: string; kind: string; amount_minor: number; currency: string; status: string; paid_at: string | null }[];
  payment_due: { kind: string; amount_minor: number; currency: string; full_amount_minor: number } | null;
  can_cancel: boolean; can_request_revision: boolean; can_review: boolean; review_rating: number | null; review_text: string | null; ai_assisted: boolean; submitted_at: string | null; delivered_at: string | null;
  admin_notes?: string; ai_classification?: Record<string, unknown> | null; allowed_transitions?: string[]; customer?: { id: number; email: string; full_name: string; is_active: boolean };
  ai_outputs?: Attachment[]; ai_executions?: Execution[]; review_public?: boolean;
  handover: Handover | null; area: { slug: string; name: string } | null;
};
export type Message = { id: number; body: string; sender_is_staff: boolean; sender_name: string | null; created_at: string; read_by_customer_at: string | null; read_by_staff_at: string | null; attachments: Attachment[] };
export type Notification = { id: number; event_type: string; title: string; body: string; link: string | null; read_at: string | null; created_at: string };
export type Execution = { id: number; order_id: number; attempt: number; status: string; capability: string | null; input_tokens: number; output_tokens: number; cost_usd: string; failure_reason: string | null; fallback_reason: string | null; started_at: string | null; finished_at: string | null; created_at: string; order_number?: string };
export type Paged<T> = { items: T[]; total: number; page: number; page_size?: number };
export type SiteSettings = Record<string, unknown> & {
  "platform.name": string; "platform.maintenance_mode": boolean; "auth.registration_enabled": boolean; "uploads.max_mb": number; "ai.assistant_ready": boolean;
  "payments.providers": { key: string; available: boolean; currencies: string[] }[]; integrations: { telegram_linking: boolean };
};
