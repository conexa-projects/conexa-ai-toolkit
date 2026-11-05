# The principles, with the cases that taught them

Rules convince less than precedents. Each principle of `SKILL.md` is listed with what went wrong in Conflux and how it was fixed. When you are tempted to bend a principle, find its row first.

## 1. Business logic only in the processor

- **Refund routing by settlement cut-off** (Shopify + Khipu): "void if before the cut-off, refund otherwise, re-query if the void's answer is lost" is a decision of the integration. It went to the processor and the target package — the provider's own rule ("a total refund is a void; a void that fails is checked before refunding") is the provider's and lives in its package; when to use it is the processor's.
- **Expiry of a pending payment**: the provider does not fix it; the integrator decides it (1 day in that processor) and passes `expiryDays` to the package. The Dispatcher never knew.

## 2. Provider knowledge in its target package

- **Khipu's canonicals first landed inside the Shopify processor.** Corrected (26/10): they moved to `@conflux/target-khipu`, agnostic to the processor, with strategy + factory per integrator. A second integrator charging with Khipu reuses it instead of copying it.
- **Amounts per currency** (CLP has no decimals; "15990.50" is rejected, never rounded) and the provider's refund policy are provider rules: package.

## 3. No third-party names in the shared core

- **The webhook consumer first lived in the Dispatcher** with provider-specific parsing. ADR-014 created the Webhook-Handler and the target document blocks (`webhook_status`, `provider_states`, `webhook.signature`) so that no provider is named in code.
- **Shopify's GraphQL builder was ported to Go** so the Dispatcher could "answer the platform" through `integrator_platforms` templates. Removed in the 26/10 redesign: the Dispatcher has no exit to integrators; the platform's processor calls its platform.
- **Strategies are named by mechanism**: `hmac-sha256-timestamped`, not "khipu-signature"; `hmac-sha256-query`, not "shopify-hmac"; `api-key-delegated`, not "khipu-auth". The architecture tests (Dispatcher, Handler, Broker) fail on a listed name; adding the new third party to their lists is part of integrating it.

## 4. Stateless processors

- The platform processor asks the Broker for the shop token on **every** call (`POST /internal/tokens/resolve` with `platform_id`) instead of caching it. A cached token is a credential outside the Broker.

## 5. Two egress doors

- **Shopify was first modeled as a target**, as if Conflux "delivered" to it. A platform is an integrator: it has its processor, its `integrators` document with `type: "platform"`, and an `integrator_platforms` document for federation only.
- The Webhook-Handler did not get Broker access or internet egress to verify per-merchant signatures; per-merchant secrets were handled by `mode: "advisory"` plus re-query.

## 6–7. Credentials and secrets

- **One global KMS key** (ADR-015, proposed) was replaced by **one key per integrator** (ADR-016): offboarding an integrator disables its key, and audit separates integrators. Per-merchant keys were rejected: linear cost, no real isolation.
- **The `credentials` collection lived in the Registry database.** ADR-017 moved it to the Broker's own DocumentDB cluster: two locks (database and KMS), both only in the Broker.
- **Manual credentials never pass through the processor**: the merchant uploads them with a single-use, time-limited ticket straight to the Broker, which validates them against the provider (`credential_validation`) before activating the connection.

## 8. Idempotency end to end

- **cobroexpress (certification mock) has no `Idempotency-Key`**: a delivery whose answer is lost cannot be resent safely. That is why the Dispatcher only retries what it knows was not processed, sends "don't know" to the DLQ as `outcome_unknown`, and lets `GET`/`DELETE` retry. Ask every provider whether it honors the key and for how long.
- **The platform's session id is the `idempotency_key`** of the payment: a platform retry never becomes a second charge. Internal queries use their own key (`<key>:get:<unix_ms>`, hashed if it exceeds 128 chars).
- **A forwarded webhook resolved twice** (F3-WHC-05): the `txdone:` mark is the arbiter, taken only with a terminal state.

## 9. The provider's truth

- **A provider rejection was classified as approved**: any 2xx counted as approved (F2-MET-06, F3-MET-01, the seed and VTEX processors). Fixed with `status_mapping` and the normalized states; a 2xx is only success if the mapping says so.
- **Khipu's states were assumed** (`expired`, `cancelled`) and the real contract said `deleted`, with the detail in `status_detail`; a `200` from `/v3/refunds` without `id` means "not completed". Found only by checking the official SDK. Verify every contract against official sources.
- **Unknown state closed as `rejected`** would make the integrator cancel an order the buyer paid. Unknown never finalizes; on expiry it closes as `unconfirmed`.
- **A provider sends its webhook timestamp in milliseconds**; read as seconds, every real webhook fell outside the tolerance. `timestamp_unit` became mandatory, with no default.

## 10. Configuration first

- Environments chosen by key (same host, another key) are **one target per environment** (`proveedor-x`, `proveedor-x-test`); the processor chooses the target. The Dispatcher never picks a key by environment.
- A `tx_id_path` typo leaves a provisional result that never closes; the Dispatcher counts it (`conflux_dispatcher_txmap_missing_txid_total`, must be 0) and it is a pre-production gate.

## 11. Metering

- CFX-240: a deferred acceptance used to be metered twice (Dispatcher at 202, Handler at the end). Now only the finalizer emits, keyed by `idempotency_key`; provisional results and notifications do not meter.

## 12. Least privilege

- The Webhook-Handler needed write access to `conflux.events.p0` and `SUBSCRIBE conflux:corr:*` for re-queries: new permissions not in the original agreement. They had to be raised with infra, and an own re-query topic is a pre-production gate.

## 13. Logs and PII

- Payer email and name were removed from the Khipu payload: not required by the provider, and PII in a payload ends up in a DLQ that more people can read.
- Dispatcher logs: one line per step, all with the envelope ids, never payloads, provider bodies, credentials or query strings.

## 14. Certification

- The platform suite has rules worth keeping: a test is never softened to pass; a known bug stays red and goes to the findings; an unbuilt piece is "blocked" with its ticket; an undecided behavior is "to define". The integration's certification file follows the same honesty.
- Known real bugs found that way: OAuth state reusable (F4-CBK-28, state fixation), `return_url` without allowlist (F4-ONB-11), token renewal without jitter (F4-TOK-27), rendezvous without resubscription after a Redis restart (F1-RDV-10).

## 15. Versioned contracts

- Raising the Kafka connection timeout was first done in one processor with a new env var. The correct change was a new `@conflux/core` version (1.3.0), published, merged, and then bumped in each consumer. A shared default belongs to the shared package.

## "Ask before deciding"

The common root of most of the above: a reasonable-looking choice made silently. Present the options, recommend one, wait.
