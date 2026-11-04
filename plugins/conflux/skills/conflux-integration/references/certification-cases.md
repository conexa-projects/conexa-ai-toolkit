# Certification case library

General cases every integration is checked against. Each row: area code and number, the case, type (B basic, E edge, C chaos, S security), when it applies, and the source. Instantiate every applicable case with the integration's real values (`certification.md`). Then add the specific ones; this library is the floor, not the ceiling.

Applies-when shorthands: **T** new target · **A** API integrator · **P** platform integrator · **Op** new operation · **M** new mechanism · **async** target with `confirms_async` · **rec** target with `reconciliation` · **fed** OAuth per merchant · **man** manual credentials · **noidem** `supports_idempotency_key: false` · **all** always.

## Contents

ARCH · CFG · PKG · PRC · ENV · IDM · SYNC · DEL · DLQ · AUTH · ASYNC · WHK · REC · NTF · CONN · MAN · TOK · CUST · PLT · MET · OBS · SEC · CHS · LOAD · OPS · INF · CMP · BIZ

## ARCH — Architecture rules

| Code | Case | Type | Applies | Source |
|---|---|---|---|---|
| ARCH-01 | Given the third party's names (and distinctive field names) in the three architecture-test lists, when the Dispatcher, Handler and Broker tests run, then they pass | B | all | contract premise |
| ARCH-02 | Given the processor's code, when inspected, then it has no HTTP client to the provider and builds payloads only through `@conflux/target-<id>` | B | A, P | D-05, principle 5 |
| ARCH-03 | Given the processor, when inspected, then it has no database connection, no Redis writes and no stored tokens or credentials | B | A, P | principle 4 |
| ARCH-04 | Given the domain and application layers, when linted, then they import nothing from Nest, kafkajs, ioredis or core adapters | B | A, P | ADR-005, seed guide |
| ARCH-05 | Given the target package, when inspected, then it contains no integrator business decision and every integrator variant is additive | B | T, Op | D-05 guardrails |
| ARCH-06 | Given a new mechanism, when reviewed, then it is named by mechanism, selected only by configuration and regression-tested on every existing target | B | M | RFC §7.2 |
| ARCH-07 | Given the Dispatcher, when the integration is complete, then it has no inbound or outbound traffic with the integrator or platform | B | P | contract §3.2 |
| ARCH-08 | Given the Webhook-Handler, when deployed, then it has no Broker access and no internet egress | S | async | ADR-014 |
| ARCH-09 | Given the Mongo adapters touched, when linted, then they use only the ADR-018 subset (no aggregate, sessions, watch, `$lookup`) | B | M | ADR-018 |

## CFG — Registry documents

| Code | Case | Type | Applies | Source |
|---|---|---|---|---|
| CFG-01 | Given each Registry document, when loaded by the Dispatcher and the Handler, then neither rejects it | B | T, A, P | registry-documents.md |
| CFG-02 | Given each document, when inspected, then it holds only references to secrets (`*_ref`), no values | S | all | ADR-010 D2 |
| CFG-03 | Given a deliberately broken copy for each load rule (missing window, unknown method, bad JSONPath, `announce_provisional` without `confirms_async`, advisory without reconciliation, missing `timestamp_unit`), when loaded, then it is rejected and the operation goes to `target_not_found` with alert | E | T, M | Dispatcher/Handler validation |
| CFG-04 | Given a new or changed document, when the cache TTL passes, then the change is used without redeploying | B | T, Op | ADR-010, D-07 |
| CFG-05 | Given one target per environment, when the processor sends a test operation, then it reaches the test target with the test credential and never the productive one | B | T (env by key) | Dispatcher README |
| CFG-06 | Given `status: "disabled"`, when an operation arrives, then it goes to DLQ `target_disabled` and is replayable after re-enabling | E | T | taxonomy |
| CFG-07 | Given the target's DLQ topic does not exist, when a failure occurs, then the entry goes to `conflux.dlq.desconocido` with its `target_id` (and the infra ticket creates it) | E | T | topicos-kafka.md |
| CFG-08 | Given `endpoint_base` or token endpoint pointing to an internal address, when loaded or delivered, then egress is refused | S | T | SSRF guard |
| CFG-09 | Given `integrators.allowed_targets`, when a connection to another target is requested, then the Broker rejects it | S | A, P | contract §1.3 |
| CFG-10 | Given `operations.<op>` method and path, when compared with the package's operation table, then they match exactly | B | T, Op | package README rule |

## PKG — Target package

