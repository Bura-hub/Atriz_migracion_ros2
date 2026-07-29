# Ruta de instalación — de apagar el sistema actual a un robot funcionando

> **Este es el documento a seguir en orden.** Los capítulos del manual están numerados
> **por tema**, no por orden de ejecución, así que seguirlos del 0 al 12 no funciona: el
> capítulo 1 (UART) presupone un sistema ya instalado, que es el capítulo 3.
>
> Aquí está el orden real, con el documento y el script de cada paso.

**Si eres un agente:** lee primero [`CLAUDE.md`](CLAUDE.md) y [`TRASPASO.md`](TRASPASO.md),
y luego recorre esta ruta. Los pasos marcados 👤 los ejecuta la persona, no tú.

---

## Resumen de la ruta

```
  ETAPA A — Cerrar el sistema actual        ← estás aquí
     A1  Preparar la Pi                     scripts/fase_0_3_respaldo.sh
     A2  Apagar                          👤
     A3  Imagen dd de la microSD          👤 RECUPERACION.md §1
     A4  Verificar la imagen              👤 RECUPERACION.md §1

  ETAPA B — Instalar el sistema nuevo
     B1  Flashear Ubuntu Server 24.04     👤 manual, cap. 3.1-3.2
     B2  Editar cmdline.txt ANTES de arrancar  👤 manual, cap. 3.3   ⚠️ CRÍTICO
     B3  Configuración de arranque + UART     manual, cap. 3.4 y 1.2
     B4  Primer arranque y verificación       manual, cap. 3.5-3.6

  ETAPA C — Poner el sistema a punto
     C1  Higiene del SO                       scripts/fase_1_higiene_so.sh
     C2  Verificar contra la línea base       manual, cap. 4.3

  ETAPA D — GO / NO-GO
     D1  Clonar el código                     manual, cap. 5.1
     D2  Validar el SDK en Python 3.12        scripts/fase_1_validar_sdk_py312.py
         ├── GO     → sigue en E
         └── NO-GO  → PARA. Decisión de arquitectura

  ETAPA E — ROS 2 y el robot
     E1  Instalar ROS 2 Jazzy                 manual, cap. 5.2-5.5
     E2  Recuperar el estado actual           ver "Cómo volver a donde estábamos"
     E3  Verificar UART y telemetría          manual, cap. 1.3 y 2
     E4  Verificar el LIDAR                   manual, cap. 8.2

  ETAPA F — Seguir construyendo (sin escribir todavía)
     F1  Driver a rclpy                       plan, Fase 2
     F2  URDF y árbol TF                      plan, Fase 3
     F3  Driver ROS del LIDAR                 plan, Fase 3
     F4  SLAM y Nav2                          plan, Fase 4
     F5  Plataforma web                       plan, Fase 5
     F6  Clonar a los 16 robots               FLOTA.md
```

---

## ETAPA A — Cerrar el sistema actual

### A1 · Preparar la Pi

```bash
bash ~/atriz_migracion/scripts/fase_0_3_respaldo.sh
```

Comprueba que no queda nada sin commitear, **sin subir**, o en un **stash** — los stashes no
viajan a un remoto y desaparecen con la tarjeta. Respalda en `~/respaldo_pre_migracion`:
claves SSH, netplan (con la PSK del WiFi), `.bashrc`, ficheros sin trackear, un inventario de
paquetes, y el historial de Claude Code.

**Si el script marca ✗, resuélvelo antes de continuar.**

👤 **Copia `~/respaldo_pre_migracion` a un USB o a tu PC.** No va a git: contiene claves
privadas y la PSK del WiFi.

### A2 👤 · Apagar

```bash
sudo poweroff
```

### A3 👤 · Imagen de la microSD — **BLOQUEANTE**

Con la tarjeta en un PC. Procedimiento completo, con las variantes de Windows y Linux, en
**[`03_operacion/RECUPERACION.md`](03_operacion/RECUPERACION.md) §1**.

```bash
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,MODEL      # identifica el dispositivo
sudo dd if=/dev/mmcblk0 of=atriz_noetic_fallback.img bs=4M status=progress conv=fsync
sha256sum atriz_noetic_fallback.img > atriz_noetic_fallback.img.sha256
gzip -6 atriz_noetic_fallback.img
```

⚠️ **Un `of=` equivocado destruye el disco de destino.** Verifica dos veces.

**Guárdala en dos sitios distintos.** Una copia única en el mismo PC desde el que reflasheas
no es un respaldo.

### A4 👤 · Verificar la imagen

