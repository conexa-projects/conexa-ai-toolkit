# Validación de token

Fuente: guidelines 7.2 y 7.3. El proveedor de identidad es Keycloak. El servicio **valida el token completo en cada request**, aunque haya un gateway delante.

## Qué se construye

- Un middleware de autenticación que produce un `Caller` (identidad, tenant, tipo de tenant, scopes, `traceId`) y lo deja en el contexto de la request.
- Un guard de scopes y un guard de audiencia, declarativos por operación (leen `x-scopes` y la audiencia permitida del contrato).
- Un cliente de JWKS con caché y refresco.

## Validación, en este orden y sin atajos

1. Extraer de `Authorization: Bearer`. Ausente u otro esquema: `401 AUTHENTICATION_REQUIRED`.
2. Verificar el algoritmo contra una **lista fija** (`RS256`, `ES256`, `EdDSA`). `none` y cualquier otro: `401 TOKEN_INVALID`. El algoritmo nunca se toma del token.
3. Obtener la clave pública por `kid` desde el JWKS de Keycloak, con caché (TTL de 1 hora). Un `kid` desconocido dispara un refresco, con límite de frecuencia para que no se use como amplificador.
4. Verificar la firma.
5. Verificar `iss` (solo el emisor configurado), `aud` (debe incluir este servicio), `exp`, `nbf` y `env` (producción rechaza `sandbox` aunque la firma sea válida).
6. Verificar revocación si aplica (`jti` o tenant suspendido).
7. Construir el `Caller`.

Errores: `AUTHENTICATION_REQUIRED`, `TOKEN_INVALID`, `TOKEN_EXPIRED`, `TOKEN_REVOKED`, todos `401`.

## Claims requeridos

`iss`, `sub`, `aud`, `exp`, `iat`, `jti`, `scope`, `tenant_id`, `tenant_kind`, `env`. **El `tenant_id` es la única fuente del tenant.** Estos claims se configuran en Keycloak. Si el token que emite no los trae, el servicio no los reemplaza con otra fuente: se frena y se avisa.

## Autorización en tres niveles (los tres obligatorios)

1. **Scope por operación**: ¿este tipo de credencial puede ejecutarla? Guard antes del caso de uso. Falla con `403 INSUFFICIENT_SCOPE` y el scope faltante en `WWW-Authenticate`. Sin scopes comodín. Los de escritura no incluyen los de lectura.
2. **Tenant**: ¿el recurso pertenece al tenant del llamador? En el caso de uso, por ID. En listados, como filtro implícito en el repositorio. Un recurso ajeno devuelve **`404`**, no `403`, con el mismo tiempo de respuesta que uno inexistente. En creación, el tenant se asigna desde el token (`merchantId` en el body es `400`).
3. **Atributos y estado**: reglas de negocio en dominio y aplicación (roles, montos, estado del recurso). Falla con `403` y un `code` específico.

Audiencias distintas, tokens distintos: un endpoint de data plane acepta `merchant` y `partner` y rechaza `operator` con `403` aunque tenga todos los scopes.

## Servicio a servicio

mTLS con identidad por certificado para el tráfico interno, y autorización por operación con deny por defecto. Cuando un servicio actúa en nombre de un usuario, propaga el token del usuario además de su identidad. Nunca lo reemplaza.

## Tests

Los seis de autorización por operación (`../tests.md`), contra un emisor de test con JWKS real. **No se mockea el guard.** Un `kid` nuevo en el JWKS se acepta tras el refresco. Un token con `alg: none` se rechaza.