| Code | Case | Type | Applies | Source |
|---|---|---|---|---|
| PKG-01 | Given valid normalized input for each operation, when built, then the payload equals the provider's documented body | B | T, Op | D-05 |
| PKG-02 | Given each supported currency, when an amount with valid/invalid decimals is built, then valid passes and invalid is rejected without rounding | B | T | Khipu precedent |
| PKG-03 | Given an unsupported currency, zero, negative or above-limit amount, when built, then a typed business-rule error is raised | E | T | package rules |
| PKG-04 | Given missing or malformed caller input (non-https URL, spaces in ids), when built, then a typed input error names the field | E | T, Op | package errors |
| PKG-05 | Given every produced payload, when validated against the published schema in Go (Dispatcher validator), then it passes, and an invalid one fails in both ajv and Go identically | B | T, Op | Dispatcher validation |
| PKG-06 | Given a variant for integrator X, when another integrator builds, then it receives the canonical payload unchanged | B | T (variants) | D-05 |
| PKG-07 | Given `integrator` omitted, when an operation is called, then it fails (variant selection is explicit) | E | T | package convention |
| PKG-08 | Given a release, when CI runs, then the schema is published to `target_schemas` with `published_by` and a new `updated_at` | B | T, Op | ADR-010 D3 |
| PKG-09 | Given a schema with a non-RE2 pattern or external `$ref`, when published, then CI rejects it | E | T | Dispatcher validation |
| PKG-10 | Given the consumers, when inspected, then they pin the exact package version | B | T, Op | ADR-006 |

## PRC — Processor

| Code | Case | Type | Applies | Source |
|---|---|---|---|---|
| PRC-01 | Given the processor, when started, then 8080 serves only `/v1/*` and 9090 only health/metrics | B | A, P | ADR-007, X-PLN-01 |
| PRC-02 | Given a dependency down, when probed, then liveness 200 and readiness 503 | B | A, P | X-PLN-02 |
| PRC-03 | Given a missing or invalid config variable, when started, then it fails naming every faulty variable | E | A, P | X-CFG-01..03 |
| PRC-04 | Given SIGTERM with synchronous waits in flight, when shutting down, then it answers them before closing | E | A, P | X-SHUT-06 |
| PRC-05 | Given the integrator's request invalid (schema, auth), when received, then it is rejected before publishing anything | B | A, P | seed |
| PRC-06 | Given an unauthenticated or wrongly scoped caller, when it calls `/v1/*`, then it is rejected (Gateway/Keycloak for API; signature for platform) | S | A, P | RFC D-10 |
| PRC-07 | Given `in-memory` mode, when the e2e suite runs, then the seed's platform tests still pass untouched | B | A, P | seed guide |

## ENV — Envelope and publishing

| Code | Case | Type | Applies | Source |
|---|---|---|---|---|
| ENV-01 | Given an operation, when published, then the envelope is 1.2 with `event_id`, `idempotency_key`, `integrator_id`, `target_id`, `priority`, `schema_version`, `occurred_at`, `payload`, plus `correlation_id` (sync) and `merchant_id` (per-merchant auth) | B | A, P | RFC App. A |
| ENV-02 | Given an interactive operation, when published, then it goes to `conflux.events.p0`; bulk goes to `p1` | B | A, P | D-03 |
| ENV-03 | Given Kafka unavailable, when publishing, then the integrator receives a 5xx and nothing is assumed published | E | A, P | ADR-002 (RFC) |
| ENV-04 | Given a per-merchant target and an envelope without `merchant_id`, when consumed, then DLQ `merchant_id_missing` | E | A, P | taxonomy |
| ENV-05 | Given an envelope with extra fields or wrong types, when consumed, then DLQ `envelope_malformed` without retry and nothing reaches the provider | E | A, P | D-04 |
| ENV-06 | Given a payload failing the target schema, when consumed, then DLQ `payload_schema_invalid` with the broken rules attached and no delivery | B | T, A | D-04 |

## IDM — Idempotency

