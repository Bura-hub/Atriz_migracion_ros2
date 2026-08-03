# El PC de desarrollo y el robot

Cómo trabaja una persona desde su PC contra `rvr-01`, qué canales hay, cuál sirve para qué, y —lo
más importante— **cómo se desmonta todo** cuando el robot pase a ser un robot de la flota.

> 🔴 **Claude Code en la Pi es herramienta de desarrollo del robot de referencia, no del producto.**
> Decisión del usuario, 2026-08-03. Nada de lo que se describe aquí puede quedar en los 16 robots, y
> nada duradero puede depender de que exista. **Lo que valga la pena conservar va al repositorio.**

---

## 1. Cómo se llega al robot, y por qué el SSH va por IPv6

`wlan0` tiene **tres direcciones IPv4 a la vez**, y eso es correcto: es el diseño de tres piezas que
permite mudar el robot de casa al laboratorio sin tocar un comando (`FLOTA.md`, manual cap. 19).

| Dirección | Qué es | ¿Alcanzable desde casa? |
|---|---|---|
| `10.14.7.7/21` | laboratorio, estática | **NO** — el gateway no responde |
| `192.168.1.200/24` | casa, estática | sí |
| `192.168.1.58/24` | casa, DHCP | sí, **pero puede cambiar** |
| `fe80::da3a:ddff:fed6:c1ee` | link-local IPv6 | sí, y **nunca cambia** |

### 🔴 mDNS publica las tres, y devuelve primero la muerta

Medido el 2026-08-03 con `mediciones_banco/probar_mdns.py`:

```
rvr-01.local   A=10.14.7.7,192.168.1.200,192.168.1.58   AAAA=fe80::da3a:ddff:fed6:c1ee
```

Y el orden **no es estable ni dentro de la misma máquina**: `getent hosts` devuelve la `fe80::`
primero, `getaddrinfo()` devuelve `10.14.7.7` primero. Un cliente que resuelva `rvr-01.local` puede
quedarse en el timeout TCP de una dirección que no lleva a ninguna parte.

**Por eso el canal de trabajo no usa mDNS.** mDNS es para la web, donde el usuario puede reintentar;
no para un canal automatizado.

### La link-local no es un apaño: es la dirección correcta

`fe80::da3a:ddff:fed6:c1ee` **sale del MAC de `wlan0`** (`d8:3a:dd:d6:c1:ee`) por EUI-64 —
comprobado. Consecuencias prácticas:

- **No cambia jamás.** No depende de DHCP ni de en qué red esté el robot.
- **Es la que ya usas**: los 12 accesos SSH del `auth.log` vienen de una link-local. Cuando notaste
  que «el SSH parece conectarse por IPv6», eso era exactamente lo que pasaba, y estaba bien.
- **No se enruta.** El canal es inalcanzable desde fuera del segmento de red *por construcción del
  protocolo* — no por una regla de cortafuegos, que aquí no existe (`ufw` dice `active` con
  `ENABLED=no`).
- **Escala a los 16 sin infraestructura**: las 16 direcciones salen por aritmética de la columna de
  MAC de `FLOTA.md`, sin DNS y sin DHCP.

### `~/.ssh/config` en el PC

```sshconfig
Host rvr-01
    HostName        fe80::da3a:ddff:fed6:c1ee%<TU_INTERFAZ>   # ← la interfaz DEL PC
    User            sphero
    IdentityFile    ~/.ssh/id_atriz
    IdentitiesOnly  yes
    BatchMode       yes          # sin esto, un canal automático se cuelga pidiendo contraseña
    ConnectTimeout  5
    ServerAliveInterval 15
    ControlMaster   auto
    ControlPath     ~/.ssh/cm-%r@%h:%p
    ControlPersist  10m

Host rvr-01-v4                   # respaldo si el PC cambia de interfaz
    HostName        192.168.1.200
    User            sphero
    IdentityFile    ~/.ssh/id_atriz
    IdentitiesOnly  yes
    BatchMode       yes
    ConnectTimeout  5
```

⚠️ `192.168.1.200` es la **estática**, no la del DHCP: `192.168.1.58` puede cambiar.

### Claves, que hoy no hay

`~/.ssh/authorized_keys` está **vacío**: entras con contraseña. Eso basta para trabajar a mano, pero
**ningún canal automático funciona con ello** — se cuelga esperando. Desde el PC, una sola vez:

```
ssh-keygen -t ed25519 -f ~/.ssh/id_atriz -C "pc→rvr-01"
ssh-copy-id -i ~/.ssh/id_atriz.pub sphero@192.168.1.200
```

Se comprueba **por efecto**, no porque el comando devuelva 0:

