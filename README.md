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
| `SECURE_HSTS_SECONDS` | Opcional. Cuánto tiempo recuerda el navegador usar siempre HTTPS. Por defecto 3600 (1 hora); cuando todo ande bien, `31536000` (1 año). |
| `SECURE_SSL_REDIRECT` | Opcional. `True` solo si nginx no redirige ya `http://` a `https://`. |
| `SECURE_COOKIES` | Opcional, para emergencias: `False` si el login del admin deja de funcionar porque se entra por `http://`. |
| `CSRF_TRUSTED_ORIGINS` | Opcional. Por defecto `https://` + cada dominio de `ALLOWED_HOSTS`. |

`.env.sample` tiene un ejemplo de cada una.

## Seguridad del admin

- **Intentos de login:** 5 contraseñas incorrectas seguidas para un mismo usuario desde una
  misma IP bloquean ese usuario desde esa IP por 1 hora (con
  [django-axes](https://django-axes.readthedocs.io/)). Quien intente adivinar contraseñas no te
  bloquea a ti desde tu conexión. Los intentos se ven en el admin, en **Axes**.
- **Desbloquear al tiro:** `python manage.py axes_reset` (todo) o
  `python manage.py axes_reset_username <email>` (un usuario).
- **En producción** (`DEBUG_BOOL=False`) las cookies del admin solo viajan por HTTPS y se
  envía HSTS. Django necesita que nginx le avise que la conexión fue HTTPS y le pase la IP real:
  `include proxy_params;` en el bloque `location` que apunta a Django ya lo hace
  (`X-Forwarded-Proto` y `X-Forwarded-For`).
- El admin está en español y muestra las horas en hora de Chile. Las fechas se escriben
  `31/12/1950` (también acepta `1950-12-31`).

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
| `python manage.py generate_image_sizes` | Crea los tamaños de cada foto (miniatura, portada y 1.600 px) que falten. Con `--dry-run` solo cuenta; con `--list-orphans` lista archivos de `media/images` que ya nadie usa (no borra nada). Las fotos nuevas se procesan solas al subirlas. |
| `python manage.py axes_reset` | Desbloquea a quien quedó bloqueado por intentos fallidos de login. |
| `python manage.py asignar_ubicacion --dry-run` | Muestra qué país y región se asignaría a cada cerro según sus coordenadas, y deja un CSV (para Excel) con todos. No escribe nada. Ver "Ubicación según coordenadas". |
| `python manage.py asignar_ubicacion` | Lo aplica. `--margen 500` cambia la distancia mínima al límite (por defecto 2000 m). |
| `python manage.py populatedb` | Importación inicial desde planillas Excel (histórico, no se usa en el día a día). |

Las reglas de cálculo del primer ascenso están documentadas en `cerros/derived.py`.

## Revisar datos en el admin

- **Cerros:** filtros por estado de la ubicación, sin país, sin región, sin altitud y sin
  coordenadas (columna derecha de la lista).
- **Ascensos:** filtro "Fecha: sin fecha". Un ascenso sin fecha se guarda con la fecha vacía
  (ya no hace falta poner 0001-01-01) y queda al final al ordenar por fecha, sin contar como
  primer ascenso frente a uno con fecha.

## Cuentas de usuario

Cualquiera puede crearse una cuenta en el sitio (`/crear-cuenta`) con nombre público, correo y
contraseña. Lo maneja [django-allauth](https://docs.allauth.org/) a través de su API JSON, en
`/djangoapi/_allauth/browser/v1/`; los datos propios del usuario están en `/djangoapi/me/`.

- **Importante:** `ALLOWED_HOSTS` debe incluir `www.andinismodeescritorio.cl`, porque el sitio
  llama a `/djangoapi/` en su propia dirección (nginx lo envía a Django).
- **Editores:** en el admin, Usuarios → marcar "Es staff" y agregar al grupo **Editores** (puede
  editar todo menos usuarios). El grupo se crea y actualiza solo con cada `migrate`. Los
  administradores son superusuarios.
- **Reclamos de perfil de andinista:** un usuario con el correo confirmado busca su ficha y pide
  vincularla. En el admin, "Reclamos de perfil de andinista" → acción "Aprobar" o "Rechazar".
- **Protección:** límites de intentos por IP y por cuenta (allauth y axes) y un campo invisible que
  solo llenan los bots. La confirmación del correo es opcional para entrar.
- Los textos de los correos están en `templates/account/email/`.

### Enviar correos con Gmail (gratis)

Sin configurar correo, los emails (confirmación, recuperar contraseña) solo quedan en el log de
gunicorn (`sudo journalctl -u gunicorn`), así que nadie los recibe. Para enviarlos con Gmail:

1. Crea una cuenta de Gmail para el sitio (o usa una existente).
2. Activa la verificación en dos pasos: <https://myaccount.google.com/security>.
3. Crea una contraseña de aplicación en <https://myaccount.google.com/apppasswords> (nombre:
   "Andinismo"). Google muestra 16 letras: cópialas sin espacios.
4. Agrega al `.env` del backend y reinicia gunicorn:
   ```
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_HOST_USER=la.cuenta@gmail.com
   EMAIL_HOST_PASSWORD=las16letras
   ```
5. Prueba: `python manage.py sendtestemail tu@correo.com`.

Gmail permite unos 500 correos al día, más que suficiente por ahora.

## Propuestas de cambios e historial

Cualquier usuario con el correo confirmado puede proponer correcciones a un cerro, ruta, ascenso o
andinista, o proponer un cerro nuevo, desde el pie de cada ficha del sitio. Nada se publica sin
que un editor lo apruebe. Qué campos se pueden proponer, cómo se validan y aplican:
`cerros/proposals.py`.

- **Revisar:** admin → "Propuestas" (filtro "Pendiente"). Cada propuesta muestra el valor actual,
  el propuesto y un campo editable "Se aplicará" para ajustarlo antes de aprobar, más la fuente y
  el comentario del colaborador. Avisa si la ficha cambió desde que se propuso y, en un cerro
  nuevo, si ya hay cerros con nombre parecido o a menos de 2 km. Botones: **Aprobar y aplicar**,
  **Pedir más información** (el mensaje es obligatorio; el colaborador la completa y la reenvía) y
  **Rechazar**. Tras cada una se abre la siguiente pendiente.
- El colaborador recibe un correo con el resultado (y el mensaje del editor) y ve sus propuestas
  en "Mi cuenta". Las aprobadas lo nombran al pie de la ficha ("Con aportes de: …", campo
  `contributors` en la API).
- Límites: 10 propuestas esperando revisión por persona y 20 por día.
- **Historial interno** ([django-simple-history](https://django-simple-history.readthedocs.io/)):
  cerros, rutas, ascensos, andinistas y grupos de montañas guardan cada cambio, hecho en el admin
  o por una propuesta (con el motivo "Propuesta #N de …"). Se ve con el botón "Historial" de
  cada ficha del admin, que también permite volver a una versión anterior. No es público.
- Al instalarlo por primera vez, `python manage.py populate_history --auto` guarda el estado
  actual de todas las fichas como punto de partida (sin eso, el historial empieza con el primer
  cambio).

## Ubicación según coordenadas

`python manage.py asignar_ubicacion` (con `--dry-run` primero) calcula para cada cerro su país y
región según sus coordenadas:

| Estado | Qué significa |
| --- | --- |
| Asignada por coordenadas | No tenía país/región, está a 2 km o más de cualquier límite y se le asignaron. |
| Por completar: cerca de un límite | No tiene país/región y está a menos de 2 km de un límite: no se asigna. Su ficha en el admin muestra la sugerencia, la distancia al límite y qué hay al otro lado. |
| No calza con las coordenadas | El país o la región cargados no coinciden con las coordenadas (cerca de un límite, cualquiera de los dos lados cuenta como correcto). Revisar coordenadas o datos. |
| Coincide con las coordenadas | Todo bien. |
| Revisada a mano | Lo marcó un editor (o cambió el país/región en el admin). El comando no la toca. |

- **Nunca cambia un país o región ya cargado**: solo completa los que faltan.
- Al guardar un cerro en el admin con coordenadas nuevas se recalcula solo. Al cambiar su país o
  región a mano queda "Revisada a mano".
- Acciones en la lista de cerros: "Usar país y región sugeridos", "Marcar ubicación como revisada"
  y "Recalcular ubicación según coordenadas".
- Si una región del mapa no existe en la base (o se llama distinto), no se asigna y la ficha lo
  dice: crea o renombra la región y vuelve a correr el comando.

**Mapas** (`cerros/geodata/limits.json.gz`, se regeneran con `cerros/geodata/build_limits.py`):
regiones de Chile y límite internacional de la Biblioteca del Congreso Nacional de Chile (BCN),
vía [geoBoundaries](https://www.geoboundaries.org/), licencia CC BY 3.0 IGO, precisos a unas
decenas de metros; provincias de Argentina, Bolivia y Perú de
[Natural Earth](https://www.naturalearthdata.com/) (dominio público), aproximadas (1 a 3 km),
por lo que sus límites internos llevan 3 km extra de margen.

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