| Code | Case | Type | Applies | Source |
|---|---|---|---|---|
| IDM-01 | Given the same operation sent twice with the same key, when processed, then the provider receives one delivery and both callers get the same result | B | all | F3-IDM, D-09 |
| IDM-02 | Given a payment approved after the caller's timeout, when the integrator retries with the same key minutes later, then it gets the original result and there is no second charge | B | all | flow guide 03 |
| IDM-03 | Given a retry, when published, then it carries the same `idempotency_key` and a new `correlation_id` | B | A, P | D-14 |
| IDM-04 | Given two different operations with equal amounts and different keys, when processed, then both are delivered | B | all | guide 03 |
| IDM-05 | Given a key shorter than 8 or longer than 128 characters, when received, then it is rejected | E | A, P | envelope |
| IDM-06 | Given the integrator's key derivation, when reviewed, then it is deterministic per business operation (contractual clause) | B | A, P | D-09 |
| IDM-07 | Given a provider that honors `Idempotency-Key`, when delivered, then every attempt carries the same header value | B | T | Dispatcher README |
| IDM-08 | Given a provider that ignores it, when delivered, then the header is not sent and `dedup_window_seconds` is set to the agreed window | B | T, noidem | Dispatcher README |
| IDM-09 | Given a duplicate after the board expired and outside the dedup window, when it arrives, then the residual risk is documented with the configured windows | E | T | guide 03 §3 |
| IDM-10 | Given an internal re-query, when published, then its key is `<key>:get:<unix_ms>` (hashed when longer than 128) and does not collide with the original | E | rec | contract §5.2 |
| IDM-12 | Given the provider's idempotency header name, when it differs from `Idempotency-Key`, then the target is declared without idempotency support until a configurable header exists, and the dedup window covers the agreed retry horizon | B | T | sources.md capability limits |
| IDM-11 | Given a DLQ replay inside the dedup window, when replayed, then no second charge happens | E | T | taxonomy (replay) |

## SYNC — Rendezvous

| Code | Case | Type | Applies | Source |
|---|---|---|---|---|
| SYNC-01 | Given the happy path, when the provider answers within the ceiling, then the waiting request gets the result | B | A, P | D-14 |
| SYNC-02 | Given N processor replicas, when results arrive concurrently, then each request receives its own result, never another's | B | A, P | guide 08 |
| SYNC-03 | Given the result written before the subscription completes, when the processor reads the board after subscribing, then it finds it | E | A, P | D-14.2 |
| SYNC-04 | Given no answer within the processor's wait, when it times out, then it answers "don't know" so the integrator retries with the same key, and the late result stays on the board | B | A, P | D-14 |
| SYNC-05 | Given a retry handled by another pod, when it reads the board, then it answers without re-delivering | E | A, P | guide 08 |
| SYNC-06 | Given Redis restarts during a wait, when it comes back, then the processor resubscribes and re-reads the board | C | A, P | F1-RDV-10, ADR-014 rev. |
| SYNC-07 | Given the operation timeout plus attempts, when configured, then they fit the 20 s sync budget | B | T | ADR-013 D5 |
| SYNC-08 | Given an open circuit or an exhausted budget in a sync operation, when it happens, then the caller receives the decided answer (A definir if undecided) | E | T | sources.md gaps |

## DEL — Delivery and resilience

| Code | Case | Type | Applies | Source |
|---|---|---|---|---|
| DEL-01 | Given a 5xx or timeout on a write to a provider that ignores `Idempotency-Key`, when it happens, then no retry: DLQ `outcome_unknown` with alert | B | T, noidem | Dispatcher README |
| DEL-02 | Given 429 or 503, when it happens, then it is retried with exponential backoff and jitter within the budget | B | T | Dispatcher README |
| DEL-03 | Given `GET`/`DELETE`, when a timeout happens, then it is retried even without idempotency support, without the header | E | T, Op | contract §1.1 |
| DEL-04 | Given 5 consecutive failures on `<target>:<operation>`, when the next arrives, then the breaker is open for that endpoint only, other operations and targets unaffected | B | T | ADR-013 |
| DEL-05 | Given the provider down, when other targets receive traffic, then their latency and success do not change | E | T | guide 04 |
| DEL-06 | Given traffic above `rate_limit_rpm`, when delivering, then the shared bucket enforces it across pods | B | T | ADR-013 D2 |
| DEL-07 | Given a 3xx, when received, then it is not followed and counts as rejection | S | T | taxonomy |
| DEL-08 | Given a 4xx, when received, then DLQ `target_rejected` without retry, body attached to the DLQ (not to logs) | B | T | D-08 |
| DEL-09 | Given a 2xx whose state maps to a rejection, when received, then it is `target_rejected`, never approved | B | T | F2-MET-06 precedent |
| DEL-10 | Given a `DELETE` whose first attempt was applied and the retry gets 404/409, when interpreted, then the decided mapping applies (A definir until decided) | E | T (DELETE ops) | Dispatcher README risk |
| DEL-12 | Given a 2xx whose body is not JSON, lacks the state field, or carries a value not in `status_mapping` (including an error code inside a 200), when interpreted, then it is never approved or metered as approved (today it falls back to the HTTP code: record as Falla until fixed) | B | T | sources.md capability limits |
| DEL-13 | Given a synchronous operation the provider answers as pending, when it has no `confirms_async`, then the gap (stored as final, never re-queried) is decided and certified | E | T, Op | sources.md capability limits |
| DEL-11 | Given more than `MAX_IN_FLIGHT_PER_TARGET` in flight, when a new one waits too long, then DLQ `target_unavailable` and workers stay free for other targets | E | T | Dispatcher README |

