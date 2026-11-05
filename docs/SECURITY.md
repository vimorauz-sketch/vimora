# Security

Designed against OWASP ASVS L2 principles and the OWASP Top 10. Each control below is implemented in code; the "Test" column names the automated test that exercises it (`backend/tests`, `frontend/tests`).

| Area | Control | Where | Test |
|---|---|---|---|
| Passwords | Argon2id (m=64 MiB, t=3, p=2), strength rules, rehash on login, timing-equalised for unknown users | `security/crypto.py` | `test_password_hash_is_argon2id` |
| Sessions | 256-bit random token, HttpOnly/Secure/SameSite=Lax cookie, only SHA-256 stored, absolute + idle expiry, rotation on login/MFA/password change, revoke on reset/role change/disable | `security/sessions.py` | `test_session_cookie_flags_and_db_stores_only_hash`, `test_change_password_rotates_and_revokes` |
| CSRF | Per-session token double-submitted in `X-CSRF-Token`, Origin check | `api/deps.py` | `test_csrf_required_for_state_changes` |
| MFA | TOTP + single-use recovery codes; **mandatory for staff in production**; admin sessions shorter (12 h) | `api/v1/auth.py`, `account.py` | `test_mfa_enroll_and_login`, `test_admin_mfa_enforced_when_required` |
| Brute force | Per-IP limits; progressive back-off per (account, IP) so attackers can't lock real users out; per-account ceiling; fail-closed when Redis is down | `security/rate_limit.py` | `test_progressive_login_throttle_is_per_ip` |
| Enumeration | Identical responses for register/forgot-password whether or not the account exists; generic login error | `auth.py` | `test_register_does_not_enumerate`, `test_bad_credentials_generic_and_audited` |
| Tokens | Email-verify and reset tokens hashed, one-time, expiring (48 h / 30 min); reset revokes all sessions | `auth.py` | `test_password_reset_flow`, `test_expired_reset_token_rejected` |
| Access control | Server-side RBAC (SUPER_ADMIN / ADMIN / SUPPORT / CUSTOMER) with least privilege; support has no finance, pricing, settings, secrets or staff management | `security/permissions.py`, `api/deps.py` | `test_support_role_least_privilege`, `test_customers_cannot_access_admin`, `test_privilege_escalation_blocked` |
| IDOR | Ownership is part of every customer query; foreign records return 404 (indistinguishable from missing) | `services/orders.py` | `test_customer_cannot_read_other_customers_order`, `test_account_cross_order_views_are_scoped` |
| Mass assignment | All request schemas `extra="forbid"`; sender, status, price, owner always come from the server | `schemas/inputs.py` | `test_customer_cannot_set_status_or_prices`, `test_message_ownership_not_spoofable` |
| Payment integrity | Signature/auth verification, amount + currency + reference checks, idempotent confirmation, replay protection, DB-immutable confirmed payments, frontend return URL never trusted | `payments/` | `test_click_*`, `test_payme_flow`, `test_stripe_webhook`, `test_confirmed_payment_is_immutable` |
| Business rules | State machine with actor restrictions; payment-only transitions; release only after full payment (configurable) | `services/order_state.py` | `test_state_machine_rejects_invalid_and_payment_only_transitions`, `test_end_to_end_delivery_requires_final_payment` |
| Uploads | Size limit, extension allowlist, content sniffing, HTML/SVG/executables rejected, Office macros and zip bombs rejected, random storage keys, quotas, optional ClamAV | `services/files.py` | `test_upload_validation`, `test_macro_office_file_rejected`, `test_oversize_upload_rejected` |
| Downloads | Private storage; 5-minute HMAC-signed links re-checking authorization; `Content-Disposition: attachment`, `nosniff`, `CSP: sandbox` | `services/files.py`, `api/v1/files.py` | `test_signed_download_link`, `test_expired_download_link` |
| XSS | React escaping; owner Markdown rendered without raw HTML; AI output previewed as plain text; strict CSP on the API and a restrictive CSP on the site | `next.config.mjs`, `features/policy-page.tsx` | — |
| SSRF | No user-supplied URLs are fetched by the server; outbound calls only to fixed provider hosts; AI base URLs must be `https://` and are admin-only | `ai/providers`, `payments/providers.py` | — |
| Open redirect | Post-login `next` only accepts same-site relative paths | `features/auth/forms.tsx` | `post-login redirect` (vitest) |
| AI safety | No tools/shell/network for the model; allowlisted capabilities and file types; unsafe file names rejected; untrusted content wrapped as data; AI never approves itself; budgets; isolated sandbox on a separate host | `ai/` | `test_ai_pipeline_requires_human_approval`, `test_ai_unsafe_output_rejected`, `test_ai_budget_limit` |
| Secrets | Env only; `.env` git-ignored; AI keys and MFA secrets Fernet-encrypted in DB and never returned (last 4 chars only); log redaction for tokens/keys/passwords; production refuses to start with weak config | `core/config.py`, `core/logging.py` | `test_admin_settings_never_return_secrets` |
| Audit | Append-only audit log (DB trigger) for logins, admin actions, payments, status changes, AI actions, config and permission changes, file link issuance | `services/audit.py` | `test_audit_and_event_tables_are_append_only` |
| Headers | HSTS, nosniff, frame-deny, referrer policy, permissions policy, no-store on API | `middleware/security.py`, Caddyfile | `test_security_headers` |
| Errors | Uniform envelope, no stack traces, request ids | `core/errors.py` | `test_errors_do_not_leak_internals` |
| Telegram | Secret webhook path + secret header; admin commands require the configured Telegram user id; read-only; rate limited and audited | `telegram/bot.py` | `test_telegram_*` |
| Infrastructure | Non-root, read-only containers with all capabilities dropped; Postgres/Redis on an internal network with no published ports; Redis password | compose files | `docker compose config` |

## Known limitations / residual risks

- Malware scanning requires a ClamAV daemon (`CLAMAV_HOST`); without it files are marked `NOT_SCANNED` (still never executed or served inline).
- The AI sandbox requires a separate Docker host; without it generated code is syntax-checked (AST) but never executed.
- A PostgreSQL superuser can bypass the append-only triggers. Run the application with a non-superuser role in production (the compose `vimora` role owns the DB; consider a separate restricted role for the app if your threat model needs it).
- Login throttling and rate limits depend on Redis.
- `--forwarded-allow-ips "*"` is safe only because the API container is reachable solely from the internal Docker networks behind Caddy; do not publish port 8000.
- A third-party penetration test has not been performed.

## Reporting

Report vulnerabilities privately to the platform owner. Rotate `SECRET_KEY` (invalidates download links), `SETTINGS_ENCRYPTION_KEY` (requires re-entering AI keys and re-enrolling MFA) and provider secrets if compromise is suspected.
