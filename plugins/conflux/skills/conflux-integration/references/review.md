# Reviewing an integration PR, design or document

Review against the rules, not against taste. Read the diff and the files it touches in full; for a design, read the Registry documents it proposes.

## Order

1. **Classify** what the change integrates (target, API integrator, platform integrator, operation, mechanism) and which repos it touches. A PR that touches the Dispatcher, Handler or Broker core for an integration is a "new mechanism" until proven otherwise: check that it went through `checklist-mechanism.md` (design review, generic name, regression).
2. **Placement** (`components.md`): every piece of logic is in its component. Flag business logic outside the processor, provider rules outside the package, platform calls outside the processor, provider calls outside the Dispatcher.
3. **Third-party names**: grep the shared components for the third party's name and field names; check the three architecture-test lists were updated.
4. **Registry documents** (`registry-documents.md`): no secrets, all load-validation rules satisfied, `status_mapping` covers every state, `provider_states` and `reconciliation` present when `confirms_async`, `supports_idempotency_key` honest, one target per environment.
5. **Money safety**: idempotency key derivation, what is retried, what goes to `outcome_unknown`, unknown states never `rejected`, duplicates answered from the board, `txdone` taken only on terminal states.
6. **Credentials and secrets**: nothing sensitive in code, tests, fixtures with real values, logs, topics or env; custody follows ADR-016/017.
7. **Logs and metrics**: ids on every line, no payloads, bodies, tokens or PII, bounded labels.
8. **Contracts and versions**: envelope untouched or versioned, schema published by CI, exact pins, package published before consumers bump.
9. **Certification**: the file exists, covers general and specific cases, has evidence for every "Pasa", and nothing was softened.
10. **Process**: branch from `main`, one purpose per PR, README/docs updated, gates listed.

## Output

For each finding: file and line, the rule it breaks (principle number or anti-pattern), the concrete failure it causes (inputs → wrong result), and the fix that respects the rules. Separate blocking findings (money, credentials, third-party names in core, wrong placement) from improvements. If something is ambiguous in the sources, say so instead of deciding it in the review.
