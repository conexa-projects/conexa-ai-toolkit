# Webhook saliente

Fuente: guidelines 3.e, 7.6 (SSRF), 7.4, 10.3. Un webhook es un evento que nosotros enviamos por HTTP a una URL que registró el consumidor. El consumidor es externo y no es de confianza.

## Registro de endpoints (control plane)

- La URL se valida al registrar y **también en cada entrega** (ver SSRF).
- Estados: `enabled`, `disabled` (lo decide el consumidor) y `suspended` (lo decidimos nosotros tras una falla sostenida).
- Verificación opcional al registrar: enviar un evento `webhook.endpoint.verification` y exigir `2xx` antes de habilitar.
- Suscripción por tipo de evento. Un tipo `.v2` es un tipo nuevo al que el consumidor se suscribe explícitamente.
- El secreto de firma se genera en el servidor (256 bits o más, prefijo identificable como `whsec_`), se muestra **una sola vez**, y se guarda **cifrado** (hay que recuperarlo para firmar). Rotación con 24 horas de doble firma.

## Entrega

1. El evento sale de la outbox (`../modulo-de-plataforma/outbox-inbox.md`). Una entrega es una fila por (evento, endpoint) con su propio estado y su propia secuencia de reintentos.
2. Un worker toma la entrega, arma el request y lo envía.
3. Timeout de **10 segundos por intento**. El consumidor tiene que responder `2xx` rápido y procesar después.
4. Cualquier otra cosa (timeout, `5xx`, `4xx`, error de conexión) se reintenta.

Headers: `Webhook-Id` (el `id` del evento, para deduplicar), `Webhook-Timestamp`, `Webhook-Signature`.

## Firma

```
signed_content = "{webhook_id}.{webhook_timestamp}.{raw_body}"
signature      = base64(HMAC_SHA256(secret, signed_content))
header         = Webhook-Signature: v1,{signature}
```

- El timestamp va **dentro** del contenido firmado, para que una entrega capturada no se pueda reenviar después.
- Se documenta que el consumidor rechaza si la diferencia con su reloj supera 5 minutos y que compara la firma en tiempo constante.
- Durante una rotación se envían dos firmas (`v1,sigA v1,sigB`).

## Reintentos

Backoff exponencial con jitter, en un período total largo:

```
intento 1: inmediato      intento 5: +2 h
intento 2: +1 min         intento 6: +6 h
intento 3: +5 min         intento 7: +12 h
intento 4: +30 min        intento 8: +24 h
después: entrega fallida, disponible para reenvío manual
```

- Los reintentos son por entrega, no por endpoint. Limitar la concurrencia por endpoint (por ejemplo 10) para no generar una avalancha cuando vuelve.
- No se garantiza orden. El consumidor ordena por `time` del evento o consulta el estado.
- Respetar `Retry-After` del consumidor con un tope.

## Suspensión

Un endpoint con 100% de fallas durante un período largo (por ejemplo 72 horas, con un mínimo de intentos) pasa a `suspended`. Se notifica al consumidor por otro canal (email del contacto técnico) y se puede reactivar. Protege nuestra infraestructura y evita que el consumidor acumule deuda sin enterarse.

## SSRF (Server-Side Request Forgery)

Nuestro servidor hace un request a una URL que eligió un tercero, desde adentro de nuestra red. Un atacante puede apuntarla a servicios internos o al servicio de metadata de la nube. Todos estos controles son obligatorios:

1. Solo `https`. Cualquier otro esquema es `400`.
2. Resolver el DNS y verificar la IP resultante contra rangos prohibidos: loopback, privados, link-local, metadata de nube (`169.254.169.254`). Si cae en uno, `400 URL_NOT_ALLOWED`.
3. Verificar en **cada entrega**, no solo al registrar (protege contra DNS rebinding, que cambia la IP después del registro).
4. No seguir redirects automáticamente, o seguirlos con la misma verificación en cada salto (máximo 3).
5. Los workers corren en un segmento de red sin acceso a servicios internos ni a metadata.
6. La respuesta del endpoint no se devuelve ni se loguea completa.

Esto se implementa una vez, en un cliente HTTP de plataforma en modo "destino no confiable". Nadie lo reimplementa por endpoint.

## Tests obligatorios

URL a `http://169.254.169.254/` y a `http://10.0.0.1/` rechazadas. URL `http` rechazada. Firma verificable de forma independiente. Rotación con doble firma. Reintentos según el calendario. Suspensión tras la falla sostenida. Una entrega duplicada lleva el mismo `Webhook-Id`.
