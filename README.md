# Andinismo de Escritorio — Backend

API REST de [andinismodeescritorio.cl](https://www.andinismodeescritorio.cl), un registro de cerros,
rutas, ascensos y andinistas de los Andes, con foco en los Andes Centrales.
Hecha con Django 5.2 + Django REST Framework sobre PostgreSQL. El panel de administración
(`/admin/`, con Jazzmin) es donde el equipo carga y edita los datos.

El frontend (Nuxt) está en
[andinismodeescritorio-frontend](https://github.com/damandak/andinismodeescritorio-frontend).

## Requisitos

- Python **3.10 o superior** (Django 5.2 no funciona con 3.9 o anteriores)
- PostgreSQL **14 o superior**

## Instalación en tu computador

```bash
git clone https://github.com/damandak/andinismodeescritorio-backend
cd andinismodeescritorio-backend

python3.12 -m venv venv          # o python3.10 / python3.11
source venv/bin/activate
which python                     # debe terminar en .../venv/bin/python
pip install -r requirements.txt

cp .env.sample .env              # y completa los valores (ver abajo)
createdb ade                     # o el nombre que pongas en DB_NAME
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver       # http://127.0.0.1:8000/admin/
```

Si `which python` **no** apunta al `venv`, algo lo está tapando:

- **conda** activo: `conda deactivate` (y para que no se active solo:
  `conda config --set auto_activate_base false`).
- Un **alias** en `~/.zshrc` o `~/.zprofile` (`alias python=...`): bórralo y abre una terminal nueva.
- Mientras tanto siempre funciona llamar al Python del venv directo: `./venv/bin/python manage.py ...`

### Variables de entorno (`.env`)

| Variable | Para qué |
| --- | --- |
| `SECRET_KEY` | Clave de Django. Larga y aleatoria; distinta en producción. |
| `DEBUG_BOOL` | `True` en tu computador, `False` en producción. |
| `ALLOWED_HOSTS` | Dominios que pueden servir el sitio, separados por coma. |
| `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Conexión a PostgreSQL. |
| `CORS_ALLOWED_ORIGINS` | URLs del frontend que pueden llamar a la API desde el navegador. |

`.env.sample` tiene un ejemplo de cada una.

## Pruebas

```bash
python manage.py test
```

Django crea una base temporal para las pruebas, así que tu usuario de PostgreSQL necesita
permiso para crear bases (una sola vez):

```bash
psql -d postgres -c "ALTER USER <DB_USER> CREATEDB;"
```

Las mismas pruebas corren solas en GitHub en cada `git push` (pestaña **Actions** del repo,
archivo `.github/workflows/ci.yml`). Una ❌ junto a un commit significa: no lo despliegues
todavía, revisa qué falló.

## Comandos útiles

| Comando | Qué hace |
| --- | --- |
| `python manage.py assign_first_ascents --dry-run` | Muestra qué primeros ascensos, "ascendido" y contadores de andinistas cambiarían al recalcularlos. No escribe nada. |
| `python manage.py assign_first_ascents` | Los recalcula y guarda (en una transacción). Normalmente no hace falta: se actualizan solos al editar ascensos. |
| `python manage.py populatedb` | Importación inicial desde planillas Excel (histórico, no se usa en el día a día). |

Las reglas de cálculo del primer ascenso están documentadas en `cerros/derived.py`.

## Desplegar en producción

En el servidor, dentro de la carpeta del backend y con el `venv` activo:

```bash
# 1. Respaldo de la base (siempre antes de actualizar dependencias o migrar)
pg_dump -Fc -h localhost -U "$(grep ^DB_USER= .env | cut -d= -f2)" \
  "$(grep ^DB_NAME= .env | cut -d= -f2)" > ~/respaldo-$(date +%F).dump

# 2. Código y dependencias
git log --oneline -1                    # anota el commit actual por si hay que volver
git pull
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput

# 3. Reiniciar el servicio del backend
```

Para volver atrás: `git checkout <commit anotado>`, `pip install -r requirements.txt` y
reiniciar. Si el despliegue incluía migraciones, restaura el respaldo con `pg_restore`.

## Estructura

```
adeback/      configuración de Django (settings, urls)
api/          API REST: vistas, serializers, búsqueda (search.py), filtros de orden, paginación
cerros/       modelos (cerros, rutas, ascensos, andinistas, imágenes...), admin,
              campos derivados (derived.py + signals.py) y comandos de manage.py
```

## Créditos

El sitio fue desarrollado por Damir Mandakovic. El proyecto lo gestionan Agustín Ferrer,
Daniel Pérez y Damir. Los datos originales provienen de distintas fuentes:

- Proyecto Nomenclatura, liderado por Ulrich Lorber
- Lista de Primeros Ascensos del sitio [Perros Alpinos](https://www.perrosalpinos.cl)
- Revista Andina, Club Andino de Chile
- Revista Andina, DAV
- Guía de los Andes Centrales, Jozsef Ambrus

Los datos se recopilan de forma continua desde distintas fuentes, incluidos andinistas activos.
