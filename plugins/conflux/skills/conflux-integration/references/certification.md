# The certification file

A document, not a suite: your detection of **every case that has to hold** before this integration goes to production, how each is verified, and where its evidence goes. The team executes it (harness, sandbox, manual run, infra evidence) and fills the evidence and state. It follows the platform suite's honesty rules: a case is never softened to pass, a known bug stays "Falla", an unbuilt piece is "Bloqueado" with its ticket, and an undecided behavior is "A definir" with its question.

## Where it lives

| Integration | File |
|---|---|
| New target | `Conflux.Packages/packages/target-<id>/CERTIFICATION.md` |
| New integrator (API or platform) | `Conflux.Processor-<Name>/docs/certification.md` |
| New operation or mechanism | Added to the file of the integration that needs it (and the mechanism's cases also listed in the component's README as regression) |

An integration that combines a new platform and a new provider has two files; end-to-end cases go in the processor's file and reference the target's file. Confirm the location with the person if the repo layout differs.

## Building it

1. Start from `assets/certification.template.md` (Spanish, like all Conflux docs).
2. Choose with the person a short uppercase prefix for the integration (e.g. `MPAGO`, `TNUBE`). IDs are `<PREFIX>-<AREA>-<NN>`, numbered within each area, stable once published (never renumber; retire with "Retirado" and a reason).
3. Walk `certification-cases.md` area by area. For each case, decide whether it applies to this integration using its "Applies when" column and the Registry documents you designed. Include every applicable case; when in doubt, include it and say why in "Verificación".
4. Instantiate each case with this integration's concrete values (its states, currencies, operations, signature, endpoints), so that it can be executed without re-reading the library. A generic case copied verbatim is not instantiated.
5. Add the **specific cases**: every answer to the third-party questions, every rule in the target package, every business decision in the processor, every platform constraint produces at least one case (mark them `Específico`). Typical sources: currency decimals and limits, refund windows and partials, expiry, state/detail combinations, signature format and unit, environment per target, platform API version, uninstall, compliance items.
6. Add the **gap cases**: each gap in `sources.md` that this integration touches, and each open third-party question, as "A definir" with the question and who decides.
7. Fill "Referencia" with the ADR, document or platform catalog id (e.g. `F3-IDM-01`, `ADR-016`) that the case derives from.
8. Write the closing section: counts per state and type, open gates, and the production verdict rule below.

## Columns

| Column | Content |
|---|---|
| ID | `<PREFIX>-<AREA>-<NN>` |
| Caso | "Dado … cuando … entonces …", with concrete values |
| Tipo | `B` básico · `E` borde · `C` caos · `S` seguridad |
| Alcance | `General` (from the library) · `Específico` (this integration) |
| Verificación | How: harness against the deployed compose, provider sandbox, manual run with steps, code review, infra evidence in the real account, document review. Precede with "Técnica:" when the technique is not obvious |
| Referencia | Source of the rule |
| Evidencia | Link or path to the run, log query, screenshot, PR, ticket. Empty until executed |
| Estado | `Pendiente` · `Pasa` · `Falla` · `Bloqueado` (motivo + ticket) · `A definir` (pregunta + quién decide) · `Retirado` (motivo) |

Assertions are against real state — topics, Redis keys, Registry documents, calls received by the provider or mock, logs — never against an HTTP answer alone.

## Production verdict

The integration is ready for production when:

- every `B` and `E` case is `Pasa`;
- every `C` and `S` case is `Pasa`, or accepted in writing as a known risk by the EM (record who and when in the file);
- no `A definir` remains in a `B` or `E` case;
- every `Bloqueado` is either resolved or accepted in writing with its ticket;
- the pre-production gates listed in the file are closed or accepted in writing.

Never write that the integration is ready yourself; summarize the counts and what blocks the verdict.
