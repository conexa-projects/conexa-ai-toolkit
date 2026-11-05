---
tags: [conflux-integration]
max_turns: 30
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Getnet firma sus webhooks con HMAC-SHA512 en el header X-Getnet-Signature, formato sha512=<hex>, sobre el body crudo y sin timestamp. Agregá en el Conflux.Webhook-Handler la verificación de la firma de Getnet.
