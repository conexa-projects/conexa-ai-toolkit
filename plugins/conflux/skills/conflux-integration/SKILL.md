---
name: conflux-integration
description: "Method and non-negotiable rules for integrating anything new into Conflux, Conexa's payments integration platform (Dispatcher, Webhook-Handler, Credential Broker, Registry, processors, @conflux packages): a new target / payment provider (Mercado Pago, PayU, Khipu, Getnet...), a new integrator (API-first merchant or multi-merchant platform), an e-commerce platform integrator with its own app model (Shopify, Tienda Nube, VTEX, WooCommerce), a new operation on an existing target (capture, refund, void, query), or a new generic mechanism (auth strategy such as OAuth client credentials or delegated API key, webhook signature, callback validation, provider state machine). Use it whenever someone asks to integrate, connect, onboard or add a provider, target, integrator, platform, operation or auth/signature mechanism to Conflux, even if they only name the third party ('integrar Mercado Pago', 'conectar Tienda Nube', 'agregar captura a PayU', 'sumar OAuth client credentials a un proveedor'), and whenever someone asks to review a PR, design or document of a Conflux integration. It also produces the production-readiness certification file for the integration. Do not use it for unrelated Conflux work: fixing the certification harness, infrastructure sizing, logging or timeout tweaks, or explaining Kafka in general."
---

# conflux-integration

You are integrating something into Conflux, or reviewing an integration. Conflux exists so that a new provider or integrator is **a configuration document plus code in the right place**, never a change to the shared core. Every rule below protects that property. The first integration (Shopify + Khipu, October 2026) broke several of them and had to be redone; the lessons are in `references/principles.md`.

This skill is a method, not an architecture document. The architecture lives in Confluence (space DT, folder "Conflux") and in the repos' `main`. `references/sources.md` says what to read for each question and **which source wins when they disagree**. Read it before designing anything.

## How to work with the person asking

- **Ask before deciding.** Whenever a request admits more than one reasonable answer — which repo or layer a change goes in, configurable or fixed, a new field or an existing one, a package version, a branch name, a new mechanism or reuse of one — present the options with your recommendation and wait for an explicit answer. Do not pick one and build it. What the person already said explicitly is decided; do not ask again.
- **Never guess a third party's behavior.** If the provider's or platform's contract is not verified against its official docs or SDK, it is an assumption: list it as one and ask.
- **Outward-facing actions need a yes**: pushing, opening PRs, publishing packages, writing to Confluence, loading Registry documents into a shared environment. In Conflux.Packages, Credential-Broker, Dispatcher and Webhook-Handler a push to a PR branch dismisses existing approvals: warn before pushing.
- Write code identifiers, files and folders in English; comments and documentation in Spanish, matching each repo. Logs in English.

## Non-negotiable principles

Each principle: the rule, why it exists, and how to verify it. `references/principles.md` has the real cases where each one was broken and how it was fixed.

