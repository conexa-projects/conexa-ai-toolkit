# Working with Conexa's API Design Guidelines

Conexa has company-wide API Design Guidelines and a skill that implements them, `conexa-api-implementation`. Both skills apply to Conflux work. They split the work like this:

| Question | Skill |
|---|---|
| Where a piece goes (processor, target package, Registry, new generic mechanism), what may cross which component, which Registry fields, what the third party must answer, the certification file | `conflux-integration` (this one) |
| How the code inside a service is written: layers, names, error filter, timeouts, token validation, tests from the contract, the blocking checklist | `conexa-api-implementation` |

Neither skill decides API style, plane or resource modeling: that belongs in the RFC. `conexa-api-implementation` also does not review code; reviews follow `references/review.md`.

When a task builds or changes a service endpoint, a consumer, a provider adapter or a webhook in a Conflux repo, decide **where** it goes with this skill first, then implement it with `conexa-api-implementation`, and apply the resolutions below.

## Precedence

**An Accepted Conflux ADR wins over the guidelines** (decided by the owner on 05/11/2026). Where no ADR covers the subject, the guidelines apply to new code. Where `main` already does something different and no ADR covers it, do not choose: the row is "A definir" and you ask.

## Clashes and how they resolve

### Resolved by an Accepted ADR

| Subject | Guidelines say | Conflux (wins) |
|---|---|---|
| Persistence and transactions | Relational database; idempotency row, state change and outbox in one transaction | ADR-011/017/018: DocumentDB with the allowed Mongo subset, **no multi-document transactions**. Do not design a transactional outbox or an idempotency table that needs one. |
| Circuit breaker | One per (dependency, operation) | ADR-013: one per endpoint. |
| Secret loading | Load from Secrets Manager at startup with workload identity, never through environment variables | ADR-018: static secrets from Secrets Manager synced by External Secrets Operator. Custody of merchant credentials stays with the Broker (ADR-016). |

### Open: `main` differs and no ADR decides (A definir)

| Subject | Guidelines say | `main` does | Question to decide |
|---|---|---|---|
| Idempotency key sent to the provider | Derived deterministically from resource, operation and provider; never the consumer's key | The Dispatcher forwards the envelope's `idempotency_key` as is (`pipeline.go:1077`, `delivery.go:146`), and the dedup key includes the target | Keep forwarding or derive per provider? Deriving also changes what happens when a retry with the same key lands on a different target. |
| Redis for deduplication | Redis `SET NX` only for high volume without external effects; idempotency fails closed | Dispatcher dedup and the result board live in Redis/Valkey and guard charges | Accept as a registered exception, or move it? |
| Outbound signature to integrators | Standard-webhooks headers `Webhook-Id`, `Webhook-Timestamp`, `Webhook-Signature: v1,<base64>` over `id.timestamp.body` | `X-Conflux-Signature: t=<unix>,v1=<hex>` (CFX-238, done) | Keep Conflux's format and document it as the integrator contract, or migrate before CFX-155 delivers webhooks to integrators? |
| DLQ policy | Transient failure pauses the partition and never goes to DLQ; one DLQ per topic and consumer group | `target_unavailable` goes to DLQ after retries; one DLQ per target (`conflux.dlq.<target_id>`) | Is the per-target DLQ an intended design (it is how operators reprocess one provider) or should transient failures pause instead? |
| Event envelope and topic names | `id`, `type`, `source`, `subject`, `time`, `dataVersion`, `traceparent`, `data`; topics `<domain>.<resource>.<past fact>` | `@conflux/envelope`: `event_id`, `occurred_at`, `schema_version`, `idempotency_key`, `integrator_id`, `traceparent`, snake_case | Existing topics stay as they are. For a new topic or event: guidelines or Conflux's envelope? |
| Inbound identity of a platform integrator | The tenant comes only from the Keycloak token (`tenant_id`); never from body or custom header | API integrators use Keycloak M2M at the gateway, which fits. A platform (Shopify-like) calls with its own signature and the shop comes from the signed request | Register the platform ingress as an exception to rule 2, with signature verification as the authentication. |
| Code structure | Hexagonal **per feature**, a local `platform/` module | Go services use `internal/<package>`; the processor seed is hexagonal per layer (`domain/`, `application/`, `adapters/`) | Apply to new repos only, or also align the seed? Never refactor an existing service as a side effect of an integration. |

## Where they already agree

Use these as one rule; they are the same in both skills:

- A provider's unknown state is unknown (pending), never success. In `main` an unmapped 2xx falls back to approved; that is the known gap DEL-12, and the guidelines confirm it is a bug, not a choice.
- Never fail over to another provider after a timeout: the outcome is ambiguous.
- Only retry what is idempotent and transient, never a 4xx (except 429).
- Money as an integer in minor units plus the ISO 4217 code; no card data outside the tokenizer.
- Explicit connect, read and total timeouts on every external call.
- No full bodies, tokens or unmasked sensitive data in logs.
- SSRF controls on every URL a third party chooses (`webhook_url`, `return_url`, `endpoint_base`).
- An inbound provider webhook is a notice; the source of truth is the authenticated re-query (`reconciliation`).

## How to apply it

- In step 3 of the workflow, add every open row that the integration touches to the decisions you present.
- In the certification file, the open rows the integration touches become "A definir" cases with the question.
- When `conexa-api-implementation` returns its blocking checklist, a "no cumple" caused by a resolved row above is not a defect: cite the ADR as the registered exception.
