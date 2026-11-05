# Sources and precedence

Conflux's rules are spread across Confluence (space **DT**, folder **Conflux**, id 498499585) and the repos. They disagree in places, because the RFC was written in August and the ADRs and the code moved on. Use this order and never pick by convenience.

## Precedence

1. **The newest Accepted ADR** on the subject. An ADR always overrides an RFC.
2. **`main` of the repos**: code, READMEs and `docs/` (for example `Conflux.Dispatcher/docs/contratos-federacion-y-respuestas.md`, `docs/taxonomia-de-fallos.md`, `docs/topicos-kafka.md`).
3. **RFC 001 and the August guides** ("Ejecución de flujos", "Conexiones y credenciales", "Packages y …").

Rules for applying it:

- **Proposed is not a rule.** ADR-012 (self-hosted IP), ADR-015, RFC 002, RFC 003 and the "GitHub Flow" page are proposals. Cite them as context, never as a requirement.
- **ADR-015 is superseded by ADR-016**, even though its page does not say so.
- **When `main` deviates from an Accepted ADR**, follow the ADR and name the deviation as a known gap (both ADR-016 and ADR-017 list their own deviations from the code).
- **Shopify + Khipu is an example, not a design.** That integration will not move forward. Use its Confluence page and code as lessons; where its page contradicts `main` (for example, it says the Dispatcher answers the platform through `integrator_platforms` templates; `main` removed that), `main` wins.
- **Conexa's API Design Guidelines rank below an Accepted Conflux ADR.** Where no ADR covers the subject they apply to new code; where `main` differs and no ADR decides, ask. The clashes and their resolutions are in `references/api-guidelines.md`.
- **If two sources of the same rank disagree, do not choose: ask.**

## What to read for each question

Read the pages with the Atlassian tools when available (cloudId `conexa-tech.atlassian.net`). If you cannot reach Confluence, say so and work from the repos, marking what you could not verify.

| Question | Source (page id) |
|---|---|
| Overall architecture, original decisions D-01…D-14 | RFC 001 (501841931). Overridden by any later ADR |
| Processors: language, framework, hexagonal rules | ADR-003 (555057153), ADR-004 (555319297), ADR-005 (554663940) |
| Packages and repos, target package rules | ADR-006 (554663948), guide "Packages y estructura de repositorios" (533463041), "07 Proyecto semilla y packages" (525336577) |
| Versioning and propagation | guide "Packages y versionado" (533037058); RFC 003 is a proposal |
| Data plane 8080 / management plane 9090 | ADR-007 (557383682) |
| `@conflux/core` adapters | ADR-008 (557907969) |
| Credential Broker | ADR-009 (558825473), updated by ADR-017 |
| Registry schemas | ADR-010 (563281922), extended by `main` (see `registry-documents.md`) |
| Registry ownership, connection state sync, the board's two writers | ADR-011 (583991300) and its 20/10 and 26/10 revisions |
| Circuit breaker and bulkhead per endpoint | ADR-013 (633339906). Overrides "per target" in RFC 001 and guide 04 |
| Webhook-Handler, outbound notifications, metering of deferred results | ADR-014 (651788289) and its 20/10 revision |
| Credential encryption | ADR-016 (700907522) |
| Credential store | ADR-017 (701399041) |
| Cloud portability, allowed Mongo subset, static secrets | ADR-018 (699990024) |
| Payment flow, rendezvous, idempotency, failure taxonomy, tiers, payload validation | "Ejecución de flujos" 01–08 (524091394, 524648450, 523730947, 524222468, 524910596, 524124162, 528285697) |
| Federation, token runtime, merchant direct, manual credentials, attacks | "Conexiones y credenciales" 01–06 (517931015, 517472272, 517668870, 517668882, 525434881, 523730956) |
| Creating a processor from the seed | "Guía para crear un Processor nuevo desde el Seed" (597524483) |
| First integration's lessons (example only) | "Integración de Shopify y Khipu en Conflux" (699138049) |
| Federation contract, provisional results, notifications (current) | `Conflux.Dispatcher/docs/contratos-federacion-y-respuestas.md` |
| Failure codes and DLQ | `Conflux.Dispatcher/docs/taxonomia-de-fallos.md` |
| Topics, partitions, per-target DLQ creation | `Conflux.Dispatcher/docs/topicos-kafka.md` |
| Delivery, retries, rate limit, secrets, logs | `Conflux.Dispatcher/README.md` |
| Target document blocks read by the Handler, notifications, gates | `Conflux.Webhook-Handler/README.md` |
| Broker API, manual credentials, platform federation, gates | `Conflux.Credential-Broker/README.md` |
| Platform-wide certification catalog (628 cases, ids F1–F4, X-) | `conflux-catalogo-certificacion.md` and `Conflux.Certification` |

## Known contradictions already resolved

So you do not re-litigate them:

