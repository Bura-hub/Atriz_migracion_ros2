# Arranque de la navegación — plan de implementación

> **Para quien lo ejecute:** implementa tarea por tarea, en orden. Los pasos usan casillas
> (`- [ ]`). **La tarea 4 es del usuario**: lleva `sudo` y reinicia el robot.

**Objetivo:** que navegar deje de exigir SSH y dos terminales, sin que Nav2 cueste batería cuando
nadie lo usa.

**Arquitectura:** una segunda unidad systemd, `atriz-nav.service`, **instalada pero no
habilitada**, con el mismo patrón que `atriz-robot.service`: un envoltorio en `/usr/local/bin/`
porque systemd no lee `~/.bashrc` —sin él no hay `ros2` en el `PATH` ni `ROS_DOMAIN_ID`, y los 16
robots acabarían en el dominio 0 viéndose entre sí—. Levanta `localizacion.launch.py` (AMCL) y
`nav2.launch.py`. Y un arreglo pequeño en `atriz.py` para que dos consumidores del barrido no se
pisen.

**Herramientas:** systemd, ROS 2 Jazzy, Nav2, `pytest` 7.4.4.

📎 **Diseño aprobado:** [`03_operacion/ARRANQUE_NAVEGACION.md`](../../03_operacion/ARRANQUE_NAVEGACION.md).
Si algo choca, manda el diseño.

🔴 **DOS REPOSITORIOS.** El envoltorio, la unidad y el instalador van en **`atriz_migracion`**
(`scripts/`, privado). `atriz.py` y el mapa van en **`Atriz_rvr`** (rama `ros2`, **público**).

---

## Restricciones globales

- **Sin secretos en el repositorio.** `Atriz_rvr` es **público**.
- **Nada se documenta sin ejecutarse.** Lo no ejecutado va marcado **NO VERIFICADO**.
- **Medir antes de atribuir.** Ningún número sin su fuente.
- **Comprueba el efecto, no el código de salida.**
- **Los pasos con `sudo` los ejecuta el usuario.** Prepáraselos como comando exacto.
- **Sin trailers de co-autoría** en los commits. Todo en **español**.
- 🔴 **Nunca `pkill -f`.** Mata por `comm` con `ps`.

---

## 🔴 Un hueco del diseño que este plan resuelve, y hay que saberlo

`localizacion.launch.py` exige el argumento `mapa` y **no tiene valor por defecto**:

```
DeclareLaunchArgument('mapa', description='Ruta al .yaml del mapa. OBLIGATORIO.')
```

Y **`atriz_rvr_bringup/maps/` no existe**. Los mapas que hay viven en
`00_auditoria/evidencia_24_04/mapas/` del repositorio **privado**, que no llega al robot.

**Suposición de este plan, explícita:** el mapa **viaja con el paquete**, en
`atriz_rvr_bringup/maps/aula.yaml`. Es lo correcto para una flota — así lo reparten `provision.sh`
y la imagen dorada, y los 16 robots comparten el mismo `map`, que es el argumento entero para usar
AMCL en vez de SLAM.

~~⏳ **Pero el mapa del aula no existe todavía**~~ ✅ **EXISTE DESDE EL 2026-08-19**: la arena
del laboratorio está mapeada (`~/mapas/arena.yaml`, ~3,95 × 4,00 m, origen anclado a una esquina
convenida). La tarea 1 sigue valiendo: la unidad **falla alto y claro** si el mapa no está, en vez
de arrancar un AMCL ciego.

🔴 **PERO LA SUPOSICIÓN DE ARRIBA NO SE ESTÁ CUMPLIENDO, y hay que decidirlo (👤).** Este plan
supone que el mapa **viaja dentro del paquete** (`atriz_rvr_bringup/maps/aula.yaml`), que es lo que
haría que `provision.sh` y la imagen dorada lo repartan a los 16. El mapa real **vive fuera**, en
`~/mapas/arena.yaml`, con `ATRIZ_MAPA` apuntando ahí — y `fase_6` **borra `~/mapas` y vacía
`ATRIZ_MAPA` a propósito**. Consecuencia medida por lectura, **no probada aún**: los 15 robots
restantes saldrían de la imagen **sin mapa**, y hoy no hay ningún mecanismo que se lo lleve.

