# Questions to the third party

Ask before designing. For each question: answer it from official documentation or SDK (cite version and URL), or leave it open. Open questions that change the Registry document or the code block the design. When the person needs to send them, give them in Spanish, grouped, ready to paste in an email or ticket.

## Payment provider (target)

| # | Question | Why it matters |
|---|---|---|
| P1 | Do you honor an idempotency key on every write operation? **Exact header name**? For how long? What do you return on a repeated key with a different body? | Decides `supports_idempotency_key`, `dedup_window_seconds`, and whether an uncertain delivery can be resent or goes to `outcome_unknown`. The Dispatcher only sends `Idempotency-Key` today |
| P1b | Does every operation return a distinct transaction id, or do some (refunds) notify with the payment's id? | Shared ids collide in the webhook mapping |
| P1c | How do you signal an error inside a 2xx (e.g. `code: ERROR`), and can the body be other than JSON? | Unmapped 2xx falls back to approved today |
| P2 | Which operations answer synchronously and which confirm later? What does the immediate answer contain (transaction id, state)? | `mode`, `confirms_async`, `tx_id_path`, provisional handling |
| P3 | Exact list of states and details per operation, which are final, and which can still change | `status_mapping`, `provider_states` (with detail lists) |
| P4 | Webhooks: which events, retry policy, ordering, duplicates, payload format (JSON/form), where the transaction id is | `webhook_status`, `webhook.tx_id_path`, duplicate handling |
| P5 | Webhook signature: algorithm, header format, what is signed, timestamp unit and tolerance, secret per provider or per merchant account, rotation | `webhook.signature` (`timestamp_unit`, `mode`) |
| P6 | Is there a query endpoint for a transaction's current state? Rate limits on it? | `reconciliation`; without it, the webhook is the only truth |
| P7 | Confirmation latency: p50/p99 of the final state, and the maximum before you consider it expired | `confirmation_window_seconds`, `result_ttl_s`, commercial commitment |
| P8 | Authentication: OAuth per merchant (authorization code, PKCE, refresh rotation), client credentials, API key per merchant, mTLS? Token lifetimes | `auth.strategy`, `federation`, onboarding path |
| P9 | Sandbox: separate host or same host with another key? Test data (cards, accounts, documents) | One target per environment, certification plan |
| P10 | A cheap read-only endpoint to validate a credential (200 vs 401) | `credential_validation` |
| P11 | Currencies and decimals per currency, minimum and maximum amounts | Package rules, amount cases |
| P12 | Refunds and voids: total/partial, how many partials, time windows, settlement cut-offs, what a "not completed" refund looks like | Package refund policy, operations |
| P13 | Expiry of a pending payment: who sets it, default, maximum | Package, processor decision |
| P14 | HTTP error semantics: which 4xx are final rejections, which 5xx are safe to retry, 429 headers | Retry and DLQ classification |
| P15 | Rate limits (global and per endpoint) | `rate_limit_rpm` |
| P16 | Redirect flow: return/cancel URLs, does "returning" imply payment? | Processor re-query |
| P17 | Required buyer data (PII) and whether it can be omitted | Payload minimization |
| P18 | Certification or approval process on your side before production | Timeline, compliance cases |
| P19 | IP allowlists or mTLS required to call you or to receive your webhooks | Infra ticket |

## Platform integrator (app model)

| # | Question | Why it matters |
|---|---|---|
| L1 | App model: how a merchant installs, how the app is reviewed and approved, distribution limits before approval | Timeline, compliance |
| L2 | How the platform calls the app: signature (HMAC over what, which secret), JWT session tokens, mTLS | Processor's inbound verification |
| L3 | OAuth per shop: authorization and token endpoints (per domain?), scopes, offline vs expiring tokens, refresh, revocation on uninstall | `integrator_platforms.federation`, `refresh_required` |
| L4 | API to close a payment, reject it, leave it pending, refund, void; idempotency of those calls; their rate limits | Processor calls, retries |
| L5 | API version and deprecation calendar | Version pin, maintenance |
| L6 | Time limits the platform imposes on us (session creation answer, pending duration) | Synchronous ceiling, expiry |
| L7 | Mandatory webhooks (uninstall, privacy/GDPR requests) and their deadlines | Uninstall flow, compliance |
| L8 | UI rules: embedded app or not, required screens, branding | Onboarding page |
| L9 | Test stores and sandbox for payments apps | Certification plan |
| L10 | Data the platform sends about the buyer and what we must not store | PII, compliance |

## API-first integrator

| # | Question | Why it matters |
|---|---|---|
| I1 | How do you derive `idempotency_key`? Is it stable across reloads, sessions and retries? | Contractual guarantee against double charges (certified) |
| I2 | Your HTTP client timeout vs our synchronous ceiling | Avoids abandoning results that later succeed |
| I3 | Can you handle "in process" and receive signed `operation.result` notifications? URL and secret rotation | `webhook_url`, `webhook_secret_refs` |
| I4 | Your retry policy (backoff, same key) | Load and duplicates |
| I5 | Peak volume, backfills, bulk operations | Tier `p0` vs `p1`, rate limiting |
| I6 | Who shows the "connect provider" button and where the merchant returns | Onboarding, `allowed_return_url_hosts` |
| I7 | Which providers and operations you need at launch | `allowed_targets`, scope |