1. **Business logic and orchestration live only in the integrator's processor.** Multi-call flows, routing by date or flag, choosing a target, chaining operations, deciding a refund strategy. *Why:* the processor is the only per-integrator code; anything else is shared by every integrator. *Verify:* if a decision needs to know which integration it is, it is in the processor.
2. **What a provider requires lives in its target package `@conflux/target-<id>`** (Conflux.Packages): payload shape, amounts per currency, expiry and refund-window rules, with strategy + factory selecting the variant for the integrator that instantiates it (canonical by default). Only structural differences of the provider's contract go in; integrator business decisions stay in the processor; every variant is an additive minor. The package's CI publishes its JSON Schema to `target_schemas`. *Why:* one provider serves many processors; copying its contract into each processor is the drift Conflux was built to end (D-05). *Verify:* the processor builds the payload by calling the package; no provider field names are mapped by hand in the processor.
3. **Zero third-party names in the Dispatcher, the Webhook-Handler and the Broker core.** Only generic capabilities, instantiated from configuration and named by mechanism (`hmac-sha256-timestamped`, `api-key-delegated`, `hmac-sha256-query`), never by the first third party that needs them. *Why:* a third-party name in shared code is the first `if target ==`, and every one of those is a deploy the day the third party changes its API. *Verify:* add the new third party's names to the three architecture tests (Dispatcher `internal/arquitectura/terceros_test.go`, Handler `internal/arquitectura/testdata/terceros.txt`, Broker `test/architecture/sin-terceros.test.ts`) and they pass. Some names (`payu`, `mercadopago`, `tiendanube`, `coppel`) are already used as sample ids in those repos' tests and comments, and the tests scan test files too: grep first, and if the name is there, say so and ask whether to rename the samples to generic ids (`proveedor-x`, `plataforma-y`) in a separate PR before adding it.
4. **Processors are stateless.** No database, no stored tokens, credentials or shops. They read the board and connections, publish to Kafka, wait by rendezvous, and ask the Broker for a token on every call. *Why:* any state in a processor is a second source of truth with its own failure modes. *Verify:* no Mongo connection or Redis writes in the processor; Valkey user read-only.
5. **Egress has exactly two doors.** Calls to a payment provider go only through the Dispatcher (as a delivery). Calls to an integrator's platform go only through that integrator's processor, with the token the Broker resolves. The Dispatcher has no inbound or outbound traffic with integrators; the Webhook-Handler has no internet egress and no Broker access. *Why:* the Dispatcher is the protected core; keeping integrators out of it keeps it generic and auditable. *Verify:* no provider HTTP client in a processor; no platform client outside its processor.
6. **Merchant credentials exist only in the Broker** (ADR-016, ADR-017): envelope encryption with one KMS key per integrator, AAD binding per connection, persisted in the Broker's own DocumentDB cluster, separate from the Registry. The Registry holds references only. Never in a processor, a log, a Kafka message, an env var, a Kubernetes Secret, a ConfigMap or the chart. *Verify:* grep for secret values in logs and topics during certification finds nothing; the Registry documents have only `*_ref` fields.
7. **Conexa's static secrets** (app client secrets, webhook signing secrets, infrastructure credentials) come from Secrets Manager through External Secrets (ADR-018). *Verify:* only `secret_ref` / `*_ref` values in Registry documents and chart values.
8. **Idempotency end to end.** The integrator defines `idempotency_key` per business operation, deterministic, 8–128 chars, never random; the Dispatcher deduplicates; the `Idempotency-Key` header goes to the provider only if it supports it (`supports_idempotency_key`); an internal query carries its own key. *Why:* the scenario that defines Conflux is the payment approved at 40 s and retried at 5 min; it must charge once. *Verify:* the IDM cases of the certification file.
9. **The truth belongs to the provider, not to the messenger.** A webhook never resolves an operation without re-querying when the target declares `reconciliation`; the provider state machine is declarative (`provider_states`, `status_mapping`); an unknown state is never `rejected` — it stays pending and closes as `unconfirmed`. *Why:* `rejected` makes the integrator act on something the buyer may have paid. *Verify:* the target document declares `provider_states` and the ASYNC/REC cases pass.
10. **What the code does not know, the Registry knows.** Operations with `mode`, `method`, parameterized `path`, `confirms_async`, `announce_provisional`; `tx_id_path`, `status_mapping`, `provider_states`, `reconciliation`, `credential_validation`, `result_ttl_s`, auth strategy, webhook signature. Design the document before any code. *Verify:* the document passes the Dispatcher's and the Handler's load validation (`references/registry-documents.md` lists what each rejects).
11. **One usage event per operation, emitted by whoever finalizes it** (CFX-240), keyed by `idempotency_key`. A provisional result does not meter; notifications to the integrator do not meter. *Verify:* the MET cases.
12. **Least privilege per component.** Own ServiceAccount, MSK role scoped to its topics and groups, Mongo user per collection, Valkey user per prefix. A new component or a new permission is born with its infrastructure ticket (`assets/infra-ticket.template.md`). Conflux does not keep deployment manifests in its repos: infrastructure is requested from the infra team.
13. **No PII or secrets in logs, DLQ or metrics; no per-merchant label cardinality; trace end to end.** Never log payloads, provider bodies, credentials, tokens or URL query strings. Buyer PII (email, name, document) does not travel in payloads unless the provider requires it, and then never reaches logs. *Verify:* the OBS and SEC cases.
14. **No integration reaches production without its certification file.** It lists every case that must hold — general and specific to this integration — and nothing is marked Pass without evidence. An assertion is never softened to pass; an undecided behavior is "A definir", never an invented expectation. See "Certification" below.
15. **Contracts are versioned.** Envelope 1.2 is shared Go/TS with a conformance set; the target schema is published by the package's CI (manual schema loads are forbidden); packages are pinned to exact versions. A cross-repo change goes in order: publish the package version, merge it, then bump the consumers.

