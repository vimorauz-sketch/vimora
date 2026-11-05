# API reference

Base path: `/api/v1`. JSON in and out. Errors always use the envelope

```json
{"error": {"code": "STRING_CODE", "message": "Human readable", "details": {}}}
```

Authentication: session cookie `vimora_session` (HttpOnly). State-changing requests from a signed-in browser must send `X-CSRF-Token` equal to the `vimora_csrf` cookie. Staff endpoints (`/admin/*`) additionally require the listed permission and, in production, a session verified with MFA. Rate limits return `429` with `Retry-After`.

Interactive OpenAPI docs are available at `/api/docs` in development only.

## account

| Method | Path | Summary |
|---|---|---|
| POST | `/api/v1/account/change-password` | Change Password |
| GET | `/api/v1/account/conversations` | My Conversations |
| POST | `/api/v1/account/deactivate` | Deactivate |
| GET | `/api/v1/account/deliverables` | My Deliverables |
| POST | `/api/v1/account/mfa/disable` | Mfa Disable |
| POST | `/api/v1/account/mfa/enable` | Mfa Enable |
| POST | `/api/v1/account/mfa/setup` | Mfa Setup |
| PUT | `/api/v1/account/notification-preferences` | Update Prefs |
| GET | `/api/v1/account/notifications` | List Notifications |
| POST | `/api/v1/account/notifications/read-all` | Read All |
| POST | `/api/v1/account/notifications/{nid}/read` | Read One |
| GET | `/api/v1/account/payments` | My Payments |
| PATCH | `/api/v1/account/profile` | Update Profile |
| GET | `/api/v1/account/sessions` | List Sessions |
| POST | `/api/v1/account/sessions/revoke-others` | Revoke Others |
| DELETE | `/api/v1/account/sessions/{session_id}` | Revoke Session |
| GET | `/api/v1/account/telegram` | Telegram Status |
| DELETE | `/api/v1/account/telegram` | Telegram Unlink |
| POST | `/api/v1/account/telegram/link` | Telegram Link |
| POST | `/api/v1/account/telegram/toggle` | Telegram Toggle |

## admin:ai

| Method | Path | Summary |
|---|---|---|
| GET | `/api/v1/admin/ai/executions` | Executions |
| GET | `/api/v1/admin/ai/executions/{eid}` | Execution Detail |
| POST | `/api/v1/admin/ai/executions/{eid}/approve` | Approve |
| POST | `/api/v1/admin/ai/executions/{eid}/cancel` | Cancel |
| POST | `/api/v1/admin/ai/executions/{eid}/reject` | Reject |
| POST | `/api/v1/admin/ai/executions/{eid}/revise` | Revise |
| POST | `/api/v1/admin/ai/executions/{eid}/take-over` | Take Over |
| POST | `/api/v1/admin/ai/models` | Create Model |
| PUT | `/api/v1/admin/ai/models/{mid}` | Update Model |
| DELETE | `/api/v1/admin/ai/models/{mid}` | Delete Model |
| GET | `/api/v1/admin/ai/outputs/{attachment_id}/preview` | Preview Output |
| GET | `/api/v1/admin/ai/overview` | Overview |
| GET | `/api/v1/admin/ai/providers` | Providers |
| POST | `/api/v1/admin/ai/providers` | Upsert Provider |
| POST | `/api/v1/admin/ai/providers/{pid}/test` | Test Provider |

## admin:catalog

| Method | Path | Summary |
|---|---|---|
| GET | `/api/v1/admin/categories` | Categories |
| POST | `/api/v1/admin/categories` | Create Category |
| PUT | `/api/v1/admin/categories/{cid}` | Update Category |
| DELETE | `/api/v1/admin/categories/{cid}` | Delete Category |
| POST | `/api/v1/admin/images` | Upload Image |
| GET | `/api/v1/admin/promo-codes` | Promos |
| POST | `/api/v1/admin/promo-codes` | Create Promo |
| PUT | `/api/v1/admin/promo-codes/{pid}` | Update Promo |
| GET | `/api/v1/admin/services` | Services |
| POST | `/api/v1/admin/services` | Create Service |
| GET | `/api/v1/admin/services/{sid}` | Get Service |
| PUT | `/api/v1/admin/services/{sid}` | Update Service |
| DELETE | `/api/v1/admin/services/{sid}` | Delete Service |
| POST | `/api/v1/admin/services/{sid}/archive` | Archive Service |
| POST | `/api/v1/admin/services/{sid}/restore` | Restore Service |