**Una imagen sin verificar no es un respaldo.** Procedimiento en `RECUPERACION.md` §1:
montarla con `losetup -Pf` y comprobar que se ven las dos particiones y que
`home/sphero/atriz_git/src/Atriz_rvr` existe dentro.

> **Qué estás respaldando:** no el sistema lento de esta mañana, sino uno donde el RVR va a
> 16.59 Hz sin perder un mensaje en 12 minutos y el LIDAR entrega el 100 % de sus tramas
> correctas. Si la migración se atasca, restaurar esto te devuelve a un punto bueno conocido.

---

## ETAPA B — Instalar el sistema nuevo

### B1 👤 · Flashear Ubuntu Server 24.04 LTS arm64

**Manual, capítulo 3.1–3.2.** Con Raspberry Pi Imager. **Server, no Desktop** — el escritorio
fue la causa nº1 de la lentitud del sistema anterior.

En «Editar ajustes»: usuario `sphero` con **contraseña nueva** (la anterior está comprometida),
hostname `rvr-01`, WiFi (preferir 5 GHz), y **activar SSH**.

### B2 👤 · Editar `cmdline.txt` ANTES del primer arranque — ⚠️ CRÍTICO

**Manual, capítulo 3.3.**

Con la tarjeta aún en el PC, monta la partición FAT y **quita `console=serial0,115200`** de
`cmdline.txt`. La imagen de Ubuntu lo trae por defecto y **reserva el UART para la consola**,
dejándolo inutilizable para el RVR.

Es el único acierto importante del manual original y hay que repetirlo en cada instalación.

### B3 · Configuración de arranque y UART

**Manual, capítulo 3.4** (qué ficheros existen en 24.04) **y capítulo 1.2** (el razonamiento
completo del UART).

En el fichero de configuración que corresponda:
```
dtoverlay=disable-bt
enable_uart=1
```

Y la regla udev de `/dev/rvr`. Lo automatiza:
```bash
sudo bash ~/atriz_migracion/scripts/fase_0_1_fix_uart.sh
sudo reboot
```

⚠️ **COMPROBAR:** en 20.04 la configuración iba en `usercfg.txt`; **en 24.04 puede ser un
único `config.txt`**. El script lo detecta, pero verifica el resultado.

### B4 · Primer arranque y verificación

**Manual, capítulo 3.5–3.6.**

```bash
lsb_release -a && uname -m && python3 --version
grep -o "console=[^ ]*" /boot/firmware/cmdline.txt      # solo console=tty1
ls -l /dev/rvr                                          # -> ttyAMA0
dmesg | grep -i ttyAMA                                  # "is a PL011 rev2"
```

---

## ETAPA C — Poner el sistema a punto

### C1 · Higiene del sistema operativo

**Manual, capítulo 4** (el por qué de cada medida, con la evidencia medida).

```bash
sudo bash ~/atriz_migracion/scripts/fase_1_higiene_so.sh
sudo reboot
```

### C2 · Verificar contra la línea base

**Manual, capítulo 4.3.** Compara con `00_auditoria/evidencia/` — el sistema *antes* de
optimizar:

| Métrica | Antes | Objetivo |
|---|---|---|
| `systemd-analyze` (userspace) | 29.5 s | **< 15 s** |
| `ps -e \| wc -l` | 273 tareas | **< 120** |
| CPU a 600 MHz | 59.6 % del tiempo | governor `performance` |
| `journalctl --disk-usage` | 784 MB | decenas de MB |
| `iw dev wlan0 get power_save` | on | **off** |

---

## ETAPA D — GO / NO-GO · el punto de decisión

**Manual, capítulo 5.1.** **No instales ROS 2 antes de esto.**

```bash
sudo apt install -y python3-pip python3-venv
pip install --break-system-packages pyserial pyserial-asyncio

mkdir -p ~/atriz_ws/src && cd ~/atriz_ws/src
git clone -b migracion-ros2 https://github.com/Bura-hub/Atriz_rvr.git

# Con el RVR ENCENDIDO:
python3 ~/atriz_migracion/scripts/fase_1_validar_sdk_py312.py
```

- **GO** → etapa E
- **NO-GO** → **PARA.** El script imprime las cuatro alternativas ordenadas por coste. Es una
  decisión de arquitectura, no algo a improvisar.

> El análisis estático fue muy favorable (0 patrones roubles en Python 3.12, un único
> `get_event_loop()` en la ruta usada), pero **análisis estático no es ejecución**.

---

## ETAPA E — ROS 2 y volver a donde estábamos