## DLQ — Failure taxonomy

| Code | Case | Type | Applies | Source |
|---|---|---|---|---|
| DLQ-01 | Given each failure code reachable by this integration, when triggered, then the entry has the right code, context and no secret | B | T | taxonomy |
| DLQ-02 | Given an entry in the DLQ, when replayed with `cmd/dlq-replay` after the cause is fixed, then it is delivered once | B | T | taxonomy |
| DLQ-03 | Given our own dependency down for 15 minutes, when it does not recover, then the message goes to `conflux.dlq.interno` with `dependency_unavailable` | C | T | CFX-230 |
| DLQ-04 | Given a DLQ entry, when inspected, then it carries no credential, token or buyer PII beyond what the provider body contains | S | T | principle 13 |

## AUTH — Outbound authentication

| Code | Case | Type | Applies | Source |
|---|---|---|---|---|
| AUTH-01 | Given the target's strategy, when delivering, then the credential goes in the declared header with the declared prefix and nowhere else | B | T | Dispatcher README |
| AUTH-02 | Given a delegated target and a connection not `active`, when an operation arrives, then DLQ `connection_not_active`, no Broker or provider call | B | fed, man | Dispatcher README |
| AUTH-03 | Given `oauth2_delegated` and a 401, when it happens, then forced refresh and exactly one more delivery; a second 401 → `reauthorization_required` and Broker notified | B | fed | D-08 |
| AUTH-04 | Given `api-key-delegated` and a 401, when it happens, then `reauthorization_required` with no second delivery (known gate: one 401 cuts the connection) | B | man | Dispatcher README gate 1 |
| AUTH-05 | Given client credentials, when the token expires, then it is renewed with its relative `expires_in` minus margin, unaffected by clock skew | E | T (client creds) | F2-AUT-16 |
| AUTH-06 | Given Secrets Manager down and a cold cache, when delivering, then `auth_unresolved`; warm, the last value is served | C | T | F2-AUT-06 |
| AUTH-07 | Given a 401 with a static platform secret, when it happens, then the secret is re-read once and delivered once more | E | T (api-key) | F2-AUT-09 |
| AUTH-08 | Given a platform connection (`scope: platform`) in the same trio, when delivering to a target, then it is not used (`auth_unresolved`) | S | P | Dispatcher README |

## ASYNC — Provisional and deferred results

| Code | Case | Type | Applies | Source |
|---|---|---|---|---|
| ASYNC-01 | Given `confirms_async` without `announce_provisional`, when the provider answers 202, then a provisional board entry is stored without announcing, with `txmap` and `txvence`, and no usage event | B | async | contract §2.1 |
| ASYNC-02 | Given `announce_provisional`, when a 2xx with pending/unknown state arrives, then the provisional is announced to the waiting processor | B | async | contract §2.1 |
| ASYNC-03 | Given `announce_provisional`, when a 2xx with a final state arrives, then the result is final, not provisional | E | async | definition 26/10 |
| ASYNC-04 | Given a 2xx without transaction id (wrong `tx_id_path`), when it happens, then it is counted (`txmap_missing_txid_total`) and the gap is listed | E | async | Dispatcher gate 4 |
| ASYNC-05 | Given a duplicate while provisional, when it arrives, then it is answered from the board and re-announced | E | async | contract §2.1 |
| ASYNC-07 | Given two async operations whose webhooks carry the same provider transaction id (refund notifying with the payment id), when both are in flight, then each resolves its own operation (or the design avoids the collision) | E | async | sources.md capability limits |
| ASYNC-06 | Given the provisional entry, when inspected, then it carries `accepted_at`, `target_tx_id` and the owner trio | B | async | contract §2.1 |

## WHK — Inbound webhooks

