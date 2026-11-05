# Database

PostgreSQL 16, schema managed exclusively by Alembic (`backend/migrations`). Never use automatic table creation in production.

```bash
alembic upgrade head      # apply
alembic check             # verify models and migrations match
```

## Integrity protections

- `audit_logs`, `order_events`, `payment_events`: **append-only** — a trigger rejects UPDATE and DELETE.
- `payments`: rows cannot be deleted; once `SUCCEEDED`, amount, currency, order and provider transaction id are immutable and the status may only move to `REFUNDED`.
- `invoices`: cannot be deleted.
- Money columns are `BIGINT` minor units with CHECK constraints (non-negative totals, deposit ≤ total, positive payment amounts).
- Unique constraints prevent duplicate provider transactions (`provider, provider_transaction_id`), duplicate webhook events, duplicate notifications (`dedupe_key`) and duplicate payment idempotency keys.
- All timestamps are `timestamptz` in UTC. Ownership is explicit (`customer_id`, `owner_id`, `order_id`) and enforced in every query.
- Soft deletion: users (`deleted_at`, `deactivated_at`), services (`archived_at`), attachments (`deleted_at`).

## Tables

### ai_execution_steps

`execution_id`, `seq`, `stage`, `status`, `summary`, `detail`, `created_at`, `id`

Foreign keys: execution_id→ai_executions

### ai_executions

`order_id`, `attempt`, `status`, `capability`, `classification`, `plan`, `validation_report`, `revision_instructions`, `failure_reason`, `fallback_reason`, `triggered_by_id`, `celery_task_id`, `input_tokens`, `output_tokens`, `cost_usd`, `started_at`, `finished_at`, `cancel_requested`, `id`, `created_at`, `updated_at`

Foreign keys: order_id→orders, triggered_by_id→users

### ai_model_configurations

`provider_id`, `purpose`, `model_identifier`, `input_cost_per_mtok`, `output_cost_per_mtok`, `max_tokens`, `temperature`, `is_active`, `id`, `created_at`, `updated_at`

Foreign keys: provider_id→ai_providers

### ai_providers

`key`, `display_name`, `base_url`, `api_key_encrypted`, `api_key_last4`, `is_enabled`, `last_health_ok`, `last_health_at`, `last_error`, `id`, `created_at`, `updated_at`

### ai_reviews

`execution_id`, `reviewer_id`, `decision`, `comment`, `created_at`, `id`

Foreign keys: execution_id→ai_executions, reviewer_id→users

### ai_usage_records

`execution_id`, `order_id`, `user_id`, `purpose`, `provider_key`, `model_identifier`, `input_tokens`, `output_tokens`, `cost_usd`, `success`, `error`, `latency_ms`, `created_at`, `id`

Foreign keys: execution_id→ai_executions, order_id→orders, user_id→users

### attachments

`owner_id`, `order_id`, `message_id`, `purpose`, `storage_key`, `original_name`, `mime_type`, `size_bytes`, `sha256`, `scan_status`, `is_public`, `created_at`, `deleted_at`, `id`

Foreign keys: message_id→messages, order_id→orders, owner_id→users

### audit_logs

`actor_id`, `actor_type`, `action`, `entity_type`, `entity_id`, `ip_address`, `user_agent`, `success`, `data`, `created_at`, `id`

Foreign keys: actor_id→users

### contact_requests

`name`, `email`, `subject`, `message`, `ip_address`, `handled_at`, `created_at`, `id`

### conversations

`order_id`, `customer_id`, `last_message_at`, `id`, `created_at`, `updated_at`

Foreign keys: customer_id→users, order_id→orders

### deliverables

`order_id`, `attachment_id`, `title`, `note`, `source`, `ai_execution_id`, `approved_by_id`, `approved_at`, `released_at`, `revision_round`, `id`, `created_at`, `updated_at`

Foreign keys: ai_execution_id→ai_executions, approved_by_id→users, attachment_id→attachments, order_id→orders

### email_verifications

`user_id`, `token_hash`, `expires_at`, `used_at`, `created_at`, `id`

Foreign keys: user_id→users

### faq_items

`question`, `answer`, `sort_order`, `is_published`, `id`, `created_at`, `updated_at`

### invoices

`invoice_number`, `order_id`, `payment_id`, `kind`, `amount_minor`, `currency`, `status`, `issued_at`, `paid_at`, `id`, `created_at`, `updated_at`

Foreign keys: order_id→orders, payment_id→payments

### messages

`conversation_id`, `sender_id`, `sender_is_staff`, `body`, `created_at`, `read_by_customer_at`, `read_by_staff_at`, `id`

Foreign keys: conversation_id→conversations, sender_id→users

### notifications

`user_id`, `channel`, `event_type`, `dedupe_key`, `title`, `body`, `data`, `status`, `attempts`, `last_error`, `sent_at`, `read_at`, `created_at`, `id`

Foreign keys: user_id→users

### order_counters

`year`, `value`

### order_events

`order_id`, `event_type`, `from_status`, `to_status`, `actor_type`, `actor_id`, `customer_visible`, `message`, `data`, `created_at`, `id`

Foreign keys: actor_id→users, order_id→orders

### order_items

`order_id`, `service_id`, `description`, `quantity`, `unit_price_minor`, `total_minor`, `addons`, `id`

Foreign keys: order_id→orders, service_id→services

### orders