## admin:customers

| Method | Path | Summary |
|---|---|---|
| GET | `/api/v1/admin/customers` | List Customers |
| GET | `/api/v1/admin/customers/{uid}` | Customer Detail |
| POST | `/api/v1/admin/customers/{uid}/disable` | Disable |
| POST | `/api/v1/admin/customers/{uid}/restore` | Restore |
| POST | `/api/v1/admin/customers/{uid}/roles` | Set Role |

## admin:finance

| Method | Path | Summary |
|---|---|---|
| GET | `/api/v1/admin/finance/export.csv` | Export |
| GET | `/api/v1/admin/finance/payments` | Payments |
| GET | `/api/v1/admin/finance/payments/{pid}/events` | Payment Events |
| GET | `/api/v1/admin/finance/reconciliation` | Reconciliation |
| GET | `/api/v1/admin/finance/refunds` | Refunds |
| GET | `/api/v1/admin/finance/summary` | Summary |

## admin:orders

| Method | Path | Summary |
|---|---|---|
| GET | `/api/v1/admin/orders` | List Orders |
| GET | `/api/v1/admin/orders/{order_id}` | Get Order |
| PATCH | `/api/v1/admin/orders/{order_id}` | Update Notes |
| POST | `/api/v1/admin/orders/{order_id}/ai/start` | Start Ai |
| POST | `/api/v1/admin/orders/{order_id}/complete` | Complete |
| POST | `/api/v1/admin/orders/{order_id}/deliverables/from-ai` | Promote Ai Output |
| DELETE | `/api/v1/admin/orders/{order_id}/deliverables/{deliverable_id}` | Delete Deliverable |
| POST | `/api/v1/admin/orders/{order_id}/files` | Upload Deliverable File |
| POST | `/api/v1/admin/orders/{order_id}/manual-payment` | Manual Payment |
| GET | `/api/v1/admin/orders/{order_id}/messages` | Messages |
| POST | `/api/v1/admin/orders/{order_id}/messages` | Post |
| POST | `/api/v1/admin/orders/{order_id}/quotations` | Create Quotation |
| POST | `/api/v1/admin/orders/{order_id}/refunds` | Request Refund |
| POST | `/api/v1/admin/orders/{order_id}/refunds/{refund_id}/complete` | Complete Refund |
| POST | `/api/v1/admin/orders/{order_id}/release` | Release |
| POST | `/api/v1/admin/orders/{order_id}/review-visibility` | Moderate Review |
| POST | `/api/v1/admin/orders/{order_id}/status` | Change Status |

## admin:system

| Method | Path | Summary |
|---|---|---|
| GET | `/api/v1/admin/analytics` | Analytics |
| GET | `/api/v1/admin/audit-logs` | Audit Logs |
| GET | `/api/v1/admin/contact-requests` | Contact Requests |
| POST | `/api/v1/admin/contact-requests/{cid}/handled` | Contact Handled |
| POST | `/api/v1/admin/email/test` | Email Test |
| GET | `/api/v1/admin/faq` | Faq |
| POST | `/api/v1/admin/faq` | Create Faq |
| PUT | `/api/v1/admin/faq/{fid}` | Update Faq |
| DELETE | `/api/v1/admin/faq/{fid}` | Delete Faq |
| GET | `/api/v1/admin/health` | Health Details |
| GET | `/api/v1/admin/overview` | Overview |
| GET | `/api/v1/admin/pages` | Pages |
| PUT | `/api/v1/admin/pages/{slug}` | Put Page |
| GET | `/api/v1/admin/reviews` | Reviews |
| GET | `/api/v1/admin/settings` | Get Settings |
| PATCH | `/api/v1/admin/settings` | Patch Settings |
| POST | `/api/v1/admin/telegram/setup-webhook` | Telegram Setup |
| POST | `/api/v1/admin/telegram/test` | Telegram Test |

## auth

