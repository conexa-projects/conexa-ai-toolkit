# Conocimiento

Lo que aprendimos trabajando en este workspace y **no se deduce leyendo el código**. Una nota por
lección.

## El test de si vale la pena

**¿Se deduce leyendo el código o corriendo un comando?** Si sí, no escribas la nota.

Las que valen: te costó horas descubrir algo que ahora parece obvio; un comportamiento contradice lo
que sugiere el código; se descartó un enfoque y sin registro alguien lo va a volver a proponer; una
trampa de entorno o de tooling que hace perder tiempo.

Las decisiones y su porqué van aparte, en [`decisiones.md`](decisiones.md).

## Cómo agregar una

Copiá [`_template.md`](_template.md), guardala en la carpeta del área con nombre en kebab-case y
**sumala a la tabla de acá abajo**. El CI falla si una nota queda fuera del índice.

La `description` del frontmatter es lo que hace que la nota se encuentre: escribila pensando en qué
buscaría alguien que tiene el problema.

## Transversal

| Nota | Cuándo te sirve |
|---|---|
| [Decisiones](decisiones.md) | Querés saber por qué algo es como es, o vas a cambiar una decisión |
| [Idioma](procesos/idioma.md) | Vas a escribir un commit, un PR, una nota o un comentario |

<!--
Sumá una sección por área a medida que aparezcan notas. Por ejemplo:

## <Repo o área>

| Nota | Cuándo te sirve |
|---|---|
| [Título](area/nombre-de-la-nota.md) | El síntoma, como lo describiría quien lo tiene |
-->
