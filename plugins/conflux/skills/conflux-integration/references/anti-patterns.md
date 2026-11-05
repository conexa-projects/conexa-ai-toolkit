# Anti-patterns: if you catch yourself doing this, stop

Each one happened, or nearly happened, in Conflux. Stop, say which one it is, and propose the alternative to the person.

| You are about to… | Instead |
|---|---|
| Write a third party's name (or its field names) in the Dispatcher, the Webhook-Handler or the Broker core | Express it in the Registry document, or create a generic mechanism named by mechanism |
| Name a strategy after the third party that needs it | Name it by what it does |
| Model a platform (Shopify, Tienda Nube, VTEX) as a target | Integrator with `type: "platform"`, its processor, and `integrator_platforms` for federation |
| Make the Dispatcher call or answer an integrator or platform | The processor calls its platform; asynchronous results reach the integrator through the Handler's `operation.result` |
| Put a provider's payload rules or canonicals in a processor | `@conflux/target-<id>` with strategy + factory |
| Put an integrator's business decision in the target package | The processor |
| Port business logic to Go "so the Dispatcher does it" | Processor or package |
| Store a token, credential, shop or any state in a processor | Ask the Broker per call; read the board |
| Make a processor call a provider directly | Publish the envelope; the Dispatcher delivers |
| Give the Webhook-Handler Broker access or internet egress | Advisory signature + re-query, or a generic per-merchant secret design decided with the person |
| Resolve an operation from what a webhook says when the target can be re-queried | Declare `reconciliation`; the Handler re-queries |
| Treat any 2xx as success | `status_mapping` for every state; unmapped is not approved |
| Close an unknown provider state as `rejected` | Unknown stays pending and closes as `unconfirmed` |
| Retry a timeout or 5xx on a write when the provider ignores `Idempotency-Key` | DLQ `outcome_unknown`; only `GET`/`DELETE` or providers that honor the key are retried |
| Generate a random `idempotency_key`, or a new one on retry | Deterministic per business operation; same key on retry, new `correlation_id` |
| Create a KMS key per merchant, or use one global key | One key per integrator (ADR-016) |
| Store credentials in the Registry, env vars, Kubernetes Secrets, ConfigMaps or the chart | Broker's credential store; static secrets via Secrets Manager + ESO |
| Let a credential pass through the processor or a chat/email/ticket | Single-use ticket straight to the Broker, validated against the provider |
| Add a UI to the Broker | The processor serves the onboarding page |
| Use `aggregate`, transactions, change streams or `$lookup` in a Mongo adapter | The ADR-018 subset |
| Load a target schema by hand | The package's CI publishes it |
| Use `^`/`~` ranges for `@conflux/*` | Exact versions; publish, merge, then bump |
| Fix a shared default in one consumer with a new env var | New version of the shared package |
| Log a payload, provider body, credential, token, query string or buyer PII | Ids only |
| Label metrics by merchant or correlation id | Bounded labels |
| Relax, skip or comment out a certification case to get green; mark "blocked" to clean the report | Leave it failing and record it; "blocked" only for an unbuilt piece with its ticket |
| Raise a timeout so a test passes, or lower a load test's volume | Fix the cause or record the finding |
| Mark a case "Pasa" without evidence | Evidence column filled, or it stays "Pendiente" |
| Invent the expected result of an undecided behavior | "A definir" with the question |
| Decide where a change goes, a version, a branch or a new field without asking | Options + recommendation, then wait |
| Assume a provider's field, state or signature format | Verify against official docs/SDK or list it as an open question |
| Push to a PR branch with approvals without warning | Warn: in Packages, Broker, Dispatcher and Handler a push dismisses approvals |
| Generate deployment manifests inside a Conflux repo | Infra ticket |