✅ **DECIDIDO EL 2026-08-20 (👤 el usuario): opción A — el mapa entra en el paquete.**
`Atriz_rvr` commit `6c8697e`: `atriz_rvr_bringup/maps/aula.yaml` + `aula.pgm` son ahora la arena
del laboratorio. Así lo reparten `provision.sh` y la imagen dorada, y el **valor por defecto** del
supervisor y de `atriz-nav.sh` lo encuentra **sin tocar `ATRIZ_MAPA`**.

Se eligió sobre la alternativa —copiarlo a mano a los 16 tras la imagen— porque ese camino **no lo
comprueba nada**: un robot sin mapa arranca, parece sano y la web le habilita el botón.

⚠️ **El coste aceptado, y cómo se paga:** mete un artefacto **de un sitio concreto** en un repo
compartido, que es justo lo que `fase_6` evita para que nadie herede el mapa de otra aula. Se paga
con `maps/README.md`, que ahora **abre** diciendo que ese `aula.yaml` es la arena de Atriz y dando
los tres pasos para reemplazarlo en otra aula. Es una convención escrita, no un mecanismo: si otra
instalación clona este repo sin leerlo, hereda un mapa que no es suyo — y el fallo **no tiene
síntoma** (Nav2 dice «llegué» a medio metro).

---

## Estructura de ficheros

| Fichero | Repo | Responsabilidad |
|---|---|---|
| `scripts/atriz-nav.sh` | `atriz_migracion` | **Crear.** Envoltorio: entorno ROS, comprobar el mapa, `exec` del launch |
| `scripts/atriz-nav.service` | `atriz_migracion` | **Crear.** La unidad, sin habilitar |
| `scripts/fase_7_systemd.sh` | `atriz_migracion` | **Modificar.** Instalar los dos, y quitarlos con `--quitar` |
| `scripts/estudiantes/atriz.py` | `Atriz_rvr` | **Modificar.** Dejar el barrido como lo encontró |
| `scripts/pruebas/test_atriz_nucleo.py` | `atriz_migracion` | **Modificar.** Tests del punto anterior |
| `atriz_rvr_bringup/maps/` | `Atriz_rvr` | **Crear** (vacío, con `README`). Donde vivirá el mapa del aula |

---

## Tarea 1: el envoltorio y la unidad

**Ficheros:**
- Crear: `~/atriz_migracion/scripts/atriz-nav.sh`
- Crear: `~/atriz_migracion/scripts/atriz-nav.service`
- Crear: `~/atriz_ws/src/Atriz_rvr/atriz_rvr_bringup/maps/README.md`

**Interfaces:**
- Consume: `/usr/local/bin/atriz-escaneo` (ya instalado, acepta `on|off|estado`).
- Produce: `/usr/local/bin/atriz-nav.sh` y la unidad `atriz-nav.service`, que la tarea 2 instala.

- [ ] **Paso 1: el envoltorio**

Crea `~/atriz_migracion/scripts/atriz-nav.sh`:

```bash
#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# atriz-nav.sh — arranca la navegación (AMCL + Nav2) bajo systemd
# ═══════════════════════════════════════════════════════════════════════════════
# Lo ejecuta atriz-nav.service. Se instala con fase_7_systemd.sh. No lo copies
# a mano.
#
# POR QUÉ UN ENVOLTORIO Y NO UN ExecStart DIRECTO — el mismo motivo que
# atriz-robot.sh: systemd NO ejecuta un shell de login, así que no lee
# `~/.bashrc`. Un `ExecStart=ros2 launch ...` falla con «command not found», y
# con la ruta absoluta arrancaría SIN ROS_DOMAIN_ID: los 16 robots en el dominio
# 0, viéndose entre sí. Es la decisión D1 de ARQUITECTURA.md, y falla en
# silencio.
#
# 📝 NO VERIFICADO bajo systemd hasta que la tarea 4 lo arranque de verdad.
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

log() { echo "[atriz-nav] $*"; }

# 🔴 Los setup.bash de ROS NO son compatibles con `set -u`:
#    «AMENT_TRACE_SETUP_FILES: unbound variable» mata el script antes de hacer
#    nada, y el mensaje no menciona ROS. Es una trampa documentada del proyecto.
set +u
source /opt/ros/jazzy/setup.bash
source "$HOME/atriz_ws/install/setup.bash"
set -u

# ── El ROS_DOMAIN_ID, que es lo que aísla a cada robot ────────────────────────
if [[ -r /etc/profile.d/atriz-robot.sh ]]; then
    set +u; source /etc/profile.d/atriz-robot.sh; set -u
fi
log "ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-<sin definir>}"

# ── El mapa ──────────────────────────────────────────────────────────────────
# 🔴 FALLA ALTO SI NO ESTÁ. `localizacion.launch.py` exige `mapa` y no tiene
#    valor por defecto; sin mapa, AMCL no sabe dónde está el robot. Arrancar
#    igualmente daría un sistema que parece vivo y no puede navegar, que es la
#    firma de fallo que este proyecto lleva toda la migración documentando.
MAPA="${ATRIZ_MAPA:-$HOME/atriz_ws/src/Atriz_rvr/atriz_rvr_bringup/maps/aula.yaml}"
if [[ ! -r "$MAPA" ]]; then
    log "🔴 no hay mapa en $MAPA"
    log "   AMCL lo necesita y no tiene valor por defecto. Sin él la navegación"
    log "   arrancaría ciega. Genera uno con slam.launch.py y guárdalo ahí, o"
    log "   apunta a otro con la variable ATRIZ_MAPA."
    exit 1
fi
log "mapa: $MAPA"

# ── Arrancar ─────────────────────────────────────────────────────────────────
# 📝 Los dos launch en un solo `ros2 launch` no se puede: son ficheros
#    distintos. Se lanza localizacion en segundo plano y nav2 con `exec`, para
#    que nav2 herede el PID y los SIGINT le lleguen — si no, systemd vigila a
#    este script y el apagado limpio de Nav2 no corre.
log "arrancando localizacion.launch.py (AMCL)"
ros2 launch atriz_rvr_bringup localizacion.launch.py mapa:="$MAPA" &
AMCL_PID=$!

# Si AMCL muere, este script se lleva a Nav2 por delante: un Nav2 sin
# localización publica sobre un marco que nadie sostiene.
trap 'kill -INT "$AMCL_PID" 2>/dev/null || true' EXIT INT TERM

log "arrancando nav2.launch.py"
exec ros2 launch atriz_rvr_bringup nav2.launch.py
```

- [ ] **Paso 2: la unidad**

Crea `~/atriz_migracion/scripts/atriz-nav.service`:

