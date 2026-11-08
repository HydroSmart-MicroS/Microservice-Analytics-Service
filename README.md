# Analytics

Agregados, tarifas editables, estimados PEN, alertas de consumo/fuga y meta mensual con aviso al 80%.

DDD: application/internal, domain/model y domain/services, infrastructure, interfaces/acl e interfaces/rest.
La base es exclusiva de este contexto. Consultas de configuración y colaboración entre servicios usan RabbitMQ RPC;
los cambios pasan por outbox y los consumidores confirman después de procesar.

## Operación en MAIN

En la red de Compose, el servicio escucha en `analytics:8080` y utiliza la base `hs_analytics`.

| Comprobación | Ruta interna |
|---|---|
| Proceso | `GET /health/live` |
| Disponibilidad | `GET /health/ready` |

Readiness verifica PostgreSQL y RabbitMQ. Revisa el resultado en el [panel de MAIN](http://127.0.0.1:8099/). Si las lecturas existen y los agregados tardan, revisa las colas de Analytics y el procesamiento del evento de lectura. Las tarifas y los totales se guardan por unidad y período.

Construye y ejecuta las pruebas del Dockerfile desde este clon con `docker build -t hydrosmart-analytics .`. Para la prueba conjunta, ejecuta `./scripts/Test-Local.ps1 -DatabaseMode Hosted` desde la carpeta de orquestación.
