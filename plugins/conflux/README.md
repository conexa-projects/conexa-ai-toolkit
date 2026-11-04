# conflux

Skills para trabajar sobre Conflux, la plataforma de integraciones de pagos de Conexa.

| Skill | Invocación | Qué hace |
|---|---|---|
| conflux-integration | `/conflux:conflux-integration` | Método y reglas innegociables para integrar en Conflux un target (proveedor de pagos), un integrador API, un integrador de tipo plataforma, una operación nueva o un mecanismo genérico nuevo; y para revisar PRs de integración. Pregunta al tercero y a la persona antes de diseñar, diseña en configuración primero, ubica cada pieza en su componente y genera el archivo de certificación de producción con todos los casos. No pushea ni publica nada sin aprobación. |

La usan tanto el equipo de Conflux como otros equipos que integren sobre Conflux: las reglas son las mismas sin importar quién esté en la sesión.

## Instalar

```bash
claude plugin marketplace add conexa-projects/conexa-ai-toolkit
claude plugin install conflux@conexa
```

## De dónde salen las reglas

De los ADR y guías del espacio DT de Confluence (carpeta "Conflux") y de `main` de los repos de Conflux, con esta precedencia: el ADR aceptado más nuevo, después `main`, después el RFC 001 y las guías de agosto. Lo que está en estado Propuesto no es regla. El detalle está en `skills/conflux-integration/references/sources.md`.

## Mantenerla cuando cambia una regla

Cuando un ADR nuevo o un cambio en `main` modifica una regla, se actualiza en este orden:

1. **El principio** en `skills/conflux-integration/SKILL.md` (si la regla es innegociable) o la referencia que la contiene.
2. **La referencia** que da el detalle (`registry-documents.md`, la checklist del tipo de integración, `certification-cases.md`) y la tabla de contradicciones resueltas de `sources.md`, si la regla nueva reemplaza a otra.
3. **La evaluación** que la cubre en `skills/conflux-integration/evals/`, o una nueva si ninguna la cubre.

Después, correr las evaluaciones con y sin la skill (`claude plugin eval skills/conflux-integration --allow-tools Write,Edit,Bash --scaffold`, desde la raíz del plugin) y comparar.
