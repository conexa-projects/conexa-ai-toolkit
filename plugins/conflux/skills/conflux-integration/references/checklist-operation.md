# Checklist: new operation on an existing target

Examples: capture, void, partial refund, payment query.

- [ ] Verify the operation's contract in the provider's official docs/SDK: method, path, body, success and failure responses, idempotency, whether it confirms later, whether it can be repeated safely.
- [ ] Decide with the person: sync or async, provisional announcement, whether it is a re-query operation (then it is also `reconciliation.operation`, not metered by the Dispatcher), naming (`<object>.<verb>`, e.g. `payment.capture`, `refund.partial`).
- [ ] Target package: new function with normalized input and `{ integrator }`, provider rules (amount limits, remaining refundable balance, time windows), schema, tests. Additive minor version.
- [ ] `targets` document: `operations.<op>` with `mode`, `method`, `path` (with `{field}` parameters), `timeout_ms`, `confirms_async`/`announce_provisional` if applicable, `status_mapping` values the operation can return.
- [ ] A `DELETE` or other repeatable call that the provider answers 404/409 when already applied: decide how it maps (today a 4xx is `target_rejected`; known risk in the Dispatcher README).
- [ ] Processor: business decision of when to call it (e.g. full refund as void, partial as refund) stays here.
- [ ] Publish the package, merge, then bump the processors that use it.
- [ ] Certification: operation-specific cases (success, each rejection, retry/duplicate, timeout "don't know", limits, windows) added to the integration's existing file.
