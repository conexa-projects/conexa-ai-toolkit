# Entorno que se asume

Lo que la skill puede dar por existente y lo que no. Cada supuesto se registra en `docs/platform-assumptions.md` del servicio para que sea visible y revisable.

| Pieza | Qué se asume | Cómo se programa |
|---|---|---|
| Proveedor de identidad | Keycloak. Publica las claves de firma en su endpoint JWKS (JSON Web Key Set, la lista de claves públicas con las que se validan los tokens). | Validación de tokens por JWKS. Ver `modulo-de-plataforma/validacion-de-token.md`. |
| Claims del token | Los guidelines esperan `iss`, `aud`, `exp`, `env`, `tenant_id`, `tenant_kind`, `scope`, `jti`. Se configuran en Keycloak, no en el servicio. | Declararlos como requisito. Si falta alguno, frenar y avisar. No inventarlos. |
| Broker de mensajes | Variable por proyecto (Kafka u otro). | Dos interfaces, publicar (con outbox) y consumir (con inbox), y un adaptador por broker. Preguntar en el bootstrap. |
| Secretos | AWS Secrets Manager. | Cargar al arrancar con la identidad de la carga de trabajo (en EKS, un rol de IAM por service account). Sin credenciales en variables de entorno. |
| Observabilidad | OpenTelemetry solo si el cluster tiene colector instalado. | Instrumentar con el SDK y exportar al endpoint configurado. Si no hay colector, el servicio arranca igual y loguea a stdout. |
| Schema registry | **No existe.** | Ver abajo. |
| Librería de plataforma, pipeline de contratos, plantillas, plugins de lint propios | **No existen.** | Módulo `platform/` local. Verificaciones con las herramientas estándar de cada lenguaje. |

## Eventos sin schema registry

- El schema de cada mensaje vive como archivo (JSON Schema dentro de AsyncAPI) en el repo de contratos. Es la fuente de verdad.
- Formato por defecto: **JSON con JSON Schema**. Si el proyecto ya usa Avro o Protobuf sobre el broker, preguntarlo en el bootstrap y adaptar.
- La compatibilidad se verifica en CI antes de cada merge, contra **todas** las versiones publicadas anteriores (compatibilidad transitiva: un consumidor con el schema viejo lee mensajes nuevos, y uno con el schema nuevo lee mensajes viejos). Para Protobuf lo hace `buf breaking`. Para JSON Schema, una herramienta de diff de schemas.
- El mensaje lleva su versión en el envelope (`dataVersion`). El consumidor valida con el schema que corresponde a esa versión. Los schemas viajan en el paquete del contrato.

Los guidelines (4.2, 8.7, 14.1) asumen un registry en modo `FULL_TRANSITIVE`. La skill lo lee como "compatibilidad transitiva verificada en CI". Si el usuario decide después adoptar un registry, solo cambia el adaptador de lectura y la verificación.

## Reglas que no se pueden verificar con un plugin propio

Los guidelines mencionan plugins de lint de Conexa (`@conexa/no-vague-names`, `@conexa/filename-matches-export`, `@conexa/no-index-barrel`). No existen. Qué hacer:

- **Límites entre capas**: verificar con la herramienta del lenguaje (dependency-cruiser o eslint-plugin-boundaries en TypeScript, ArchUnit en Java y Kotlin, import-linter en Python, depguard o go-arch-lint en Go).
- **Nombres vagos, archivo igual a su clase, barrels**: revisión propia contra `nombres-por-rol.md`. Menos confiable que un lint, y se dice en el reporte.
