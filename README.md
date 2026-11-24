# Gestor de cola de triaje

Gestor de la cola de espera de una unidad de urgencias, en terminal. Atiende siempre primero a los pacientes más graves (1 = crítico, 2 = urgente, 3 = estándar) y, dentro de cada nivel, por orden de llegada.

## Requisitos

Python 3.10 o superior. Solo usa la biblioteca estándar: no hay que instalar nada.

## Uso

```bash
python triage_queue.py
```

El menú permite añadir pacientes, llamar al siguiente, ver la cola, ver estadísticas por nivel y salir.

## Tests

```bash
python -m unittest -v
```

## Diseño

La elección de la estructura de datos y el comportamiento con varios workers a la vez están explicados en [DESIGN.md](DESIGN.md).