| Method | Path | Summary |
|---|---|---|
| POST | `/api/v1/auth/forgot-password` | Forgot Password |
| POST | `/api/v1/auth/login` | Login |
| POST | `/api/v1/auth/logout` | Logout |
| GET | `/api/v1/auth/me` | Me |
| POST | `/api/v1/auth/mfa/verify` | Mfa Verify |
| POST | `/api/v1/auth/register` | Register |
| POST | `/api/v1/auth/resend-verification` | Resend Verification |
| POST | `/api/v1/auth/reset-password` | Reset Password |
| POST | `/api/v1/auth/verify-email` | Verify Email |

## files

| Method | Path | Summary |
|---|---|---|
| POST | `/api/v1/files` | Upload |
| GET | `/api/v1/files/download` | Download |
| GET | `/api/v1/files/{attachment_id}/link` | Download Link |

## health

| Method | Path | Summary |
|---|---|---|
| GET | `/api/v1/health/details` | Health Token |
| GET | `/api/v1/health/live` | Live |
| GET | `/api/v1/health/ready` | Ready |

## messages

| Method | Path | Summary |
|---|---|---|
| GET | `/api/v1/orders/{order_id}/messages` | Customer Messages |
| POST | `/api/v1/orders/{order_id}/messages` | Customer Post |

## orders

| Method | Path | Summary |
|---|---|---|
| POST | `/api/v1/orders` | Create Order |
| GET | `/api/v1/orders` | List Orders |
| GET | `/api/v1/orders/overview` | Overview |
| GET | `/api/v1/orders/{order_id}` | Get Order |
| POST | `/api/v1/orders/{order_id}/attachments` | Add Attachments |
| POST | `/api/v1/orders/{order_id}/cancel` | Cancel |
| POST | `/api/v1/orders/{order_id}/close` | Close |
| POST | `/api/v1/orders/{order_id}/payments` | Start Payment |
| GET | `/api/v1/orders/{order_id}/payments/{reference}` | Payment Status |
| POST | `/api/v1/orders/{order_id}/quotation/accept` | Accept Quotation |
| POST | `/api/v1/orders/{order_id}/quotation/reject` | Reject Quotation |
| POST | `/api/v1/orders/{order_id}/review` | Review |
| POST | `/api/v1/orders/{order_id}/revision` | Revision |

## public

| Method | Path | Summary |
|---|---|---|
| POST | `/api/v1/ai/assist` | Ai Assist |
| GET | `/api/v1/catalog/categories` | Categories |
| POST | `/api/v1/catalog/price` | Price Preview |
| GET | `/api/v1/catalog/services` | Services |
| GET | `/api/v1/catalog/services/{slug}` | Service Detail |
| POST | `/api/v1/contact` | Contact |
| GET | `/api/v1/faq` | Faq |
| GET | `/api/v1/pages/{slug}` | Static Page |
| GET | `/api/v1/public-files/{att_id}` | Public File |
| GET | `/api/v1/site` | Site Settings |
| GET | `/api/v1/stats` | Public Stats |
| GET | `/api/v1/testimonials` | Testimonials |

## webhooks

| Method | Path | Summary |
|---|---|---|
| POST | `/api/v1/webhooks/click/complete` | Click Complete |
| POST | `/api/v1/webhooks/click/prepare` | Click Prepare |
| POST | `/api/v1/webhooks/payme` | Payme Rpc |
| POST | `/api/v1/webhooks/stripe` | Stripe |
| POST | `/api/v1/webhooks/telegram/{path_secret}` | Telegram |

## WebSocket

| Path | Purpose |
|---|---|
| `/api/v1/ws/orders/{order_id}` | Live order messages. Authenticated by session cookie; origin checked; customers only for their own orders. Polling fallback is used by the frontend. |

## Provider webhooks

| Endpoint | Verification |
|---|---|
| `POST /webhooks/click/prepare`, `/complete` | MD5 `sign_string` per Click SHOP API, service id, amount, reference, idempotent complete |
| `POST /webhooks/payme` | HTTP Basic `Paycom:<key>`, JSON-RPC methods CheckPerformTransaction, CreateTransaction, PerformTransaction, CancelTransaction, CheckTransaction, GetStatement; account field `payment_ref` |
| `POST /webhooks/stripe` | `Stripe-Signature` HMAC-SHA256 with 5-minute tolerance; event id replay protection; amount+currency check |
| `POST /webhooks/telegram/{secret}` | secret path segment **and** `X-Telegram-Bot-Api-Secret-Token` header |