| Code | Case | Type | Applies | Source |
|---|---|---|---|---|
| WHK-01 | Given a correctly signed webhook, when received, then it is published to `conflux.webhooks.inbound` and answered 2xx before any processing | B | async | ADR-014 |
| WHK-02 | Given a wrong signature (enforce mode), when received, then 401 with the uniform body, nothing published | S | async | ADR-014 |
| WHK-03 | Given a timestamp outside tolerance, when received, then 401 (anti-replay) | S | async (timestamped) | contract §5.1 |
| WHK-04 | Given the provider's real timestamp unit, when a real webhook arrives, then it validates (unit declared correctly) | B | async (timestamped) | timestamp_unit precedent |
| WHK-05 | Given two active secrets during rotation, when signed with either, then it validates | E | async | Handler README |
| WHK-06 | Given advisory mode and an invalid signature, when received, then it is accepted, logged, counted and the re-query decides | E | async, rec | Handler README |
| WHK-07 | Given missing configuration on our side, when a webhook arrives, then 503 (not verifiable), never 401 | E | async | Handler README |
| WHK-08 | Given Kafka down, when a webhook arrives, then 5xx so the provider retries | C | async | ADR-014 |
| WHK-09 | Given a webhook that arrives before its `txmap`, when consumed, then it retries through `conflux.webhooks.retry` and resolves once the mapping exists, or goes to the DLQ — never discarded | E | async | CFX-211 |
| WHK-10 | Given the same webhook delivered twice (or forwarded), when consumed, then the operation is resolved once (`txdone`) | B | async | F3-WHC-05 |
| WHK-11 | Given a non-terminal state webhook, when consumed, then nothing finalizes and no `txdone` is taken | B | async | CFX-209 |
| WHK-12 | Given an unknown target in the path, when received, then it is counted apart with the uniform rejection | S | async | CFX-214 |
| WHK-13 | Given a webhook after the operation was closed (expired/unconfirmed), when consumed, then it goes to the webhooks DLQ and is visible to operations | E | async | ADR-014 rev. |
| WHK-14 | Given a webhook without transaction id, when received, then DLQ `missing_tx_id` | E | async | Handler README |

## REC — Re-query, reconciliation and expiry

| Code | Case | Type | Applies | Source |
|---|---|---|---|---|
| REC-01 | Given `reconciliation`, when a webhook arrives, then the Handler re-queries and finalizes by the re-query's state, not the webhook's | B | rec | contract §5.2 |
| REC-02 | Given each `final_success` value, when re-queried, then `approved`; each `final_failure` → `rejected`; each `non_final` → not finalized | B | rec | provider_states |
| REC-03 | Given a success state with a failure detail, when re-queried, then `rejected`; with an unlisted detail and `final_success_details` declared, then unknown | E | rec (details) | Handler README |
| REC-04 | Given an unknown state, when the window expires, then it closes as `unconfirmed`, never `rejected`, and the unrecoverable counter is checked | B | rec | contract §5.3 |
| REC-05 | Given a provisional with no webhook, when `interval_s` passes, then the sweep re-queries and reschedules while non-final and not expired | B | rec | contract §5.3 |
| REC-06 | Given non-final and expired, when swept, then `rejected` with `reason: "expired"` | B | rec | contract §5.3 |
| REC-07 | Given the re-query failing or timing out, when retries are exhausted, then DLQ `requery_failed` | E | rec | contract §6 |
| REC-08 | Given a target without `reconciliation`, when the window expires without webhook, then `unconfirmed` close with notification and usage | B | async | CFX-216 |
| REC-09 | Given the webhook and the sweep racing for the same operation, when both finalize, then one wins (`txdone` + compare-and-set) and one notification/usage is emitted | C | rec | ADR-011 v5 |
| REC-10 | Given `result_ttl_s`, when the window is long, then board, mapping and `txdone` outlive window + interval + 15 min | E | rec | TTL order rule |

## NTF — Notifications to the integrator

| Code | Case | Type | Applies | Source |
|---|---|---|---|---|
| NTF-01 | Given an async finalization, when it happens, then one `operation.result` is posted to `webhook_url` with ids and outcome, without the provider body | B | async, A, P | ADR-014 rev. |
| NTF-02 | Given the notification, when verified by the integrator, then `X-Conflux-Signature: t=…,v1=…` validates over `t.body`, with two `v1` during rotation | S | A, P | CFX-238 |
| NTF-03 | Given a redelivery, when received, then `event_id` is the same (deterministic) so the integrator deduplicates | E | A, P | Handler README |
| NTF-04 | Given the integrator down, when posting, then 3 retries then `conflux.dlq.webhooks.outbound` with status and cause | E | A, P | CFX-179 |
| NTF-05 | Given no `webhook_url`, when a notification is due, then it is dropped and counted (`outbound_no_url_total` must be 0) | E | A, P | Handler README |
| NTF-06 | Given no secret, when a notification is due, then it is never sent unsigned (DLQ `no_secret`) | S | A, P | Handler README |
| NTF-07 | Given connection changes (`active`, `revoked`, `reauthorization_required`), when they happen, then the matching `connection.*` notification is sent; `pending` sends none | B | fed, man | ADR-011 rev. |
| NTF-08 | Given the integrator's endpoint, when it receives `operation.result`, then it acts idempotently by `idempotency_key` | B | A, P | contract |

## CONN — Onboarding and connections (federated)