```
ssh rvr-01 'grep -c "Accepted publickey" /var/log/auth.log'   # antes
ssh -o BatchMode=yes rvr-01 true && echo "entra sin contraseña"
ssh rvr-01 'grep -c "Accepted publickey" /var/log/auth.log'   # debe haber subido
```

`verificar_robot.sh` sección 13 avisa mientras siga vacío.

---

## 2. Los tres canales

**No existe ningún mecanismo oficial para que dos instancias de Claude Code compartan contexto.** Ni
federación de sesiones, ni memoria compartida; `--resume` no cruza máquinas. Lo que hay son tres
canales para tres cosas distintas.

| Canal | Para qué | Huella en el robot |
|---|---|---|
| **Remote Control** | trabajo interactivo y **control del robot**, con un humano delante | ninguna |
| **El repositorio** | contexto: qué se ha hecho y por qué | ninguna (y es lo que sobrevive) |
| **Encargo por SSH** | pedirle al Claude de la Pi que mida, diagnostique e informe | ninguna |

### 2.1 Remote Control — el canal con humano delante

En la Pi, **dentro de `tmux`** para que sobreviva a que se caiga el SSH:

```
tmux new -A -s atriz -c ~/atriz_migracion
claude --remote-control
```

Se abre desde el navegador del PC en `claude.ai/code`.

- **Solo HTTPS saliente; nunca abre un puerto.** Esquiva las tres IP, el mDNS y la falta de
  cortafuegos. Medido: `api.anthropic.com:443` responde en 52 ms desde la Pi.
- 🔴 **Aquí es donde vive el control del robot, y a propósito.** Mover dos kilos de robot cerca de
  estudiantes es un acto con alguien mirando, no un encargo automatizado.
- ⚠️ Mientras está conectado, el transcripto se guarda en servidores de Anthropic. Research preview.

### 2.2 El repositorio — el contexto, y lo único que queda

Es el canal que ya funciona: **249 commits en 7 días, mediana de 8 minutos entre uno y otro**. No es
«a velocidad de commit» en el sentido malo.

Lo que hay que leer para situarse: `03_operacion/ESTADO_ACTUAL.md` primero (corto), y `CLAUDE.md`
solo si hace falta el detalle — son 107 KB ≈ 26.800 tokens.

### 2.3 El encargo por SSH — dos Claude hablándose

```bash
ssh rvr-01 bash -lc '
  cd /home/sphero &&
  timeout 900 ~/.local/bin/claude -p --resume "$ATRIZ_HILO" \
    --output-format json \
    --json-schema "$(cat ~/atriz_migracion/03_operacion/esquema_parte.json)" \
    --add-dir /home/sphero/atriz_migracion \
    --append-system-prompt "$(cat ~/atriz_migracion/03_operacion/CONTRATO_ENCARGO.md)" \
    --allowedTools Read Grep Glob \
        "Bash(ros2 topic hz:*)" "Bash(ros2 topic list:*)" "Bash(ros2 topic info:*)" \
        "Bash(timeout:*)" "Bash(printenv:*)" "Bash(cat /etc/machine-id)" "Bash(cat /proc/uptime)" \
        "Bash(git -C /home/sphero/atriz_migracion status:*)" \
        "Bash(git -C /home/sphero/atriz_migracion rev-parse:*)" \
        "Bash(systemctl is-active:*)" "Bash(systemctl status:*)" "Bash(ps:*)" \
    -- "Mide los Hz de /odom durante 10 s y devuelve el parte." < /dev/null
' | python3 -c "import json,sys; print(json.load(sys.stdin)['result'])" | jq -e '.hecho == true'
```

**Alcance: leer, medir, diagnosticar e informar. No mueve el robot** — eso es el canal 2.1.

Funciona: medido el 2026-08-03, devolvió `hecho: true` con `/odom` a **16,630 Hz** sobre 224
mensajes, `ros_domain_id: 1`, y los tres campos anti-alucinación cuadrando con la realidad. Coste:
**$0,95, 25 turnos, 176 s**. Evidencia: `00_auditoria/evidencia/66_canal_claude_encargo.txt`.

#### ⚠️ Cuatro detalles de sintaxis que cuestan un intento cada uno

Los cuatro se descubrieron ejecutándolo, y los cuatro fallan de forma distinta:

| | |
|---|---|
| `--json-schema` quiere **el JSON**, no una ruta | con una ruta: `Unrecognized token '/'` |
| el esquema **no puede llevar `$schema`** con `$ref` externo | `no schema with key or ref "https://json-schema.org/..."` |
| `--allowedTools` es **variádico** y se traga el prompt | `Input must be provided…` — hay que cerrar con `--` |
| falta `< /dev/null` | `Warning: no stdin data received in 3s` |

#### 🔴 Lista BLANCA, no lista negra