`order_number`, `customer_id`, `service_id`, `category_id`, `is_custom`, `title`, `description`, `requirements`, `preferred_language`, `contact_info`, `budget_minor`, `status`, `currency`, `total_minor`, `deposit_minor`, `paid_minor`, `refunded_minor`, `payment_status`, `accepted_quotation_id`, `execution_method`, `ai_status`, `admin_notes`, `customer_notes`, `revision_count`, `deadline`, `submitted_at`, `completed_at`, `delivered_at`, `closed_at`, `cancelled_at`, `ai_classification`, `review_rating`, `review_text`, `review_public`, `reviewed_at`, `version`, `id`, `created_at`, `updated_at`

Foreign keys: accepted_quotation_id→quotations, category_id→service_categories, customer_id→users, service_id→services

### password_resets

`user_id`, `token_hash`, `expires_at`, `used_at`, `created_at`, `ip_address`, `id`

Foreign keys: user_id→users

### payment_events

`payment_id`, `event_type`, `from_status`, `to_status`, `provider_event_id`, `data`, `created_at`, `id`

Foreign keys: payment_id→payments

### payments

`reference`, `order_id`, `customer_id`, `kind`, `provider`, `status`, `amount_minor`, `currency`, `idempotency_key`, `provider_transaction_id`, `provider_state`, `confirmed_at`, `cancelled_at`, `failure_reason`, `recorded_by_id`, `id`, `created_at`, `updated_at`

Foreign keys: customer_id→users, order_id→orders, recorded_by_id→users

### permissions

`code`, `description`, `id`

### processed_webhook_events

`provider`, `event_id`, `created_at`, `id`

### promo_code_usages

`promo_code_id`, `user_id`, `order_id`, `discount_minor`, `created_at`, `id`

Foreign keys: order_id→orders, promo_code_id→promo_codes, user_id→users

### promo_codes

`code`, `percent_off`, `amount_off_minor`, `currency`, `max_uses`, `max_uses_per_user`, `min_order_minor`, `valid_from`, `valid_until`, `is_active`, `service_ids`, `id`, `created_at`, `updated_at`

### quotations

`order_id`, `status`, `currency`, `line_items`, `subtotal_minor`, `discount_minor`, `extra_charges_minor`, `total_minor`, `deposit_minor`, `promo_code_id`, `estimated_delivery_days`, `note`, `created_by_id`, `source`, `valid_until`, `responded_at`, `rejection_reason`, `id`, `created_at`, `updated_at`

Foreign keys: created_by_id→users, order_id→orders, promo_code_id→promo_codes

### refunds

`order_id`, `payment_id`, `amount_minor`, `currency`, `status`, `reason`, `requested_by_id`, `processed_by_id`, `provider_refund_id`, `processed_at`, `id`, `created_at`, `updated_at`

Foreign keys: order_id→orders, payment_id→payments, processed_by_id→users, requested_by_id→users

### role_permissions

`role_id`, `permission_id`

Foreign keys: permission_id→permissions, role_id→roles

### roles

`name`, `description`, `id`

### service_categories

`slug`, `name`, `description`, `icon`, `sort_order`, `is_active`, `id`, `created_at`, `updated_at`

### service_pricing

`service_id`, `pricing_type`, `currency`, `base_price_minor`, `unit_label`, `min_quantity`, `max_quantity`, `tiers`, `addons`, `deposit_type`, `deposit_value`, `id`, `created_at`, `updated_at`

Foreign keys: service_id→services

### services

`slug`, `category_id`, `name`, `short_description`, `description`, `icon`, `image_attachment_id`, `estimated_delivery`, `estimated_hours`, `required_fields`, `allows_attachments`, `examples`, `is_active`, `is_featured`, `ai_eligible`, `ai_capability`, `revision_limit`, `sort_order`, `archived_at`, `id`, `created_at`, `updated_at`

Foreign keys: category_id→service_categories, image_attachment_id→attachments

### sessions

`user_id`, `token_hash`, `csrf_token_hash`, `created_at`, `last_seen_at`, `expires_at`, `revoked_at`, `mfa_verified`, `ip_address`, `user_agent`, `id`

Foreign keys: user_id→users

### static_pages

`slug`, `title`, `body`, `is_published`, `updated_by_id`, `id`, `created_at`, `updated_at`

Foreign keys: updated_by_id→users

### system_settings

`key`, `value`, `is_secret`, `encrypted_value`, `updated_by_id`, `id`, `created_at`, `updated_at`

Foreign keys: updated_by_id→users

### telegram_accounts

`user_id`, `telegram_user_id`, `chat_id`, `username`, `notifications_enabled`, `linked_at`, `id`, `created_at`, `updated_at`

Foreign keys: user_id→users

### telegram_link_codes

`user_id`, `code_hash`, `expires_at`, `used_at`, `attempts`, `id`

Foreign keys: user_id→users

### user_profiles

`user_id`, `full_name`, `phone`, `company`, `language`, `timezone`, `notification_prefs`, `id`, `created_at`, `updated_at`

Foreign keys: user_id→users

### user_roles

`user_id`, `role_id`, `granted_by_id`, `created_at`

Foreign keys: granted_by_id→users, role_id→roles, user_id→users

### users

`email`, `password_hash`, `is_active`, `email_verified_at`, `mfa_secret_encrypted`, `mfa_enabled`, `mfa_recovery_hashes`, `last_login_at`, `deactivated_at`, `deleted_at`, `password_changed_at`, `id`, `created_at`, `updated_at`