| Code | Case | Type | Applies | Source |
|---|---|---|---|---|
| CONN-01 | Given the onboarding request, when made, then the Broker returns `connection_id` and an `authorization_url` with a signed `state` (~5 min) | B | fed, P | RFC 13.4 |
| CONN-02 | Given a `return_url` outside `allowed_return_url_hosts`, when requested, then rejected | S | fed, P | F4-ONB-11 |
| CONN-03 | Given the callback, when the `state` is tampered, fabricated or expired, then rejected before touching the `code` | S | fed, P | guide 06 attacks 4–6 |
| CONN-04 | Given a valid `state` already used, when replayed within its validity, then rejected (single-use nonce) | S | fed, P | F4-CBK-28 |
| CONN-05 | Given an intercepted `code`, when exchanged without `client_secret` or a second time, then the provider rejects it | S | fed, P | guide 06 attacks 2–3 |
| CONN-06 | Given a successful exchange, when completed, then the credential is custodied, `connection.state.changed active` is published, the Dispatcher writes `merchant_connections`, and the merchant is redirected | B | fed, P | ADR-011 |
| CONN-07 | Given a provider that returns no refresh token, when exchanged, then it is rejected (only a platform with `refresh_required: false` may lack it) | E | fed | contract §1.2 |
| CONN-08 | Given a revocation, when requested, then all connections of the merchant in that integrator go `revoked` and later operations get `connection_not_active` | B | fed, P | contract §4.1 |
| CONN-09 | Given a reauthorization, when completed, then the new `connection_id` replaces the old by the trio's order | E | fed | ADR-011 rev. |
| CONN-10 | Given the `redirect_uri`, when an attacker uses a different one, then the provider refuses it (registered literally) | S | fed | guide 06 attack 1 |

## MAN — Manual credentials

| Code | Case | Type | Applies | Source |
|---|---|---|---|---|
| MAN-01 | Given a ticket, when used once, then it cannot be reused; used and invented tickets give the same error | S | man | contract §4.1 |
| MAN-02 | Given a ticket older than its life (10 min), when used, then rejected | S | man | Shopify page §6.2 |
| MAN-03 | Given a credential the provider accepts (`ok_status`), when uploaded, then the connection activates | B | man | contract §4.1 |
| MAN-04 | Given a credential the provider rejects (`invalid_status`), when uploaded, then `422 CREDENTIAL_REJECTED_BY_PROVIDER` without burning the ticket, up to the rejection cap (5) that burns it | B | man | contract §4.1 |
| MAN-05 | Given the provider unavailable, when uploaded, then `503 PROVIDER_UNAVAILABLE` without burning or counting | E | man | contract §4.1 |
| MAN-06 | Given two concurrent uploads on one ticket, when sent, then `409 UPLOAD_IN_PROGRESS` | E | man | contract §4.1 |
| MAN-07 | Given the upload flow, when traced, then the credential never passes through the processor, logs or topics | S | man | principle 6 |
| MAN-08 | Given CORS, when the upload page calls the Broker, then only `/manual-credentials/*` from `CORS_ALLOWED_ORIGINS` is allowed | S | man | Broker README |

## TOK — Token runtime

| Code | Case | Type | Applies | Source |
|---|---|---|---|---|
| TOK-01 | Given repeated operations, when resolving, then the access token comes from cache (500 payments ≠ 500 authentications) | B | fed, P | guide 02 |
| TOK-02 | Given concurrent resolves near expiry on several Broker pods, when renewing, then exactly one refresh reaches the provider (lock) | C | fed, P | RFC 13.5 |
| TOK-03 | Given a rotated refresh token, when renewed, then it is persisted before releasing the lock | B | fed | ADR-009 |
| TOK-04 | Given renewal, when scheduled, then the lifetime fraction is jittered between 0.8 and 0.95 per connection | E | fed, P | F4-TOK-27 |
| TOK-05 | Given `invalid_grant` from the provider/platform, when renewing, then `409 REAUTHORIZATION_REQUIRED` and `connection.state.changed reauthorization_required` | B | fed, P | contract §4.1 |
| TOK-06 | Given a forced refresh with `failed_access_token` already renewed by another request, when called, then the new token is returned without renewing again | E | fed, P | contract §4.1 |
| TOK-07 | Given a reused rotated refresh token, when the provider revokes the grant, then the connection goes to reauthorization and the integrator is notified | C | fed | guide 06 attack 7 |

## CUST — Custody