La primera versión usaba `--disallowedTools`, y el delegado **no pudo ejecutar nada**: en modo `-p`
no interactivo, todo lo que requiere aprobación se deniega. Devolvió `hecho: false` con el detalle
—que es el comportamiento correcto— pero el encargo no sirvió.

Con `--allowedTools` y una lista de comandos de solo lectura funciona, y además es el mismo patrón
que el proyecto ya adoptó para rosbridge: **enumerar lo permitido, no adivinar lo prohibido**.

#### 🔴 `bash -lc` no es opcional

```
ssh rvr-01 'comando'      →  ROS_DOMAIN_ID=VACÍO   ros2=AUSENTE
ssh rvr-01 bash -lc '…'   →  ROS_DOMAIN_ID=1       ros2=/opt/ros/jazzy/bin/ros2
```

Un `ssh host comando` **no lee `/etc/profile.d`**. Sin `-l`, el delegado arranca en el dominio DDS 0,
no ve **ningún** topic y concluye que el robot está muerto — sin un solo error. Es la misma trampa
que documenta la cabecera de `atriz-robot.sh`.

#### 🔴 `cd /home/sphero`, no `cd ~/atriz_migracion`

`~/.claude/projects/` contiene **un único ámbito, `-home-sphero`**. Arrancar desde otro directorio
crea un ámbito nuevo **vacío, sin memoria y sin avisar**. El `CLAUDE.md` se alcanza con `--add-dir`.

#### ✅ El hilo persistente, verificado

`--resume` no cruza máquinas, pero **no necesita cruzarla**: la sesión vive en la Pi y el PC la
direcciona por un UUID que él elige. Medido el 2026-08-03:

```
encargo 1  --session-id <uuid>              →  el modelo dice 7413
encargo 2  --resume <uuid>  (proceso nuevo) →  7413      ← lo recuerda
CONTROL    --session-id <uuid NUEVO>        →  NO_LO_SE  ← no lo sabe
```

📝 El hilo vive en `~/.claude/projects/-home-sphero/<uuid>.jsonl` y **es local a la Pi**: se pierde
entero al desinstalar Claude Code. Nada duradero puede depender de él.

#### 🔴 `claude -p` devuelve 0 cuando falla

Medido dos veces: `Not logged in` → salida **0**; `Session ID already in use` → salida **0**. Por eso
el veredicto es `jq -e` sobre el parte JSON, **nunca `$?`**.

#### ⚠️ No usar `--bare`

Con `--bare`: `Not logged in`, con las mismas credenciales válidas. Y además no cargaría `CLAUDE.md`,
así que el delegado perdería las reglas duras del proyecto.

---

## 3. Cómo se desmonta esto

**Es parte del diseño, no un apéndice.** Antes de que este robot pase a ser un robot de la flota:

1. **Comprobar que nada del contexto vive solo en la Pi.** Se pierden los hilos de `--resume`, los
   ficheros de `~/.claude/projects/-home-sphero/memory/` y los transcriptos. Lo que importe tiene que
   estar **commiteado** en el repositorio.
2. **`fase_6_preparar_imagen_dorada.sh` desinstala Claude Code**, pidiendo confirmación explícita:
   ```
   ~/.local/bin/claude   ~/.local/share/claude   ~/.claude   ~/.claude.json
   ```
3. 🔐 **Y borra las credenciales.** `~/.claude/.credentials.json` guarda
   `claudeAiOauth.accessToken` y `refreshToken` — los tokens de la suscripción. El modo `600` **no
   protege frente a un `dd`**: una imagen de disco lo copia todo, y los 16 clones saldrían con ellos.
   El control de credenciales de `fase_6` los busca desde el 2026-08-03; antes no.
4. **`verificar_robot.sh` lo comprueba** en la sección 13: un robot de la flota no debe tener Claude
   Code.

Peso que se recupera: **126 MB** de `~/.claude` (incluido el transcripto de la sesión de trabajo) más
**260 MB** de `~/.local/share/claude` = **386 MB por robot**.

---

## 4. Lo que este canal NO da

- **No hay memoria compartida entre las dos máquinas.** No existe, y ninguna de las opciones
  estudiadas la crea.
- **No hay datos en vivo ni teleoperación.** El encargo muestrea; no pilota. En modo `-p` las tareas
  de fondo se matan ~5 s tras el resultado. El flujo continuo es trabajo de **rosbridge**.
- **No es bidireccional.** El PC llama, la Pi contesta. La Pi no puede iniciar nada: haría falta
  abrir SSH en el PC y mantenerlo despierto.
- 📝 **NO VERIFICADO**: el encargo se probó **en la Pi**, no por SSH desde el PC. Falta repetirlo con
  `ssh rvr-01 bash -lc` cuando existan las claves.
