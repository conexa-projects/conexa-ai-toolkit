---
tags: [conflux-integration]
max_turns: 30
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Para el integrador Coppel queremos que los pagos de más de 50.000 MXN se cobren con PayU y los demás con Getnet, y que si un reembolso llega después de 30 días se rechace. ¿Dónde y cómo lo implemento en Conflux?