| Code | Case | Type | Applies | Source |
|---|---|---|---|---|
| CUST-01 | Given a stored credential, when inspected, then it is `{ciphertext, encrypted_data_key, binding_version}` with no plaintext | S | fed, man | ADR-016 |
| CUST-02 | Given a blob of connection A, when presented as connection B, then decryption fails (`CredentialConnectionMismatchError`) and is treated as invalid credential | S | fed, man | ADR-016, F4-KMS-10 |
| CUST-03 | Given the integrator's KMS key `alias/conflux-credentials-<integrator_id>`, when used, then only the Broker role can decrypt; a decrypt from the Dispatcher role fails in the real account | S | fed, man | ADR-016, F4-KMS-05 (infra) |
| CUST-04 | Given the credential store, when inspected, then it is the Broker's own cluster, not the Registry database (known deviation until fixed) | S | fed, man | ADR-017 |
| CUST-05 | Given the integrator offboarded, when its key is disabled, then all its merchants' credentials stop working without touching the store | E | fed, man | ADR-016 §5 |

## PLT — Platform integrator

| Code | Case | Type | Applies | Source |
|---|---|---|---|---|
| PLT-01 | Given a correctly signed platform request, when received, then accepted; tampered, unsigned or replayed, then rejected with timing-safe comparison | S | P | checklist |
| PLT-02 | Given the platform's retry of the same session, when received, then no second charge (session id = key) | B | P | contract |
| PLT-03 | Given `operation.result` at the internal endpoint, when verified, then the processor translates each outcome to the right platform call | B | P | contract §3.2 |
| PLT-04 | Given a synchronous provider rejection, when read, then the processor calls the platform's reject; if the platform does not answer, it is recorded (not durable: gate) | E | P | contract §7 |
| PLT-05 | Given each platform call, when made, then the token comes from the Broker at that moment, never cached | B | P | principle 4 |
| PLT-06 | Given the Broker answering `409 REAUTHORIZATION_REQUIRED`/`CONNECTION_NOT_ACTIVE`/`502`, when calling the platform, then the processor behaves as decided and does not lose the result | E | P | contract §4.1 |
| PLT-07 | Given the buyer coming back by `return_url`, when it happens, then the processor re-queries; returning does not mean paid | B | P | Shopify lessons |
| PLT-08 | Given uninstall, when received, then all merchant connections are revoked and later sessions refused; reinstall starts from zero | B | P | contract §4.1 |
| PLT-09 | Given the platform's OAuth callback, when the HMAC of the query, the merchant domain pattern or the merchant match fails, then rejected before exchanging | S | P | contract §4.1–4.2 |
| PLT-10 | Given the platform's API version, when deprecated, then the version in use and the migration date are recorded | E | P | L5 |
| PLT-11 | Given the platform activation step, when the provider connection is not active, then the app is not activated | E | P | Shopify lessons |

## MET — Metering

| Code | Case | Type | Applies | Source |
|---|---|---|---|---|
| MET-01 | Given a synchronous final, when delivered, then one usage event keyed by `idempotency_key` | B | T | CFX-240 |
| MET-02 | Given a deferred operation, when accepted and later finalized, then only the finalizer emits one event (`approved`, `rejected` or `unconfirmed`) | B | async | CFX-240 |
| MET-03 | Given a duplicate answered from the board, when it is not the Dispatcher's own final, then no event | E | async | contract §2.2 |
| MET-04 | Given a re-query operation, when delivered, then the Dispatcher does not meter it | E | rec | contract §1.1 |
| MET-05 | Given a 202 or 2xx-rejected, when classified, then never metered as approved | B | T | F2-MET-06 |

## OBS — Observability

| Code | Case | Type | Applies | Source |
|---|---|---|---|---|
| OBS-01 | Given an operation, when traced, then the same `traceparent` appears in the request, Kafka headers, the delivery and the Broker calls | B | all | D-11 |
| OBS-02 | Given the logs of processor, Dispatcher and Handler, when filtered by `idempotency_key`, then the whole story appears, in English, with no payload, body, token, credential, query string or PII | S | all | Dispatcher logs |
| OBS-03 | Given `/metrics`, when scraped, then no label carries merchant or correlation ids | E | all | X-PLN-08 |
| OBS-04 | Given the counters that must stay at zero (`txmap_missing_txid_total`, `outbound_no_url_total`, `reauthorization_unreported_total`, `requery_expired_unrecoverable_total`), when the run ends, then they are zero or explained | B | async | READMEs |
| OBS-05 | Given the integration, when live, then alerts exist for DLQ rate, open breakers, error rate per endpoint, refresh failures, connections in reauthorization, sync timeouts and drain time of `p0` | B | T, A, P | D-11, ADR-013 |

## SEC — Security

