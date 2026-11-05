# Ticket de infraestructura: <componente o integración>

> Conflux no mantiene manifiestos de despliegue en sus repos: este ticket es el pedido al equipo de infraestructura. No incluye valores de secretos, solo sus referencias.

## Qué se despliega o cambia

<processor nuevo `Conflux.Processor-<Nombre>` / target nuevo `<target_id>` / permiso nuevo para un componente existente>

## Red

- Namespace: <`domain-<integrador>` para un processor; `identity` para el Broker>
- Entrada: <ruta del API Gateway, si aplica; nunca `/internal/*`>
- Salida permitida: <hosts del proveedor desde el Dispatcher y el Broker / host de la plataforma desde su processor / ninguna>
- Puertos: data plane 8080, management plane 9090 (solo red interna)

## Identidad y permisos (mínimo privilegio)

| Recurso | Permiso | Por qué |
|---|---|---|
| ServiceAccount | <nombre> | |
| Rol de MSK | <producir / consumir tópicos y grupos exactos> | |
| Usuario de Valkey | <prefijos y comandos: lectura de `conflux:result:*`, SUBSCRIBE `conflux:corr:*`> | |
| Usuario de Mongo | <colecciones y operaciones> | |
| KMS | <solo el rol del Broker; clave `alias/conflux-credentials-<integrator_id>` si es un integrador nuevo> | |
| Keycloak | <cliente `client_credentials` del integrador> | |

## Tópicos

| Tópico | Particiones | Retención | Notas |
|---|---|---|---|
| `conflux.dlq.<target_id>` | 2 | 14 días | Se crea con el alta del target |

## Secretos (Secrets Manager → External Secrets)

| Referencia | Qué es | Quién lo consume |
|---|---|---|

## Verificación esperada

Los casos INF del archivo de certificación que esta infraestructura tiene que hacer pasar (por ejemplo, un `kms:Decrypt` desde un rol que no es el del Broker tiene que fallar).
