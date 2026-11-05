# Checklist: platform integrator with app model (`integrators.type: "platform"`)

Everything in `checklist-integrator-api.md` applies. On top of it, the platform calls Conflux with its own signature and expects Conflux to call its API. A platform is **never** a target. All platform-specific code lives in its processor; the shared components only gain generic, mechanism-named capabilities, decided with the person.

## 1. Before designing

- [ ] Run the platform battery of `third-party-questions.md`: app model and review, inbound signature or mTLS, OAuth per shop (domain-scoped endpoints, offline vs expiring tokens, refresh), API version and deprecation calendar, the calls that close a payment / refund / void and their limits, mandatory webhooks (uninstall, privacy/GDPR), embedded vs non-embedded UI rules, session timeouts the platform imposes on us.
- [ ] Verify against the platform's official docs and SDK; name the API version.
- [ ] Decide with the person: which operations the app supports at launch (and what it declares as unsupported), how merchants connect the payment provider (federated or manual upload), and the onboarding page (served by the processor, not by the Broker, which has no UI).

## 2. Processor

- [ ] Verifies the platform's inbound signature (HMAC, JWT, or mTLS validated at the ingress with a trusted proxy header). Timing-safe comparison.
- [ ] Translates the platform's request into the canonical operation and builds the provider payload with the target package.
- [ ] `idempotency_key` = the platform's own session/request id, so a platform retry is never a second charge.
- [ ] Receives `operation.result` at its internal endpoint (the integrator's `webhook_url`), verifies `X-Conflux-Signature`, and translates the `outcome` into the platform call.
- [ ] For synchronous results it sees itself (a provider rejection, a refund), calls the platform after reading the rendezvous. This call is not durable today (contract §7): certify it and list it as a gate.
- [ ] Gets the shop token from the Broker on every call (`POST /internal/tokens/resolve` with `{integrator_id, merchant_id, platform_id}`); never stores it. Handles `409 REAUTHORIZATION_REQUIRED`, `409 CONNECTION_NOT_ACTIVE`, `502 PROVIDER_UNAVAILABLE`.
- [ ] `return_url`/`cancel_url` of the provider point to the processor, which re-queries: coming back does not mean the buyer paid.
- [ ] Uninstall → `POST /internal/connections/revoke {integrator_id, merchant_id}`; later sessions are refused with `connection_not_active`. Reinstall starts from zero.
- [ ] Activation in the platform only after the merchant's provider connection is active.
- [ ] The platform's client secret is used by the processor to verify inbound HMAC only if the platform signs with it; it comes from Secrets Manager.

## 3. Registry and Broker

- [ ] `integrators` document with `type: "platform"`, `webhook_url` pointing to the processor's internal endpoint.
- [ ] `integrator_platforms` document (`assets/integrator-platform.template.json`): federation endpoints (with `{merchant_id}` if per-domain), refs, scopes, `redirect_uri`, `callback_validation` (existing strategy or a new mechanism), `refresh_required`, `token_request_params`, `merchant_id_pattern`.
- [ ] Register the app at the platform (exact redirect URI, required webhooks), secrets to Secrets Manager.

## 4. Shared core

- [ ] Platform names added to the three architecture-test lists.
- [ ] A new callback validation, token format or signature is a new mechanism (`checklist-mechanism.md`), named by mechanism.

## 5. Platform compliance

- [ ] The platform's app review requirements, privacy webhooks, data retention, and any UI rules, listed in the certification file as cases with evidence.

## 6. Certification and documentation

- [ ] Certification file in the processor: everything of the API integrator, plus inbound signature, OAuth per shop, token runtime, uninstall/reinstall, notification-to-platform translation, platform API errors and versions, compliance.