```ini
# atriz-nav.service
#
# Levanta la NAVEGACIÓN: AMCL (localizacion.launch.py) + Nav2 (nav2.launch.py).
#
# 🔴 SE INSTALA PERO **NO SE HABILITA**. Tras un reinicio vuelve el driver y NO
#    vuelve la navegación — decisión del usuario, 2026-08-03. El bloque
#    [Install] existe para que `systemctl enable atriz-nav` funcione el día que
#    la web lo pida, que es todo el punto del diseño.
#
# Lo instala fase_7_systemd.sh. No copiarlo a mano.
#
# 📝 NO VERIFICADO — escrito el 2026-08-03, sin haberse arrancado nunca bajo
#    systemd. Lo verifica la tarea 4 del plan.

[Unit]
Description=Atriz — navegación (AMCL + Nav2)
Documentation=file:///home/sphero/atriz_migracion/03_operacion/ARRANQUE_NAVEGACION.md

# 🔴 BindsTo, no solo After. Si el driver se para, la navegación se para con él:
#    un Nav2 publicando sobre una odometría muerta es algo que parece vivo y no
#    lo está — lo mismo que `on_exit=Shutdown()` resolvió en robot.launch.py.
BindsTo=atriz-robot.service
After=atriz-robot.service

# 🔴 En [Unit], NO en [Service]: systemd los ignora ahí sin dar error.
StartLimitIntervalSec=300
StartLimitBurst=3

[Service]
Type=simple
User=sphero
Group=sphero
WorkingDirectory=/home/sphero

# ── El barrido, ANTES de arrancar ────────────────────────────────────────────
# 🔴 SIN `-`, a diferencia de atriz-robot.service. Ahí un fallo al apagar el
#    barrido es desgaste; aquí un fallo al ENCENDERLO deja la navegación ciega:
#    sin /scan el collision_monitor bloquea el movimiento (medido: 0.0 cm contra
#    9.9 del control) y el robot parece averiado. Si no se puede encender, la
#    unidad NO debe arrancar.
# 📝 `atriz-escaneo on` ya comprueba el EFECTO —espera a que /scan publique— y
#    devuelve error si no. No hace falta comprobarlo otra vez aquí.
ExecStartPre=/usr/local/bin/atriz-escaneo on

ExecStart=/usr/local/bin/atriz-nav.sh

# Al parar, devolver el barrido a su estado de reposo. Con `-`: si falla, no
# bloquea el apagado.
# ⚠️ Esto puede dejar sin /scan a un guion de alumno que esté corriendo en ese
#    momento. Se acepta porque parar la navegación es un acto explícito de
#    operador, no algo que ocurra solo. La dirección contraria —que el guion del
#    alumno deje ciega a la navegación— sí se arregla, en la tarea 3.
ExecStopPost=-/usr/local/bin/atriz-escaneo off

# Nav2 tarda en levantar sus nodos de ciclo de vida. ⏳ Cuánto exactamente es
# una de las cosas que la tarea 4 mide por primera vez.
TimeoutStartSec=120

# SIGINT para que los nodos de Nav2 ejecuten su apagado limpio.
KillSignal=SIGINT
KillMode=mixed
TimeoutStopSec=30

# ⚠️ on-failure, NO always. Con `always`, una salida limpia también reiniciaría,
#    y aquí una salida limpia significa «alguien lo paró». El límite de arriba
#    corta el bucle si Nav2 se cae una y otra vez.
Restart=on-failure
RestartSec=10

StandardOutput=journal
StandardError=journal
SyslogIdentifier=atriz-nav

[Install]
WantedBy=multi-user.target
```

- [ ] **Paso 3: el sitio del mapa**

Crea `~/atriz_ws/src/Atriz_rvr/atriz_rvr_bringup/maps/README.md`:

```markdown
# Mapas del aula

`atriz-nav.service` busca aquí **`aula.yaml`**, y **falla alto si no está**: AMCL lo necesita y
`localizacion.launch.py` no tiene valor por defecto para el argumento `mapa`.

El mapa vive **con el paquete** a propósito: así lo reparten `provision.sh` y la imagen dorada, y
los 16 robots comparten el mismo `map`. Ese marco compartido es el argumento entero para usar
AMCL en vez de SLAM — no la CPU, que en AMCL es **mayor** (8.8 % contra 4.8 %).

## Cómo se genera

```bash
ros2 launch atriz_rvr_bringup slam.launch.py     # y pasear el robot por el aula
ros2 run nav2_map_server map_saver_cli -f aula --ros-args -p save_map_timeout:=10.0
```

⚠️ `save_map` falla con `result=255` de forma **intermitente** (~1 de cada 3) por una carrera
entre `map_update_interval` y `save_map_timeout`. Por eso el `-p save_map_timeout:=10.0`.

⏳ **El mapa del aula NO existe todavía** (2026-08-03).
```

- [ ] **Paso 4: comprobar que son válidos, sin instalar nada**

```bash
cd ~/atriz_migracion
bash -n scripts/atriz-nav.sh && echo "sintaxis del envoltorio OK"
systemd-analyze verify scripts/atriz-nav.service 2>&1 | head -5
```

Esperado: sintaxis OK, y `systemd-analyze verify` **sin quejas**.
🔴 Este proyecto ya se comió que `StartLimitBurst` en `[Service]` se ignora **en silencio**, y que
solo lo dice `systemd-analyze verify` si lo ejecutas. Por eso este paso existe.

- [ ] **Paso 5: commit**