| Topic | Old statement | What holds | Why |
|---|---|---|---|
| Who writes `merchant_connections` | Broker (RFC 13.3, guides 01/02/04) | Dispatcher is the only physical writer; Broker publishes `connection.state.changed` and reads | ADR-011 |
| Where merchant credentials live | `merchant_connections` in the Registry (RFC) / "external vault, Broker has no DB" (ADR-009/010) | Broker's own DocumentDB cluster, collection `credentials` | ADR-017 |
| KMS keys | one global key (ADR-015) | one key per integrator, AAD per connection | ADR-016 |
| Circuit breaker scope | per target | per endpoint `<target>:<operation>` and `<target>:auth` | ADR-013 |
| Who receives provider webhooks | Dispatcher (RFC Appendix D) | Webhook-Handler | ADR-014 |
| Who notifies the integrator | Broker (`connection.activated`, RFC 13.3) / Dispatcher (guide 01 diagram) | Webhook-Handler, always, signed `X-Conflux-Signature` | ADR-014 rev., ADR-011 rev. |
| Answering a platform integrator | Dispatcher with `integrator_platforms` templates (Shopify page) | the integrator's processor calls its platform with the Broker token; `integrator_platforms` holds federation only | `main` (contract §3.2) |
| Dispatcher language | Node (Arquitectura y Stack) | Go | ADR-009, ADR-014 |
| `txmap` TTL | `map:{tx}` ~30 s | `conflux:txmap:<target>␟<tx>` 48 h (or `result_ttl_s`) | ADR-014 rev. |
| Retry policy per target | `retry_policy` in the target (RFC Appendix B) | global parameters; only timeout and rate limit come from the Registry | ADR-010, Dispatcher README |
| Redis key names | `result:{key}`, `corr:{id}` | `conflux:result:<idempotency_key>`, `conflux:corr:<correlation_id>` | `main` |
| State validation in the OAuth callback | signature and expiry only (guide 06) | signature, expiry, single-use nonce, `aud`, callback validation, merchant match | `main` (contract §4.1) |

## Known capability limits of `main`

Checked against `main` on 2026-11-04 (Dispatcher `d8ddc59`). Re-check the cited file before relying on it; when a provider hits one of these, it needs a new generic mechanism (`checklist-mechanism.md`) or an accepted workaround, decided with the person.

| Limit | Where | Consequence for an integration |
|---|---|---|
| The idempotency header name is fixed: `Idempotency-Key` | `Conflux.Dispatcher/internal/delivery/delivery.go` (`IdempotencyHeader`) | A provider that expects another name (e.g. `X-Idempotency-Key`) does not see the key: treat it as `supports_idempotency_key: false` until a configurable header exists |
| A 2xx whose state cannot be read (body not JSON, field missing, value not mapped) falls back to the HTTP code, i.e. **approved** | `internal/registry/states.go` (`StateOf`) and `interpretar` in `internal/pipeline/pipeline.go` | Providers that answer 200 with an error code in the body, or XML, would be approved and metered. Map every value, and certify the unmapped case; it is a money risk to raise |
| `status_mapping` is per target, not per operation | `registry.go` | An operation whose `approved` means something else (a refund) is normalized like a payment |
| `api-key` puts the credential in one header | `internal/auth` | Providers that authenticate in the body or sign fields (e.g. `apiLogin`/`apiKey` + MD5 signature) need a new mechanism; the processor never holds credentials |
| A synchronous operation without `confirms_async` whose provider answers "pending" is stored as final and never re-queried | pipeline + Handler | Declare `confirms_async` with `reconciliation`, or accept and certify the gap |
| `dedup_window_seconds: 0` means no Dispatcher dedup | `registry.go` | With a provider that ignores `Idempotency-Key`, an integrator retry charges twice: set a window > 0 |
| Webhooks of different operations that carry the same provider transaction id (a refund notifying with the payment id) collide in `conflux:txmap:<target>␟<tx>` | Dispatcher/Handler txmap | Make those operations synchronous, or design the mapping key with the person |
| Platform federation in the Broker assumes the merchant id is known before authorizing and a signed callback query (`hmac-sha256-query`); the code exchange is form-urlencoded | `Conflux.Credential-Broker/src` federation module | Platforms whose shop id arrives in the token response, whose callback is unsigned, or that exchange in JSON need a new mechanism |
| `target-payu` no longer exists in `Conflux.Packages` `main` (removed in PR #15) | Conflux.Packages | Use `target-khipu` as the model for a new package |

## Gaps no document closes

When the integration touches one of these, the certification case is "A definir" and the decision goes to the person:

- Scope of `idempotency_key` beyond "per integrator" when two operations of the same business object reuse it.
- What the synchronous caller receives when the circuit is open or the budget runs out (error code vs "en proceso").
- Default dedup window when the provider does not honor `Idempotency-Key` (`dedup_window_seconds` per target, no default value decided).
- Durability of the processor's synchronous call to a platform (not retried today; contract §7).
- `status_mapping` (Dispatcher) and `provider_states` (Handler) are parallel mappings of the same data and can drift (Dispatcher README, gate 3).
- A single 401 with `api-key-delegated` cuts the merchant's connection (Dispatcher README, gate 1).
- Re-query traffic written by the Handler into `conflux.events.p0` (gate: own topic with scoped MSK role).