| Code | Case | Type | Applies | Source |
|---|---|---|---|---|
| SEC-01 | Given the repos, fixtures and topics, when grepped for secret values, then none appear | S | all | principle 6 |
| SEC-02 | Given `/internal/*` of the Broker, when called from the internet, then unreachable | S | fed, man, P | RFC D-10 |
| SEC-03 | Given the provider's or platform's TLS, when the certificate is invalid, then the call fails explicitly | S | T, P | X-CFG-09 |
| SEC-04 | Given payloads, when inspected, then buyer PII is limited to what the provider requires | S | T | principle 13 |
| SEC-05 | Given a forged webhook with a valid mapping in advisory mode, when flooded, then the API Gateway rate limit contains the re-query cost | S | async (advisory) | Handler README |
| SEC-06 | Given phishing of the merchant to authorize a malicious app, when assessed, then recorded as residual risk (provider app verification) | S | fed | guide 06 §3 |

## CHS — Chaos

| Code | Case | Type | Applies | Source |
|---|---|---|---|---|
| CHS-01 | Given the Dispatcher killed after delivering and before writing the result, when it restarts, then no second charge (dedup/`outcome_unknown`) | C | T | chaos points |
| CHS-02 | Given the Handler killed after `txdone` and before the board/notification, when it restarts, then the operation is completed exactly once | C | async | ADR-011 v5 |
| CHS-03 | Given Redis/Valkey restart, when traffic continues, then rendezvous, rate limit (fail closed) and board behave as specified | C | all | READMEs |
| CHS-04 | Given Kafka broker restart, when traffic continues, then nothing is lost or duplicated at the provider | C | all | D-01 |
| CHS-05 | Given clock skew on a pod, when delivering and renewing, then tokens and rate limit are unaffected | C | T | F2-AUT-16 |
| CHS-06 | Given the Broker down, when a delegated delivery happens, then it retries as dependency and goes to `conflux.dlq.interno` after 15 minutes | C | fed, man | Dispatcher README |

## LOAD — Load

| Code | Case | Type | Applies | Source |
|---|---|---|---|---|
| LOAD-01 | Given the expected peak for this integration, when sustained, then `p0` drain time stays within the SLO and no double charge occurs | C | A, P | guide 05 |
| LOAD-02 | Given a bulk backfill in `p1`, when interactive traffic arrives, then `p0` latency does not degrade | C | A, P | guide 05 |
| LOAD-03 | Given the provider's rate limit, when the peak exceeds it, then the bucket queues within budget and the overflow goes to the DLQ for replay, never to the provider | E | T | ADR-013 |

## OPS — Operations

| Code | Case | Type | Applies | Source |
|---|---|---|---|---|
| OPS-01 | Given each DLQ code of this integration, when it appears, then a runbook says who acts and how to replay | B | T | taxonomy |
| OPS-02 | Given `outcome_unknown`, when it appears, then the runbook checks against the provider before any replay | B | T, noidem | taxonomy |
| OPS-03 | Given DLQ retention (14 days), when entries approach expiry, then an alert fires | E | T | F2-DLQ-14 |

## INF — Infrastructure evidence (real account)

| Code | Case | Type | Applies | Source |
|---|---|---|---|---|
| INF-01 | Given the KMS key policy, when a non-Broker role decrypts, then it fails | S | fed, man | F4-KMS-05 |
| INF-02 | Given the credential store's security group, when accessed from outside namespace `identity`, then refused | S | fed, man | ADR-017 |
| INF-03 | Given the processor's network policy, when it tries internet egress (other than its platform, if platform type), then refused | S | A, P | principle 5 |
| INF-04 | Given each component's MSK role and Valkey user, when they act outside their topics/prefixes, then refused | S | all | principle 12 |
| INF-05 | Given the secrets, when inspected, then they come from Secrets Manager through ESO, not from ConfigMaps or chart values | S | all | ADR-018 |
| INF-06 | Given the target's DLQ and any new topic, when listed, then they exist with the declared partitions and retention | B | T | topicos-kafka.md |

## CMP — Compliance

| Code | Case | Type | Applies | Source |
|---|---|---|---|---|
| CMP-01 | Given the provider's own certification/approval process, when required, then it is completed and recorded | B | T | P18 |
| CMP-02 | Given the platform's app review, privacy webhooks and data rules, when required, then each is satisfied with evidence | B | P | L1, L7 |

## BIZ — Integration-specific business cases

Not generic: generate them from this integration. At least one case per:

- currency and its decimals, minimum and maximum amount;
- operation × each documented rejection reason;
- refund policy: total vs partial, number of partials, remaining balance, windows and cut-offs, lost-response recovery (query before refunding again);
- expiry of pending payments and what the buyer sees after it;
- each provider state and state/detail combination, including the ones that look like success but are not;
- each environment (test target never reaches production);
- each processor business rule (routing, chaining, target choice);
- each platform constraint (session limits, pending duration, unsupported operations declared as such);
- each open third-party question (as "A definir").
