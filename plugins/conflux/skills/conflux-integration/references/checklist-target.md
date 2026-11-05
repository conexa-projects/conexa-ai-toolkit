# Checklist: new target (payment provider)

A target is configuration plus a package. If you find yourself writing provider-specific code in the Dispatcher, the Webhook-Handler or the Broker, stop: either the provider fits an existing mechanism, or it needs a new generic one (`checklist-mechanism.md`), decided with the person first.

## 1. Before designing

- [ ] Run the provider battery of `third-party-questions.md`. Mark each answer with its official source (docs URL, SDK version) or as open.
- [ ] Verify the contract against the provider's **official SDK or reference docs**, and against its sandbox when there is one. Field names, state values, refund responses and signature formats are where assumptions broke before.
- [ ] Decide with the person: auth strategy (existing or new mechanism), one target per environment if the environment is chosen by key, which operations enter now and which do not, sync vs async per operation, whether `announce_provisional` is needed (it is the processor that needs a provisional answer, for example to redirect a buyer).

## 2. Registry documents (`registry-documents.md`, `assets/target.template.json`)

- [ ] Check every answer against "Known capability limits" in `sources.md` (idempotency header name, auth in body, unmapped 2xx, per-target mapping, shared transaction ids).
- [ ] `targets` document per environment: `target_id`, `endpoint_base`, `status`, `auth`, `supports_idempotency_key` (false also when the provider's header name is not `Idempotency-Key`), `dedup_window_seconds` (never 0 when the provider ignores the key), `default_timeout_ms` (must fit the 20 s sync budget with attempts), `rate_limit_rpm`, every operation with `mode`, `method`, `path`, `timeout_ms`.
- [ ] Interpretation: `status_mapping` for every state the provider returns, so a 2xx is not success unless mapped as such.
- [ ] If any operation confirms later: `confirms_async`, `confirmation_window_seconds`, `tx_id_path` or `target_tx_id_header`, `webhook_status`, `webhook.signature`, `webhook.tx_id_path`, `provider_states` (with details lists if the provider splits state and detail), `reconciliation` (re-query operation declared in `operations`, `vars_from_result`, `expires_at_path`, `interval_s`), `result_ttl_s` if the window exceeds 48 h.
- [ ] Federated providers: `federation` block; register Conexa's app with the provider (exact `redirect_uri`), secrets to Secrets Manager.
- [ ] Manual credentials: `credential_validation` with a cheap, read-only endpoint and explicit `ok_status`/`invalid_status`.
- [ ] Check the document against every load-rejection rule in `registry-documents.md` before anyone loads it.

## 3. Target package `@conflux/target-<id>` (Conflux.Packages)

- [ ] Created by copying `target-khipu` (the only target package in `main`; `target-payu` was removed), with the same structure: operations as functions taking normalized input plus `{ integrator }` (mandatory), strategy + factory with the canonical construction as default.
- [ ] Payloads are exactly the provider's body (the Dispatcher delivers them as they are); path parameters at the first level.
- [ ] Provider rules enforced here: amount decimals per currency (never round), currency allowlist, expiry, refund windows and policy, field formats. Typed errors split by owner (caller input, provider business rule, our payload validation).
- [ ] JSON Schema per operation, RE2-compatible patterns, no external `$ref`; published by CI to `target_schemas` (never by hand).
- [ ] Tests: per operation, per currency (accepted and rejected amounts), per variant, conformance of produced payloads against the schema, and that adding a variant does not change the canonical output.
- [ ] Version: first `0.1.0`; later variants are additive minors; a required field is a major.

## 4. Shared core (only what configuration cannot express)

- [ ] Add the provider's names (and any distinctive field names) to the three architecture-test lists: Dispatcher `PalabrasProhibidas`, Handler `testdata/terceros.txt`, Broker `NOMBRES_BASE`. Grep first: if the name is already a sample id in those repos, propose renaming the samples to generic ids in a separate PR, and ask.
- [ ] Anything else in Dispatcher/Handler/Broker is a new mechanism: follow `checklist-mechanism.md`.

## 5. Infrastructure (ticket to infra, `assets/infra-ticket.template.md`)

- [ ] DLQ `conflux.dlq.<target_id>` (2 partitions, 14 days), created with the target.
- [ ] Secrets in Secrets Manager (app client secret, webhook signing secret, Conexa's API key) and their ESO mapping.
- [ ] Egress allowlist to the provider's hosts from the Dispatcher (and from the Broker for OAuth/validation).
- [ ] Webhook route in the API Gateway to the Webhook-Handler, if the provider sends webhooks.

## 6. Certification and documentation

- [ ] Certification file (`certification.md`) in the package's folder: all general target cases plus the provider-specific ones (currencies, states, refunds, signature, environments).
- [ ] Mock behavior needed to certify (the platform suite uses a controllable mock with `/__control`): list what the mock must simulate for this provider; building it is a separate decision.
- [ ] ADR draft and README of the package (operations table with method and path matching the `targets` document).
