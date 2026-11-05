# Checklist: new generic mechanism

A new auth strategy, inbound signature strategy, callback validation, state reading or delivery behavior that no existing capability covers. This is the only legitimate reason to change the Dispatcher, the Webhook-Handler or the Broker core for an integration, and it is the riskiest change in Conflux.

## Classify the change (RFC 001 §7.2)

| Scenario | Example | What it requires |
|---|---|---|
| E1 – configuration | A provider fits existing strategies | Only documents and package. Not this checklist |
| E2 – new strategy in the catalog | `oauth2-client-credentials` with a new token format, a new HMAC variant | Design review first; regression over every existing target; Dispatcher (or Handler/Broker) release |
| E3 – outside the catalog | Delivery that is not HTTP request/response, a new transport | Design review, full regression, coordinated deployment window |

Governance of the transport layer: an SSR may develop; a SR or TL reviews; the EM approves the merge to the productive branch.

## Steps

- [ ] Confirm with the person that no existing strategy covers it, showing the closest one and why it does not fit. Get explicit approval for a new mechanism.
- [ ] Name it by mechanism, never by the third party (`hmac-sha256-timestamped`, `api-key-delegated`, `hmac-sha256-query`). If you cannot name it without the third party, it is not generic yet.
- [ ] Parameters live in the Registry document; no defaults that encode one provider's choice (the Handler rejects a timestamped signature without `timestamp_unit` for that reason).
- [ ] Factory + strategy registration in the component; the new strategy is selected only by configuration.
- [ ] Load validation: a document that declares the strategy with missing or contradictory parameters is rejected at load (and say how it is reported).
- [ ] Security properties: timing-safe comparison, anti-replay window, secret by reference, uniform rejection body, no secret or signature in logs.
- [ ] Unit tests of the strategy with generic examples (the architecture tests forbid third-party names in test code too) plus regression of every existing target using that component.
- [ ] Documentation in the component's README and in `contratos-federacion-y-respuestas.md` (or the doc that owns the contract).
- [ ] Only after it is merged and released, use it from the integration's document.
- [ ] Certification: mechanism cases (valid, invalid, missing parameters, replay, rotation with two secrets, misconfiguration answered as "not verifiable" rather than "invalid") in the integration's file and as platform regression.
