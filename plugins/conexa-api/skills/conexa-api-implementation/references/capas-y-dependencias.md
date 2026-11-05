# Capas y dependencias

Fuente: guidelines 6.1. Arquitectura hexagonal pragmática: se respeta la dirección de las dependencias y la separación de adaptadores, sin una interfaz por cada clase.

## Las cuatro capas

La regla única: **las dependencias apuntan hacia adentro.**

| Capa | Contiene | Puede importar | No puede importar |
|---|---|---|---|
| Dominio | Entidades, value objects (objetos inmutables que se comparan por valor, como `Money`), eventos de dominio, errores de dominio, reglas | Solo el lenguaje y utilidades puras | Aplicación, adaptadores, framework, ORM, cliente HTTP, broker |
| Aplicación | Casos de uso, comandos, queries, puertos (interfaces que la aplicación necesita del exterior) | Dominio | Adaptadores, framework, ORM, otras features |
| Adaptadores de entrada | Controllers, handlers gRPC, consumidores de eventos, jobs, mappers | Aplicación, dominio, framework | Adaptadores de salida, otras features |
| Adaptadores de salida | Repositorios, clientes de proveedores, publicador de eventos, mappers | Puertos de aplicación, dominio, tecnología concreta | Adaptadores de entrada, otras features |

Los adaptadores de entrada son **delgados**: si tienen lógica de negocio, está en el lugar equivocado.

## Qué se abstrae con un puerto

Criterio: **¿se va a reemplazar en tests o en algún ambiente?** Si sí, puerto. Si no, clase concreta.

- Se abstrae: persistencia, proveedores externos, publicación de eventos, tiempo (`Clock`), generación de IDs.
- No se abstrae: el framework HTTP, el logger, utilidades puras, otros casos de uso.
- No se crea una interfaz por cada clase "por si acaso", ni un servicio que solo delega.

## Estructura por feature, no por capa técnica

```
src/
  <feature>/                  ej: payments
    domain/
    application/
      commands/ queries/ ports/
    adapters/
      inbound/   (http, events, jobs)
      outbound/  (persistence, providers/<proveedor>, events)
  shared/                     solo lo que usan 2 o más features del servicio
  platform/                   módulo de plataforma local (idempotencia, errores, token, outbox, resiliencia, observabilidad)
```

Adaptá los nombres de carpeta al lenguaje (paquetes en Java, módulos en Go o Python), manteniendo las cuatro capas y la agrupación por feature.

Reglas:
- Una carpeta de primer nivel por feature. Dos features que se importan todo el tiempo son una.
- **Entidad de dominio y entidad de ORM separadas.** La de dominio no tiene decoradores ni anotaciones de persistencia.
- `shared/` es solo para lo que usan dos o más features del mismo servicio. No es un cajón de sastre.
- Las features no importan clases internas entre sí. Si `refunds` necesita un pago, define su propio puerto y la feature de pagos expone un adaptador que lo implementa.
- Lo transversal (idempotencia, errores, token, outbox) va en `platform/`, con interfaz estable.

## Verificación

Configurá la herramienta de límites del lenguaje con las reglas de la tabla (ver `entorno.md`) y correla en CI. Un import de adaptadores desde dominio es un error de build, no una observación de review.

## Anti-patrones

- Carpetas por capa técnica en la raíz (`controllers/`, `services/`, `repositories/`).
- Dominio que importa framework u ORM, o entidad con decoradores de ORM.
- Caso de uso que recibe un `Request` HTTP o devuelve un `Response`.
- Repositorio con reglas de negocio (elegibilidad calculada en SQL).
- Una interfaz por clase, o un `Service` genérico con toda la lógica.
- Features que se importan internamente.
