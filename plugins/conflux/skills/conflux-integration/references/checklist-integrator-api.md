# Checklist: new API-first integrator (`integrators.type: "api"`)

Merchant direct or multi-merchant platform that calls Conflux's API from its backend. One integrator, one processor.

## 1. Before designing

- [ ] Run the integrator battery of `third-party-questions.md`: how it derives `idempotency_key`, its HTTP timeout vs the synchronous ceiling, whether it handles "in process" and signed notifications, its retry policy, peak volume and backfills, who shows the connect button.
- [ ] Decide with the person: which targets it uses (`allowed_targets`), sync vs async exposure per operation, the API shape it gets (`/v1/...`), which business rules are its own.

## 2. Processor `Conflux.Processor-<Name>`

- [ ] Born from `Conflux.Processor-Seed` (clone, change remote to keep history), renamed in `package.json` (kebab-case, `0.1.0`), `src/config/config.ts` (`processorName`, `integratorId`, `targetId`) and README. Node 22, exact dependency versions (`save-exact`).
- [ ] Respect the seed's map: domain and application import nothing from `@nestjs/*`, `kafkajs`, `ioredis` or core adapters (lint enforces it); do not touch `bootstrap/` (except registering use cases), `adapters/out/platform/`, `rendezvous/`, `management.controller.ts`, `test/platform/`.
- [ ] Data plane 8080 `/v1/...`, management 9090 (`/health`, `/health/liveness`, `/health/readiness`, `/metrics`, `/info`).
- [ ] Payloads only through `@conflux/target-<id>` with `{ integrator: "<integrator_id>" }`.
- [ ] Envelope 1.2: `idempotency_key` from the integrator (validate 8–128, deterministic), new `correlation_id` per request, `merchant_id` when the target's auth is per merchant, `traceparent`, correct `priority` (interactive → `p0`, bulk → `p1`).
- [ ] Synchronous wait through `@conflux/core`'s rendezvous: subscribe before publishing, read the board after subscribing, `timeout` means "don't know" (answer so the integrator retries with the same key).
- [ ] Stateless: no database, no tokens, no credentials.
- [ ] Logs in English, ids on every line, no payloads or PII.
- [ ] Tests: domain, use cases, e2e in `in-memory` mode, and the seed's platform tests untouched.

## 3. Registry and connections

- [ ] `integrators` document (`assets/integrator.template.json`): `type: "api"`, `allowed_targets`, `allowed_return_url_hosts`, `webhook_url`, `webhook_secret_refs`.
- [ ] Onboarding of merchants: federated (`POST /connections` in the Broker, `connection.activated` to its webhook) or manual (ticket), per target.
- [ ] Keycloak client for the integrator (`client_credentials`) and its API Gateway route.

## 4. Infrastructure ticket

- [ ] Namespace `domain-<integrator>`, ServiceAccount, MSK role limited to producing `conflux.events.p0`/`p1`, Valkey user read-only on `conflux:result:*` and subscribe on `conflux:corr:*`, Keycloak client, Gateway route, secrets via ESO, no internet egress.

## 5. Certification and documentation

- [ ] Certification file in the processor's `docs/certification.md`: general processor, idempotency, rendezvous, notification and onboarding cases, plus its business cases.
- [ ] ADR draft and README (which integrator, which targets, which operations).