```bash
cd ~/atriz_migracion
git add scripts/atriz-nav.sh scripts/atriz-nav.service && git commit -m \
"atriz-nav.service: la unidad de navegacion, sin instalar todavia

Envoltorio con el mismo patron que atriz-robot.sh: systemd no lee .bashrc, asi
que sin el no hay ros2 en el PATH ni ROS_DOMAIN_ID — y los 16 robots acabarian
en el dominio 0.

Falla alto si no hay mapa: localizacion.launch.py lo exige y no tiene valor por
defecto. Arrancar sin el daria un AMCL ciego que parece vivo.

NO VERIFICADO bajo systemd."

cd ~/atriz_ws/src/Atriz_rvr
git add atriz_rvr_bringup/maps/README.md && git commit -m \
"maps/: donde vive el mapa del aula, que aun no existe

El mapa viaja con el paquete para que lo repartan provision.sh y la imagen
dorada, y los 16 robots compartan el mismo map."
```

---

## Tarea 2: instalarla con `fase_7_systemd.sh`

**Ficheros:**
- Modificar: `~/atriz_migracion/scripts/fase_7_systemd.sh`

**Interfaces:**
- Consume: `scripts/atriz-nav.sh` y `scripts/atriz-nav.service` de la tarea 1.
- Produce: `/usr/local/bin/atriz-nav.sh` y `/etc/systemd/system/atriz-nav.service`, instalados
  **sin `enable`**.

- [ ] **Paso 1: mira cómo instala lo que ya hay**

```bash
cd ~/atriz_migracion
grep -n "hacer install\|systemctl enable\|systemctl disable" scripts/fase_7_systemd.sh
```

Sigue **ese mismo patrón** —la función `hacer`, que respeta `--simular`—, no inventes otro.

- [ ] **Paso 2: añadir la instalación**

Junto a las líneas que instalan `atriz-robot.sh` y `atriz-escaneo`:

```bash
hacer install -m 755 "$SCRIPTS_DIR/atriz-nav.sh"     /usr/local/bin/atriz-nav.sh
hacer install -m 644 "$SCRIPTS_DIR/atriz-nav.service" /etc/systemd/system/atriz-nav.service
```

🔴 **Y NO añadas `systemctl enable atriz-nav`.** Es el punto entero del diseño: la unidad se
instala pero no arranca sola. Deja un comentario diciéndolo, para que nadie lo «arregle» después:

```bash
# 🔴 atriz-nav NO se habilita, a proposito. La navegacion cuesta ~58 % de un
#    nucleo y sale de la bateria del robot (la Pi se alimenta del USB del RVR),
#    y aun no se sabe si la web la necesitara siempre o a demanda. Se arranca a
#    mano con `systemctl start atriz-nav`; el dia que haga falta que arranque
#    sola, es un `systemctl enable`. Ver 03_operacion/ARRANQUE_NAVEGACION.md.
```

- [ ] **Paso 3: que `--quitar` también la quite**

Junto al `systemctl disable --now atriz-robot.service` que ya hay:

```bash
systemctl disable --now atriz-nav.service 2>/dev/null || true
rm -f /etc/systemd/system/atriz-nav.service /usr/local/bin/atriz-nav.sh
```

⚠️ **Comprueba el orden**: el `daemon-reload` que ya existe tiene que correr **después** de
borrar los dos ficheros, no entre medias.

- [ ] **Paso 4: comprobarlo en seco**

```bash
cd ~/atriz_migracion
bash -n scripts/fase_7_systemd.sh && echo "sintaxis OK"
sudo bash scripts/fase_7_systemd.sh --simular 2>&1 | grep -iE "atriz-nav|enable" 
```

Esperado: **las dos líneas de instalación de `atriz-nav`** y **ningún `enable atriz-nav`**.
🔴 Si aparece un `enable atriz-nav`, está mal: el diseño dice que no.

📝 `--simular` necesita `sudo` pero **no toca nada**: es el propio script quien lo exige.

- [ ] **Paso 5: commit**

```bash
cd ~/atriz_migracion
git add scripts/fase_7_systemd.sh && git commit -m \
"fase_7_systemd.sh: instala atriz-nav, y NO la habilita

Se instala como las demas, pero sin enable: la navegacion cuesta 58 % de un
nucleo sobre la bateria del robot y aun no se sabe si la web la necesitara
siempre. El dia que haga falta, es un systemctl enable.

--quitar tambien la retira."
```

