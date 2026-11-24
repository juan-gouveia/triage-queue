# Diseño del gestor de triaje

## Estructura de la cola

`TriageQueue` utiliza un min-heap de `heapq`. Cada entrada contiene el nivel de triaje, la fecha de llegada normalizada a UTC, un contador de inserción y el paciente. El heap compara estos campos en ese orden: primero atiende el nivel menor y, dentro del mismo nivel, la llegada más antigua. Si dos fechas coinciden, el contador conserva el orden de inserción y evita comparar objetos `Patient`.

`Patient` valida sus propios datos al crearse: nombre no vacío, nivel entero entre 1 y 3 y fecha de llegada con zona horaria (por defecto, la hora actual en UTC). Así, cualquier paciente que llegue a la cola ya es válido, venga de la CLI o de otra aplicación. La prioridad de un paciente crítico recién encolado se aplica a los pacientes que aún esperan, no a uno que ya se ha retirado.

Ordenar por `arrived_at` tiene un riesgo conocido: la hora por defecto sale del reloj del sistema, y si este se ajusta hacia atrás (por ejemplo, al sincronizarse por red), un paciente que llegó después podría quedar por delante dentro de su nivel. Se acepta porque permite registrar llegadas con su hora real aunque se encolen más tarde. Si se quisiera eliminar, bastaría con ordenar solo por nivel y contador.

Para *n* pacientes, encolar y desencolar cuestan O(log n), y consultar el siguiente cuesta O(1). Listar ordena una copia en O(n log n), sin modificar la cola; calcular las estadísticas recorre el heap en O(n).

### Alternativas consideradas

- Una sola `deque` facilita el FIFO, pero no permite insertar por prioridad sin buscar o reorganizar elementos.
- Una lista ordenada permite consultar el siguiente fácilmente, pero insertar puede requerir desplazar O(n) elementos.
- Tres colas separadas, una por nivel, permiten operaciones eficientes si los pacientes se insertan en orden de llegada. Son una opción válida para los tres niveles fijos; el heap también ordena fechas explícitas que se encolen fuera de orden y permite añadir prioridades sin crear otra cola por nivel.

## Concurrencia

`TriageQueue` protege el heap y el contador con un único `threading.Lock`, de modo que varios workers del mismo proceso pueden usarla a la vez.

**Reclamar un paciente.** `dequeue()` hace, dentro del bloqueo, la comprobación de cola vacía y la retirada (`heappop`) como un solo paso. El paciente sale del heap *antes* de que el worker lo reciba, así que ningún otro worker puede verlo ni extraerlo después. Si dos workers llaman a la vez, uno espera al otro y obtiene el siguiente paciente, o `EmptyQueueError` si ya no queda nadie.

**Llegada de un crítico mientras otro worker extrae.** `enqueue()` también se ejecuta bajo el mismo bloqueo, por lo que las dos operaciones nunca se intercalan: o el crítico entra antes de la extracción (y es él quien sale), o entra después (y queda el primero para la siguiente). El heap nunca se observa a medio reorganizar.

**`peek()` no sirve para reclamar.** `peek()` y `dequeue()` son atómicas por separado, pero no en conjunto: entre ambas llamadas otro worker puede llevarse a ese paciente o puede llegar un crítico. Dos workers que hagan `peek()` verán al mismo paciente. Por eso un worker reclama siempre con `dequeue()`; `peek()` es solo informativo (por ejemplo, para mostrarlo en pantalla).

`list_queue()` y `stats()` toman una instantánea bajo el bloqueo, de modo que devuelven un estado coherente aunque haya escrituras simultáneas.

### Límites

- Si un mismo paciente pudiera encolarse dos veces, haría falta un identificador único comprobado bajo el mismo bloqueo para evitar atenderlo dos veces.
- El bloqueo vive en memoria: no coordina varios procesos ni sobrevive a un fallo. Para eso se necesitaría almacenamiento compartido con transacciones (por ejemplo, una base de datos que reclame filas con `SELECT … FOR UPDATE SKIP LOCKED`) y un estado «en atención» que se pueda recuperar si el worker cae.
