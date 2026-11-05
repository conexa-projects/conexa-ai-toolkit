# Registry documents

The Registry is a DocumentDB/Mongo database owned by the Dispatcher (ADR-011). Documents are loaded by hand (back office or seed), never generated at runtime. **No secret ever lives here, not even encrypted**: only references (`*_ref`). A reference is the Secrets Manager SecretId as-is (`conflux/<target_id>/api_key`): the Dispatcher and the Handler use it verbatim, so a `secretsmanager:` prefix (which the Broker tolerates and some docs show) breaks them. Field names below are the ones `main` reads today (ADR-010 plus the extensions recorded in the Dispatcher's `registry.go`, the Handler's README and the federation contract). If `main` changed, `main` wins: re-check `Conflux.Dispatcher/internal/registry/registry.go` and `mongo.go` before writing a document.

Templates: `assets/target.template.json`, `assets/integrator.template.json`, `assets/integrator-platform.template.json`. They carry `_doc` keys that explain each block: **strip every `_doc` key before loading**.

## `targets` (one per provider and per environment)

| Field | Meaning | Read by |
|---|---|---|
| `_id` and `target_id` | Target id, lowercase, in **both** fields: the Dispatcher and the Handler query by `target_id`, ADR-010 names `_id`. Not one of the reserved DLQ suffixes (`desconocido`, `interno`, `webhooks.inbound`, `webhooks.outbound`, nor their `_` variants) | all |
| `endpoint_base` | Base URL; each operation adds its `path`. HTTPS, never an internal network address (SSRF guard) | Dispatcher, Broker |
| `status` | `active` \| `disabled` (disabled → DLQ `target_disabled`) | Dispatcher |
| `auth.strategy` | `api-key` · `oauth2-client-credentials` · `oauth2_delegated` · `api-key-delegated` (and `manual` for manual upload in the Broker) | Dispatcher, Broker |
| `auth.scope` | `target` (Conexa's credential) or `merchant` (per-merchant credential). Inconsistent combos are rejected (e.g. `oauth2_delegated` + `target`) | Dispatcher |
| `auth.secret_ref` | Reference to Conexa's static secret (`api-key`) | Dispatcher |
| `auth.header_name`, `auth.header_prefix` | Where the key goes (`api-key`, `api-key-delegated`); no default | Dispatcher |
| `oauth.{token_endpoint, client_id_ref, client_secret_ref, scopes}` | Client credentials (`oauth2-client-credentials`) | Dispatcher |
| `federation.{authorization_endpoint, token_endpoint, client_id_ref, client_secret_ref, scopes, pkce}` | Merchant OAuth (`oauth2_delegated`) | Broker |
| `credential_validation.{method, path, auth_header, header_prefix, ok_status[], invalid_status[]}` | How the Broker validates a manually uploaded credential before activating it | Broker |
| `supports_idempotency_key` | `false` if the provider ignores `Idempotency-Key`: the header is not sent and uncertain deliveries go to `outcome_unknown` instead of being resent | Dispatcher |
| `dedup_window_seconds` | How long the Dispatcher remembers a delivered operation. 0 = no Dispatcher dedup | Dispatcher |
| `default_timeout_ms`, `rate_limit_rpm` | Per-target timeout and shared token bucket | Dispatcher |
| `operations.<op>.mode` | `sync` \| `async` | Dispatcher |
| `operations.<op>.method` | `GET\|POST\|PUT\|PATCH\|DELETE` (default `POST`). `GET`/`DELETE` go without body and are retried even without idempotency support | Dispatcher |
| `operations.<op>.path` | Path under `endpoint_base`; `{field}` comes from `payload.<field>` (first level), URL-encoded | Dispatcher |
| `operations.<op>.timeout_ms` | Per-operation timeout | Dispatcher |
| `operations.<op>.confirms_async` | The provider confirms later (webhook or query). Requires `confirmation_window_seconds` and `webhook_status`/`provider_states` | Dispatcher, Handler |
| `operations.<op>.announce_provisional` | Only with `confirms_async`: a non-final 2xx is announced to the waiting processor | Dispatcher |
| `status_mapping.{field, values}` | Provider value → normalized state (`pending`, `authorized`, `captured`, `declined`, `voided`, `failed`, `refunded`). Without it, only the HTTP code decides | Dispatcher, Handler |
| `target_tx_id_header`, `tx_id_path` | Where the provider's transaction id is (header, or JSONPath in the body; body wins) | Dispatcher |
| `confirmation_window_seconds` | How long the provider has to confirm. Window + 15 min must fit in the board's life (48 h or `result_ttl_s`) | Dispatcher, Handler |
| `result_ttl_s` | Board TTL for this target's `confirms_async` operations (≤ 30 days). Only together with `reconciliation` (the Handler rejects it otherwise) | Dispatcher, Handler |
| `webhook_status.{source: json\|form, path, approved[], rejected[], non_terminal[]}` | Where the state is in the webhook body and which values are terminal | Handler |
| `webhook.signature.{strategy, header, timestamp_key, signature_key, signed_payload: body\|timestamp.body, timestamp_unit: s\|ms, encoding: hex\|base64, tolerance_s, mode: enforce\|advisory, secret_ref}` | Inbound signature. `timestamp_unit` is mandatory for `hmac-sha256-timestamped`. `advisory` only with `reconciliation` | Handler |
| `webhook.tx_id_path` | Transaction id in the webhook body | Handler |
| `provider_states.{status_path, final_success[], final_failure[], non_final[], detail_path, final_failure_details[], final_success_details[]}` | Declarative state machine for re-query results. A value in no list is unknown: never finalizes, closes as `unconfirmed` on expiry | Handler |
| `reconciliation.{operation, vars_from_result, expires_at_path, interval_s}` | Which declared operation re-queries a provisional result, its variables (JSONPath over the board), where the expiry is, and how often | Handler, Dispatcher |

### What gets a target document rejected at load

Treat these as validation rules for your document; a rejected target behaves as non-existent (`target_not_found`, which alerts).

- Dispatcher: `confirms_async` without `confirmation_window_seconds` or without `webhook_status`/`provider_states`; window + 15 min longer than the board's life; `tx_id_path` that does not compile; unknown `method`; malformed `{field}` in a path; `result_ttl_s` negative or > 30 days; `reconciliation` without `interval_s` or whose `operation` is not declared; `announce_provisional` without `confirms_async`; reserved id.
- Handler: `hmac-sha256-timestamped` without `timestamp_unit`; `mode: advisory` without `reconciliation`; `reconciliation` without `provider_states`, without final values, with a value in two lists, or `interval_s` 0; `detail_path` without either detail list (or a list without `detail_path`); `confirmation_window_seconds` missing with `reconciliation`, or window + `interval_s` + 15 min beyond the mapping's life; `result_ttl_s` without `reconciliation`; JSONPath outside the minimal grammar (`$`, `.field`, `[n]`, `.*`, `[*]`).
- Warning only: `signed_payload: "body"` (the timestamp is not signed, so anti-replay protects nothing).

### Related operational facts

- The target's DLQ `conflux.dlq.<target_id>` must be created by infra when the target is added (2 partitions, 14 days). Without it, entries go to `conflux.dlq.desconocido`.
- Changes are visible after the Registry cache TTL (60 s by default).
- One schema per target in `target_schemas`; publishing replaces it.

## `target_schemas`

`{ _id: <target_id>, schema: <JSON Schema 2020-12>, published_by: "@conflux/target-<id>@<version>", updated_at }`. Published by the package's CI, never loaded by hand. The Dispatcher caches by `updated_at`: publishing without moving it does not invalidate. No external `$ref`. Patterns must be RE2-compatible (no lookahead/backreference), because Go validates what ajv validated in the package.

## `integrators`

| Field | Meaning |
|---|---|
| `_id` | `integrator_id` (for a platform integrator, equal to its `integrator_platforms._id`) |
| `type` | `api` (default) \| `platform` |
| `allowed_targets` | Optional allowlist; if present, the Broker rejects connections to other targets (empty list = none) |
| `allowed_return_url_hosts` | Mandatory allowlist for onboarding `return_url` (exact host or `*.domain`, which excludes the apex) |
| `webhook_url` | Where the Webhook-Handler posts `operation.result` and `connection.*`. For a platform integrator, its processor's internal endpoint |
| `webhook_secret_refs` | One or two references (two during rotation) for `X-Conflux-Signature` |

## `integrator_platforms` (only for `type: "platform"`)

Federation only — how the merchant authorizes Conflux at the platform. How to call the platform's API is **not** here: it is the processor's code.

| Field | Meaning |
|---|---|
| `_id` | Platform id = `integrator_id` |
| `federation.authorization_endpoint`, `federation.token_endpoint` | May contain `{merchant_id}` (platforms that authorize on each shop's domain) |
| `federation.client_id_ref`, `federation.client_secret_ref` | References to Secrets Manager |
| `federation.scopes`, `federation.redirect_uri`, `federation.scope_separator` | OAuth basics |
| `federation.callback_validation` | e.g. `{strategy: "hmac-sha256-query", signature_param, merchant_param, secret_ref}` |
| `federation.refresh_required` | `true` (default): exchange must return `refresh_token` and `expires_in`; `false`: perpetual token, exchange must not return them |
| `federation.token_request_params` | Extra string params for the code exchange only (cannot override OAuth params) |
| `federation.renew_min_remaining_s` | Renew when less than this remains (only with `refresh_required: true`) |
| `federation.merchant_id_pattern` | Anchored regex the `merchant_id` must match before exchanging |
| `status` | `active` \| `disabled` |

## `merchant_connections` (written only by the Dispatcher, from `connection.state.changed`)

`{ _id, integrator_id, merchant_id, target_id, scope: target|platform, status: pending|active|revoked|reauthorization_required, return_url, credential_ref, created_at, updated_at }`. Unique `(target_id, integrator_id, merchant_id)`. A platform connection has `target_id = "platform:<platform_id>"`. Nobody else writes it; no human reads it in production.

## Allowed Mongo operations (ADR-018)

Adapters use only: `findOne`, `find` with simple filters, `insertOne`, `replaceOne` (upsert), `updateOne` with `$set`/`$unset`, `deleteOne`, `deleteMany` by indexed field, simple and compound indexes, TTL indexes. Forbidden: aggregation beyond `$match`/`$project`, multi-document transactions, change streams, `$lookup`, `$graphLookup`, text search, advanced array operators, server-side functions.