---

## Tarea 3: que un guion de alumno no deje ciega la navegación

**Ficheros:**
- Modificar: `~/atriz_ws/src/Atriz_rvr/scripts/estudiantes/atriz.py`
- Modificar: `~/atriz_migracion/scripts/pruebas/test_atriz_nucleo.py`

**Interfaces:**
- Consume: `Robot._encender_barrido`, `Robot.cerrar`, `Robot._ultimo`.
- Produce: el atributo `Robot._barrido_era_mio: bool`, y la función pura
  `debe_apagar_barrido(lo_encendi: bool) -> bool`.

- [ ] **Paso 1: escribe los tests que fallan**

En `~/atriz_migracion/scripts/pruebas/test_atriz_nucleo.py`, junto a los demás:

```python
def test_no_apaga_el_barrido_si_ya_estaba_encendido():
    """🔴 Con la navegacion corriendo, un guion de alumno que apagara el
    barrido al cerrar dejaria a Nav2 CIEGO en silencio: sin /scan el
    collision_monitor bloquea y el robot parece averiado."""
    assert debe_apagar_barrido(lo_encendi=False) is False


def test_apaga_el_barrido_si_lo_encendio_el():
    """El caso normal: nadie mas lo usaba, asi que se deja como estaba."""
    assert debe_apagar_barrido(lo_encendi=True) is True
```

Y añade `debe_apagar_barrido` al `from atriz import (...)` de la cabecera.

- [ ] **Paso 2: ejecútalos para verlos fallar**

```bash
cd ~/atriz_migracion && source /opt/ros/jazzy/setup.bash
python3 -m pytest scripts/pruebas/test_atriz_nucleo.py -q -k barrido
```

Esperado: **error de importación**, `cannot import name 'debe_apagar_barrido'`.

- [ ] **Paso 3: la función pura**

En `atriz.py`, junto a las demás funciones puras:

```python
def debe_apagar_barrido(lo_encendi):
    """¿Hay que apagar el barrido al cerrar? Solo si lo encendimos nosotros.

    🔴 Dejar las cosas como las encontramos. Si al conectar ya llegaba `/scan`,
       es que otro lo tiene encendido —la navegacion, u otro programa— y
       apagarlo al salir lo dejaria CIEGO sin avisar. Sin `/scan` el
       collision_monitor bloquea el movimiento (medido: 0.0 cm contra 9.9 del
       control) y el robot parece averiado.
    """
    return bool(lo_encendi)
```

- [ ] **Paso 4: usarla**

En `_encender_barrido()`, antes de llamar a `/start_scan`, mirar si ya llegaba `/scan`:

```python
        # ¿Lo tenia encendido otro? Se mira ANTES de encenderlo nosotros.
        # Una espera corta basta: /scan va a ~10 Hz cuando esta activo.
        self._barrido_era_mio = True
        try:
            self._ultimo('_scan', timeout=1.0, que='/scan')
            self._barrido_era_mio = False
            print('AVISO: el barrido ya estaba encendido (¿navegacion en '
                  'marcha?). No lo apagare al cerrar.')
        except ErrorAtriz:
            pass                    # no llegaba: lo encendemos nosotros
```

Y en `cerrar()`, envolver la llamada a `/stop_scan`:

```python
            if debe_apagar_barrido(getattr(self, '_barrido_era_mio', True)):
                self._llamar(self._cli_parar_barrido, EmptySrv.Request(),
                             timeout=5.0, que='/stop_scan')
```

⚠️ El `getattr` con defecto no es adorno: `cerrar()` puede correr desde `atexit` o desde el
manejador de señales **antes** de que `__init__` haya llegado a fijar el atributo.

- [ ] **Paso 5: ejecuta los tests**

```bash
cd ~/atriz_migracion && source /opt/ros/jazzy/setup.bash
python3 -m pytest scripts/pruebas/ -q
python3 -m pyflakes /home/sphero/atriz_ws/src/Atriz_rvr/scripts/estudiantes/atriz.py
```