### E1 · Instalar ROS 2 Jazzy

**Manual, capítulo 5.2–5.5.** `ros-jazzy-ros-base`, **no** `desktop`.

⚠️ **COMPROBAR:** el método de las claves GPG cambia entre versiones. `apt-key add`, que
usaba el manual original, está obsoleto.

### E2 · Cómo volver a donde estábamos

El estado alcanzado el 2026-07-29 se reproduce con **cuatro cosas**, y todas están ya en los
repositorios:

| Qué | Dónde |
|---|---|
| `dtoverlay=disable-bt` + regla udev `/dev/rvr` | `scripts/fase_0_1_fix_uart.sh` |
| Código con `/dev/rvr` e `interval=60` | rama **`migracion-ros2`** de `Atriz_rvr` |
| Higiene del SO | `scripts/fase_1_higiene_so.sh` |
| Cómo verificar que funciona | manual, caps. 1.3, 2 y 8.2 |

> El código de `migracion-ros2` es **ROS 1 (catkin)**. En ROS 2 no compilará hasta el port del
> capítulo 6. En esta etapa solo interesa el **SDK**, que es Python puro.

### E3 · Verificar UART y telemetría

**Manual, capítulos 1.3 y 2.**

```bash
python3 ~/atriz_migracion/00_auditoria/evidencia/mediciones_banco/raw_uart.py
# esperado: "el RVR CONTESTA (46 bytes)"

python3 ~/atriz_migracion/00_auditoria/evidencia/mediciones_banco/sdk_full.py 60
# esperado: ~16.5 Hz en los 6 sensores de odometría
```

### E4 · Verificar el LIDAR

**Manual, capítulo 8.2.**

```bash
ls -l /dev/ttyUSB0
python3 ~/atriz_migracion/00_auditoria/evidencia/mediciones_banco/x2_parse.py
# esperado: 100 % de checksums válidos, ~2998 muestras/s
```

**Al llegar aquí has recuperado el estado del 2026-07-29, pero sobre ROS 2.**

---

## ETAPA F — Seguir construyendo

⏳ **No documentado todavía.** Los capítulos 6, 7 y 9–12 del manual se escriben al
ejecutarlos. El alcance previsto está en
[`01_plan/PLAN_MIGRACION_ROS2.md`](01_plan/PLAN_MIGRACION_ROS2.md), fases 2 a 6.

Orden y bloqueantes:

1. **Driver a `rclpy`** (plan, Fase 2) — incluye el **watchdog de `cmd_vel`**, que hoy no
   existe, y corregir las unidades a rad/s
2. **URDF + `robot_state_publisher`** (Fase 3) — **es el bloqueante raíz**: sin árbol TF
   conectado, SLAM es imposible
3. **Driver ROS del X2** (Fase 3) — `YDLidar-SDK` + `ydlidar_ros2_driver` rama `humble`
4. **SLAM y Nav2** (Fase 4)
5. **Plataforma web** (Fase 5) — al final. **Arreglar primero la parada de emergencia**, que
   está confirmada como no funcional
6. **Los 16 robots** ([`FLOTA.md`](03_operacion/FLOTA.md))

---

## Si algo va mal

| Situación | Dónde mirar |
|---|---|
| El robot no responde | [`RUNBOOK.md`](03_operacion/RUNBOOK.md) → «Cuando algo falla» |
| El LIDAR no aparece | `RUNBOOK.md` → «El LIDAR no aparece» |
| Hay que volver a Noetic | [`RECUPERACION.md`](03_operacion/RECUPERACION.md) §2 |
| No sé en qué punto estoy | [`TRASPASO.md`](TRASPASO.md) |
| ¿Por qué se decidió X? | [`ARQUITECTURA.md`](03_operacion/ARQUITECTURA.md) |

**Las tres trampas que más tiempo cuestan** (detalle en `CLAUDE.md`):

1. **Un robot dormido parece un cable roto.** Apaga y enciende el robot antes de tocar nada.
2. **Que el nodo arranque no prueba que el enlace funcione.** El check de firmware traga
   excepciones. Usa `raw_uart.py`.
3. **`uart0_pins` vacío tras `disable-bt` es normal**, no un fallo.

---

## Recordatorio final

**Los capítulos 3, 4 y 5 están 📝 NO VERIFICADOS**: se escribieron antes de ejecutarse en
24.04. Al recorrerlos, **corrige el manual en el mismo momento** y cambia su marca a ✅ con la
fecha. No en un mensaje de chat: en el repositorio.
