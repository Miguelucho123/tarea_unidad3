# Plataforma de prácticas profesionales - Taller 3

[![CI/CD](https://github.com/Miguelucho123/tarea_unidad3/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/Miguelucho123/tarea_unidad3/actions/workflows/ci-cd.yml)

Prototipo funcional (MVP 0.1) de la plataforma de gestión de prácticas profesionales para Ingeniería de Software, Unidad 3.

Cubre tres requisitos del Taller 2:

1. RF02 Publicación de ofertas: una empresa registrada publica una vacante.
2. RF03 Postulación a vacantes: un estudiante se postula una sola vez a cada oferta abierta.
3. RF04 Revisión de solicitudes: coordinación aprueba o rechaza y el estado queda guardado.

En el Taller 2 se propuso Angular, NestJS y PostgreSQL. Para este prototipo usamos FastAPI, SQLite y HTML/CSS/JavaScript, que se puede ejecutar sin montar infraestructura. El modelo de datos (Empresa, Estudiante, Oferta y Postulación) y los casos de uso son los mismos. La migración al stack definitivo queda pendiente.

## Ejecutar en local

Requiere Python 3.11 o superior.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

La aplicación queda en http://127.0.0.1:8000 y la documentación de la API en http://127.0.0.1:8000/docs.

La base de datos se crea sola en `data/demo.db` con dos empresas, dos estudiantes y tres ofertas de ejemplo. Todos los datos son ficticios.

## Pruebas

```bash
pip install -r requirements-dev.txt
python -m pytest -v tests
```

| Caso | Prueba | Tipo |
|------|--------|------|
| CP-U01 | `test_publicar_oferta_valida` | API |
| CP-U02 | `test_postulacion_crea_estado_pendiente` | API |
| CP-U03 | `test_postulacion_duplicada_rechazada` | API |
| CP-U04 | `test_aprobacion_y_segunda_revision_bloqueada` | API |
| CP-U05 | `test_publicacion_empresa_inexistente` | API |
| CP-U06 | `test_unit_publicacion_rechaza_titulo_vacio` | Unitaria |
| CP-U07 | `test_unit_oferta_cerrada_no_admite_postulaciones` | Unitaria |
| CP-U08 | `test_unit_transicion_estado_controlada` | Unitaria |
| CP-I01 | `test_integracion_flujo_completo` | Integración |

Las pruebas de API usan una base SQLite temporal para cada caso, así que no tocan `data/demo.db`.

También hay una prueba de punta a punta con Playwright que levanta el servidor, publica una oferta, se postula, la aprueba desde coordinación y guarda capturas en `evidencias/`:

```bash
python -m playwright install chromium
python scripts/capturar_evidencias.py
```

## Integración y despliegue continuo

El workflow `.github/workflows/ci-cd.yml` se ejecuta en cada push y pull request a `main`:

1. Pruebas unitarias y de API con pytest. El resultado se guarda como artefacto `resultados-pytest`.
2. Recorrido e2e con Playwright. Las capturas quedan en el artefacto `capturas-e2e`.
3. Despliegue en Render, solo en `main` y solo si los dos pasos anteriores pasan. El workflow llama al deploy hook del servicio y espera hasta que `/api/health` devuelve el commit recién publicado.

Los artefactos se descargan desde la pestaña Actions, entrando a la ejecución correspondiente.

## Despliegue

La aplicación corre en Render con el plan gratuito. La configuración del servicio está en `render.yaml` y tiene el despliegue automático de Render apagado, para que solo se publique lo que pasó las pruebas en GitHub Actions.

Configuración inicial (se hace una sola vez):

1. Entrar a https://render.com con la cuenta de GitHub.
2. New > Blueprint y elegir este repositorio. Render lee `render.yaml` y crea el servicio `practicas-ucn`.
3. En el servicio, ir a Settings > Deploy Hook y copiar la URL.
4. En GitHub, Settings > Secrets and variables > Actions:
   - En Secrets, crear `RENDER_DEPLOY_HOOK_URL` con la URL del deploy hook.
   - En Variables, crear `APP_URL` con la dirección pública del servicio (por ejemplo `https://practicas-ucn.onrender.com`).
5. En Actions > CI/CD > Run workflow, ejecutar el pipeline sobre `main`.

En el plan gratuito el servicio se apaga tras 15 minutos sin visitas y la primera carga después tarda cerca de un minuto. La base SQLite vive en `/tmp`, así que se reinicia con cada despliegue y vuelve a cargar los datos de ejemplo.

## Estructura

```
app.py                     API REST y esquema SQLite
domain.py                  reglas de negocio sin dependencias de base de datos ni HTTP
static/                    interfaz web
tests/                     pruebas unitarias, de API y de integración
scripts/                   recorrido e2e con Playwright
assets/                    capturas y diagramas del informe
render.yaml                servicio en Render
.github/workflows/         pipeline de CI/CD
```

## Limitaciones

- No hay autenticación: los perfiles son de demostración y los endpoints no están protegidos. No usar con datos reales.
- No incluye carga de documentos, correos ni integración con el sistema académico.
- Usa SQLite en lugar de PostgreSQL.
- Es un prototipo para la entrega del taller, no un sistema listo para producción.