Esperado: **91 tests** (89 + 2) en verde y `pyflakes` limpio.

- [ ] **Paso 6: comprobar que el test PUEDE fallar**

🔴 En este plan ya han aparecido **cuatro** tests que decían proteger de un bug y no lo
detectaban. Rompe la función a propósito:

```bash
cd /home/sphero/atriz_ws/src/Atriz_rvr
sed -i 's/    return bool(lo_encendi)/    return True/' scripts/estudiantes/atriz.py
cd ~/atriz_migracion && python3 -m pytest scripts/pruebas/ -q -k barrido
git -C /home/sphero/atriz_ws/src/Atriz_rvr checkout -- scripts/estudiantes/atriz.py
git -C /home/sphero/atriz_ws/src/Atriz_rvr status --porcelain
```

Esperado: **1 failed** con el bug puesto, árbol limpio tras restaurar, y verde otra vez.

- [ ] **Paso 7: commit**

```bash
cd /home/sphero/atriz_ws/src/Atriz_rvr
git add scripts/estudiantes/atriz.py && git commit -m \
"atriz.py: deja el barrido como lo encontro

Con la navegacion corriendo, cerrar() apagaba el barrido y dejaba a Nav2 CIEGO
en silencio: sin /scan el collision_monitor bloquea (0.0 cm contra 9.9 del
control) y el robot parece averiado.

Ahora solo apaga lo que encendio el. Si al conectar ya llegaba /scan, avisa y lo
deja encendido al salir."

cd ~/atriz_migracion
git add scripts/pruebas/test_atriz_nucleo.py && git commit -m \
"Dos tests del barrido compartido, comprobados rompiendo la funcion"
```

---

## Tarea 4: verificación con el robot — **ES DEL USUARIO**

🔴 **Lleva `sudo` y reinicia el robot.** Prepárasela como comandos exactos y **no la ejecutes tú**.

**Ficheros:**
- Crear: `~/atriz_migracion/00_auditoria/evidencia/64_arranque_navegacion.txt`

⏳ **Requisito previo:** hace falta **un mapa válido**. Sin él la unidad falla alto a propósito
(tarea 1).

🔴 **Y ojo con la precisión, porque una versión anterior de este plan decía «el mapa del aula» y
era más restrictivo de lo que se sostiene:** lo que esta tarea verifica es el **mecanismo** —que
la unidad arranque, encienda el barrido sola, que `BindsTo` la tumbe con el driver, que un guion
de alumno no la deje ciega y que tras un reinicio no vuelva—. **Nada de eso depende de qué
habitación esté mapeada.**

→ Se puede cerrar **fuera del laboratorio** con un mapa cualquiera, apuntándolo con la variable
  `ATRIZ_MAPA` (que el envoltorio ya soporta) para no meter un mapa de pruebas en el paquete.
  Lo único que espera al aula es tener el `aula.yaml` de verdad, que es **contenido**, no
  mecanismo.

- [ ] **Paso 1: instalar**

```bash
cd ~/atriz_migracion
sudo bash scripts/fase_7_systemd.sh --simular | grep -i atriz-nav   # mirar antes
sudo bash scripts/fase_7_systemd.sh
systemctl is-enabled atriz-nav        # debe decir «disabled»
```

🔴 **`disabled` es el resultado correcto.** Si dice `enabled`, la tarea 2 está mal.

- [ ] **Paso 2: sin mapa, falla alto**

Antes de poner el mapa:

```bash
sudo systemctl start atriz-nav; echo "codigo: $?"
journalctl -u atriz-nav -n 10 --no-pager
```

Esperado: **falla**, y el journal dice `🔴 no hay mapa en …`. Es el comportamiento buscado: mejor
no arrancar que arrancar ciego.

- [ ] **Paso 3: con mapa, arranca y navega — y se cronometra**

Con `aula.yaml` en su sitio, y **el robot recién reiniciado** (barrido apagado por diseño):

```bash
time sudo systemctl start atriz-nav
source /opt/ros/jazzy/setup.bash
timeout 10 stdbuf -oL ros2 topic hz /scan | head -2      # el barrido se encendio SOLO
ros2 lifecycle get /amcl ; ros2 lifecycle get /bt_navigator
```

