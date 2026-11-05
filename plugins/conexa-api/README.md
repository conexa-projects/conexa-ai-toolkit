# conexa-api

Skills para construir APIs de Conexa según los API Design Guidelines.

| Skill | Invocación | Qué hace |
|---|---|---|
| conexa-api-implementation | `/conexa-api:conexa-api-implementation` | Convierte un diseño aprobado (RFC y contrato) en código que cumple los API Design Guidelines, en cualquier lenguaje. Cubre endpoints REST y gRPC, productores y consumidores de eventos, adaptadores de proveedores externos, webhooks salientes, jobs asíncronos y el bootstrap de un repo de servicio. Construye lo transversal en un módulo `platform/` local, escribe los tests primero desde el contrato y cierra con el checklist de bloqueo. No decide estilo, plano ni modelado de la API (eso va en el RFC) ni revisa código ya escrito. |

## Instalar

```bash
claude plugin marketplace add conexa-projects/conexa-ai-toolkit
claude plugin install conexa-api@conexa
```

## Con Conflux

En los repos de Conflux se usa junto con `conflux-integration` (plugin `conflux`): esa skill decide dónde va cada pieza y esta, cómo se escribe el código dentro de cada servicio. Cuando chocan, un ADR aceptado de Conflux gana sobre los guidelines. Los choques conocidos y cómo se resuelven están en `plugins/conflux/skills/conflux-integration/references/api-guidelines.md`.
