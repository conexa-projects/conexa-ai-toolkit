# Components and integrator types

## Vocabulary

- **Target**: a payment provider Conflux delivers operations to (PayU, Khipu, Mercado Pago…). One Registry document in `targets`, one schema in `target_schemas`, one package `@conflux/target-<id>`, one DLQ `conflux.dlq.<target_id>`.
- **Integrator**: who brings transactions (and merchants) to Conflux. One `integrators` document, **one processor** (`Conflux.Processor-<Name>`, born from `Conflux.Processor-Seed`). "New integrator = new processor; the rest of the system is not touched" (RFC 001 §4).
- **Merchant**: the shop or company whose money moves. Has its own account at the provider.
- **Connection**: the trio `(integrator_id, merchant_id, target_id)` in `merchant_connections`, with `status` (`pending | active | revoked | reauthorization_required`) and `scope` (`target | platform`). Federated (OAuth) or manual (API key uploaded by ticket).

## Integrator types

| Type | `integrators.type` | What it is | What changes |
|---|---|---|---|
| Merchant direct | `api` | The company integrates by itself to send its own payments | One connection per provider. Its backend calls the processor's API (Keycloak `client_credentials` through the API Gateway) and receives notifications at its `webhook_url` |
| Multi-merchant platform via API | `api` | A platform with many merchants (the August guides use Tienda Nube) that calls Conflux's API from its backend | Thousands of connections. It shows the "connect" button, calls the onboarding endpoint, receives `connection.*` and `operation.result` at its `webhook_url` |
| Platform with app model | `platform` | A platform that does not call Conflux's API: the merchant installs an app, the platform calls Conflux with **its own signature**, and expects Conflux to **call its API** to close each payment (Shopify was the first) | Needs an `integrator_platforms` document (federation: OAuth with the platform per merchant), a processor that verifies the platform's inbound signature, receives `operation.result` at an internal endpoint (its `webhook_url`) and calls the platform's API with the token from the Broker. **A platform is never a target.** |

Whether something is a "platform" in the sense of the last row is a question of how it talks to us, not of its size. Ask: *does it call our API, or does it expect us to call its API?*

## Who does what

| Component | Does | Never does |
|---|---|---|
| **Processor** (one per integrator, NestJS, hexagonal) | Data plane 8080 / management 9090. Authenticates the integrator's request (or the platform's signature), applies business logic, builds the payload **by calling the target package**, wraps it in envelope 1.2, publishes to `conflux.events.p0`/`p1`, waits by rendezvous (subscribe `conflux:corr:<correlation_id>` **before** publishing, then read `conflux:result:<idempotency_key>`), answers. For a platform integrator: verifies inbound signatures, receives `operation.result`, calls the platform with a Broker token per call | Store state, tokens or credentials; call a provider; map provider payloads by hand; import another processor |
| **Target package** `@conflux/target-<id>` | Builds the exact provider payload per operation, enforces provider rules (currency decimals, expiry, refund windows), strategy + factory per integrator, publishes its JSON Schema from CI | Contain integrator business decisions; know the processor |
| **`@conflux/core` / `@conflux/envelope`** | Kafka and Redis adapters, envelope, rendezvous, health, OTel, errors | Be copied into a processor |
| **Dispatcher** (Go) | Consumes the tiers, validates envelope and payload (schema from the Registry), dedups by `idempotency_key`, resolves auth (secrets or Broker), delivers over HTTPS with resilience per endpoint, interprets with `status_mapping`, writes the board and announces, writes `txmap`/`txvence` for deferred results, sends failures to the per-target DLQ, emits usage for what it finalizes, writes `merchant_connections` from `connection.state.changed` | Receive webhooks; talk to integrators or platforms; contain any third-party name; see refresh tokens |
| **Webhook-Handler** (Go) | Public endpoint, ack-first: verify signature → publish raw to `conflux.webhooks.inbound` → 2xx. Consumer: resolve `txmap`, re-query when the target declares `reconciliation`, apply `provider_states`, take `txdone`, write the final board, announce, emit usage, notify the integrator (`operation.result`, `connection.*`) signed with `X-Conflux-Signature`, sweep `conflux:txvence` (expiry, `unconfirmed`) | Access the Broker; egress to the internet; resolve without re-querying when `reconciliation` is declared; contain any third-party name |
| **Credential Broker** (NestJS, namespace `identity`) | OAuth onboarding (targets and platforms), signed `state` with single-use nonce, code exchange, manual-credential tickets with provider validation, custody (ADR-016/017), token resolve with lock, cache and jittered renewal, publishes `connection.state.changed` | Write the Registry; have a UI; expose `/internal/*` to the internet; contain third-party names in its core |
| **Registry** (DocumentDB/Mongo, owned by the Dispatcher) | `targets`, `target_schemas`, `integrators`, `integrator_platforms`, `merchant_connections` | Hold secrets, even encrypted |

## The two result paths

- **Synchronous**: the Dispatcher's result (final, or provisional when the operation declares `announce_provisional`) goes to the board `conflux:result:<idempotency_key>` and is announced on `conflux:corr:<correlation_id>`. The processor reads it. If the processor stops waiting (~25 s; the Dispatcher's sync budget is 20 s), the result stays on the board for the integrator's retry with the same key.
- **Asynchronous** (provider confirms later): the Dispatcher writes a provisional board entry and the `txmap`; the Webhook-Handler finalizes it (webhook + re-query, or reconciliation sweep, or `unconfirmed` on expiry) and notifies the integrator with `operation.result` at its `webhook_url` — always, whatever the integrator type.

## Where a change goes (decision aid)

| The need | Goes in |
|---|---|
| A provider field, format, currency rule or refund window | Target package |
| A provider endpoint, method, path, timeout, rate limit, state values, signature parameters | `targets` document |
| A decision that depends on the integrator or the merchant | Processor |
| A call to the integrator's platform | Processor (token from the Broker) |
| A new way to authenticate, sign, validate a callback or read a state, that no existing strategy covers | New generic mechanism in the Dispatcher/Handler/Broker, named by mechanism (`checklist-mechanism.md`) |
| A new shared default for processors | New version of `@conflux/core` |

If the need does not fit a row, stop and ask.
