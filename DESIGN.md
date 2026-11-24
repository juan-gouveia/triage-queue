# Diseño del gestor de triaje

## Estructura de la cola

`TriageQueue` utiliza un min-heap de `heapq`. Cada entrada contiene el nivel de triaje, la fecha de llegada normalizada a UTC, un contador de inserción y el paciente. El heap compara estos campos en ese orden: primero atiende el nivel menor y, dentro del mismo nivel, la llegada más antigua. Si dos fechas coinciden, el contador conserva el orden de inserción y evita comparar objetos `Patient`.

Las fechas de llegada deben incluir zona horaria. `Patient` genera por defecto una fecha UTC; si se proporciona una fecha explícita, la cola rechaza las que no incluyen zona horaria. La prioridad de un paciente crítico recién encolado se aplica a los pacientes que aún esperan, no a uno que ya se ha retirado.

Para *n* pacientes, encolar y desencolar cuestan O(log n), y consultar el siguiente cuesta O(1). Listar ordena una copia en O(n log n), sin modificar la cola; calcular las estadísticas recorre el heap en O(n).

### Alternativas consideradas

- Una sola `deque` facilita el FIFO, pero no permite insertar por prioridad sin buscar o reorganizar elementos.
- Una lista ordenada permite consultar el siguiente fácilmente, pero insertar puede requerir desplazar O(n) elementos.
- Tres colas separadas, una por nivel, permiten operaciones eficientes si los pacientes se insertan en orden de llegada. Son una opción válida para los tres niveles fijos; el heap también ordena fechas explícitas que se encolen fuera de orden y permite añadir prioridades sin crear otra cola por nivel.

## Posible concurrencia

La implementación actual es de un solo hilo y **no** garantiza seguridad ante acceso concurrente. Si se incorporan workers en un mismo proceso, todas las operaciones sobre el heap y el contador deben coordinarse con el mismo bloqueo; las lecturas también deben protegerse para obtener una vista coherente.

Para reclamar un paciente, un worker adquiriría el bloqueo, seleccionaría y retiraría el primer paciente y lo registraría como «en atención» antes de liberar el bloqueo. Otro worker no podría retirar la misma entrada durante esa transición. La inserción de un nuevo paciente crítico también se realizaría bajo el bloqueo: si se completa antes de la selección, tiene prioridad; si ocurre después, no desplaza al paciente ya reclamado.

Para evitar procesar dos veces a un mismo paciente que pudiera encolarse más de una vez, haría falta además una identidad única y comprobarla bajo la misma sincronización. Estas medidas describen un posible diseño, no están implementadas. Un bloqueo en memoria tampoco ofrece recuperación ante fallos ni coordinación entre procesos; para ello se necesitaría almacenamiento y transacciones compartidas.