## Workflow

Follow these steps in order. Steps 2 and 3 are where integrations went wrong before; do not skip them because the request sounds simple.

1. **Ground and classify.** Read `references/sources.md` and the sources it lists for this class. Classify the request; each class has a checklist:
   | Class | Checklist |
   |---|---|
   | New target (payment provider) | `references/checklist-target.md` |
   | New integrator, API-first (`integrators.type: "api"`) | `references/checklist-integrator-api.md` |
   | New integrator, platform with app model (`integrators.type: "platform"`) | `references/checklist-integrator-platform.md` |
   | New operation on an existing target | `references/checklist-operation.md` |
   | New generic mechanism (auth, signature, callback validation, state format) | `references/checklist-mechanism.md` |
   | Review of an integration PR, design or doc | `references/review.md` |

   Most real requests combine classes (a new platform integrator that charges with a new provider is two integrations). Say which classes apply. What "platform" means and who does what: `references/components.md`.
2. **Ask the third party before designing.** Produce the questions from `references/third-party-questions.md` for this type and mark which ones are already answered by official documentation (cite it) and which are open. Open questions that change the design block the design; say so. Then check each answer against what `main` can actually do today (`references/sources.md`, "Known capability limits"): a provider that needs something Conflux does not support yet is a new mechanism, not a configuration detail.
3. **Decide with the person.** List the decisions this integration needs (where each piece goes, new mechanism or existing one, environments as separate targets, versions, branch names, what is out of scope) with your recommendation for each, and wait.
4. **Design in configuration first.** Write the Registry documents (`targets` and/or `integrators`, `integrator_platforms`) from `assets/` before touching code. If something cannot be expressed in a document, decide — with the person — whether it is (a) processor logic, (b) target package logic, or (c) a new generic capability for the Dispatcher, Handler or Broker (then it is also a "new mechanism" and follows its checklist). Never (d) third-party code in those components.
5. **Build the artifacts** the checklist lists, each in its repo, on a branch from `main`, with tests. Code inside a service (endpoint, consumer, provider adapter, webhook) follows Conexa's API Design Guidelines through the `conexa-api-implementation` skill, with the Conflux resolutions in `references/api-guidelines.md`.
6. **Write the certification file** (below).
7. **Document.** A short ADR from `assets/adr-integration.template.md` in the owning repo's `docs/`, ready for the person to publish in the Confluence ADR folder (publishing is their call), plus the README/docs updates of each touched repo. Pre-production gates are listed explicitly, never left implicit.
8. **Check against `references/anti-patterns.md`** before calling it done, and say which gates remain open.

## Certification

The certification file is a document, not an executable suite: your analysis of **every case that must hold** for this integration to be declared ready for production, with how each one is verified and where its evidence goes. Build it with `references/certification.md` (format, IDs, states, where the file lives) and the case library in `references/certification-cases.md`. Include all applicable general cases plus the ones specific to this integration (its currency rules, its refund policy, its state machine, its signature, its environments, its platform's callbacks). When a behavior is not decided anywhere, the case is "A definir" with the question to decide. Write it in Spanish, like the rest of Conflux's documentation, from `assets/certification.template.md`.

## Reference map

| File | Read it when |
|---|---|
| `references/sources.md` | Always first: where each rule comes from and which source wins |
| `references/principles.md` | You need the reasoning or the real precedent behind a principle |
| `references/components.md` | Deciding which component does what; integrator types |
| `references/registry-documents.md` | Writing or reviewing any Registry document |
| `references/checklist-*.md` | Building that class of integration |
| `references/third-party-questions.md` | Step 2 |
| `references/certification.md`, `references/certification-cases.md` | Step 6 |
| `references/anti-patterns.md` | Step 8, and during any review |
| `references/review.md` | Reviewing a PR or design |
| `references/api-guidelines.md` | Writing service code, or when Conexa's API Design Guidelines and Conflux seem to disagree |
| `assets/*` | Templates for documents, certification, ADR and infra ticket |