🔴 **Y el efecto que de verdad cuenta: mandar un objetivo y que el robot llegue.** Que la unidad
diga `active` no prueba nada — este proyecto lleva seis veces documentado que un código de salida
0 no prueba que algo hiciera algo.

⏳ **Apunta el tiempo de `time`**: es el dato NO MEDIDO que el diseño necesita para decidir algún
día si la navegación debe arrancar sola.

- [ ] **Paso 4: el conflicto del barrido, provocado**

Con `atriz-nav` corriendo:

```bash
cd ~/atriz_ws/src/Atriz_rvr/scripts/estudiantes
python3 01_avanzar.py                                    # avisa de que no lo apagara
timeout 10 stdbuf -oL ros2 topic hz /scan | head -2      # DEBE seguir publicando
```

🔴 **Es el conflicto 2 del diseño, y hay que provocarlo, no razonarlo.** Si `/scan` se queda
mudo, la tarea 3 no funciona.

- [ ] **Paso 5: el resto de las comprobaciones**

```bash
# restart no toca el driver
N=$(systemctl show atriz-robot -p NRestarts --value)
sudo systemctl restart atriz-nav
[ "$(systemctl show atriz-robot -p NRestarts --value)" = "$N" ] && echo "el driver no se entero ✅"

# BindsTo: parar el driver para la navegacion
sudo systemctl stop atriz-robot
systemctl is-active atriz-nav        # debe decir «inactive»
sudo systemctl start atriz-robot
```

- [ ] **Paso 6: tras un reinicio de verdad, la navegación NO vuelve**

```bash
sudo systemctl start atriz-nav && sudo reboot
# esperar ~60 s
systemctl is-active atriz-robot      # active
systemctl is-active atriz-nav        # inactive   <- lo que se busca
```

- [ ] **Paso 7: escribir la evidencia 64 y commitear**

Con la salida literal de todos los pasos, **el tiempo de arranque medido**, y lo que no se haya
podido comprobar marcado **NO VERIFICADO**.

---

## Tarea 5: cerrar

**Ficheros:**
- Modificar: `CLAUDE.md`, `TRASPASO.md`, `CHANGELOG.md`, `03_operacion/ARQUITECTURA.md`

- [ ] **Paso 1: quitar la contradicción de `ARQUITECTURA.md`**

Tiene anotado *«🔴 NADIE ARRANCA Nav2 NI AMCL […] ⏳ Decisión pendiente»*. Sustituirlo por la
decisión tomada, con enlace a `ARRANQUE_NAVEGACION.md`.

⚠️ **Busca TODAS las menciones, no la primera.** En este proyecto ya pasó corregir una cabecera y
dejar una subsección diciendo lo contrario.

- [ ] **Paso 2: `CLAUDE.md`**

En «Decisiones ya tomadas», una fila: la navegación va en `atriz-nav.service`, **instalada y no
habilitada**, y por qué. Y en las herramientas de la flota, la unidad nueva.

- [ ] **Paso 3: `TRASPASO.md` y `CHANGELOG.md`**

Estado y siguiente paso. Y lo que queda **NO VERIFICADO**: todo lo de la tarea 4 si no se ha
ejecutado, más el tiempo de arranque de Nav2 y el coste en batería de la CPU.

- [ ] **Paso 4: los verificadores**

```bash
cd ~/atriz_migracion && source /opt/ros/jazzy/setup.bash
python3 -m pytest scripts/pruebas/ -q
python3 scripts/auditar_documentacion.py
```

- [ ] **Paso 5: commit y push**

```bash
git -C ~/atriz_migracion fetch origin && echo "hay credenciales"
# commit y push en los dos repositorios
```

---

## Lo que este plan NO hace

- **No habilita la navegación al arranque.** Es el punto entero del diseño.
- **No genera el mapa del aula.** Sin él la tarea 4 no se puede cerrar, y hace falta estar en el
  laboratorio.
- **No mide el coste en batería** de tener Nav2 corriendo. Se anota **NO MEDIDO**.
- **No construye ningún disparador para la web**, que no existe.
- **No toca SLAM**, que sigue lanzándose a mano para mapear.
