# Recuperación — volver al sistema ROS Noetic

> ## ✅ La imagen de respaldo EXISTE y está verificada
>
> **Fase 0.3 completada.** La imagen `dd` de la microSD con el sistema Ubuntu 20.04 + ROS
> Noetic se creó **y se verificó** antes de reflashear (confirmado el 2026-07-30). La **ruta
> A** de esta página es por tanto viable.
>
> El respaldo de ficheros (§0 y §3) se ejecutó el 2026-07-29; su contenido está en
> `~/respaldo_pre_migracion`, copiado fuera de la tarjeta.
>
> 👤 **Lo único que hace falta saber es dónde está guardada.** Anótalo abajo — una imagen
> que nadie encuentra no es un respaldo:
>
> | | |
> |---|---|
> | Fichero | `atriz_noetic_fallback.img` (o `.img.gz`) |
> | Copia 1 | *(anotar ruta / equipo)* |
> | Copia 2 | *(anotar — una copia única en el mismo PC desde el que se reflasheó no es un respaldo)* |
> | `sha256` | *(anotar, si se generó)* |
>
> Estado del resto de esta página: el procedimiento de **creación** (§1) se siguió con éxito;
> el de **restauración** (§2) sigue 📝 **NO VERIFICADO** — nadie ha restaurado la imagen
> todavía, y ojalá no haga falta.

Existen dos rutas de vuelta, de muy distinto coste.

| Ruta | Tiempo | Requiere | Estado |
|---|---|---|---|
| **A — Restaurar la imagen** | ~20 min | La imagen hecha antes de reflashear | ✅ **disponible** |
| **B — Rehacer desde el manual** | 3–5 h | Solo el manual original | siempre disponible |

**Haz la imagen.** Es la diferencia entre una tarde perdida y veinte minutos. Para los 16
robots de la flota, el equivalente es la **imagen dorada** — ver
[`FLOTA.md`](FLOTA.md).

---

## 0-bis. Rescate rápido: el arranque automático da problemas

**No hace falta reflashear nada por esto.** Desde el 2026-07-31 el robot levanta
`atriz-robot.service` al encender, y si ese servicio se porta mal —bucle de reinicio, pelea por
`/dev/rvr`, un `colcon build` a medias— la vuelta atrás es de un comando.

```bash
sudo systemctl disable --now atriz-robot     # para AHORA y no vuelve al reiniciar
```

🔴 **El SSH y la red NO dependen de este servicio.** Aunque el robot arranque en bucle, siempre
puedes entrar. Es a propósito: un servicio que se lleve por delante el acceso remoto convertiría
cada fallo en un viaje al edificio.

Para quitarlo del todo, incluidos los ficheros instalados:

```bash
sudo bash ~/atriz_migracion/scripts/fase_7_systemd.sh --quitar
```

Y para diagnosticar antes de rendirse:

```bash
systemctl status atriz-robot
journalctl -u atriz-robot -b --no-pager | tail -50
```

⚠️ **Un fallo que NO es un fallo:** si el robot arranca pero **no conduce**, casi seguro es que
el barrido del lidar está apagado a propósito y el `collision_monitor` bloquea el movimiento.
`atriz-escaneo on` y ya. Ver [RUNBOOK](RUNBOOK.md).

---

## 0. Preparar la Pi antes de apagarla

**Ejecuta esto primero, en la Raspberry Pi:**

```bash
bash ~/atriz_migracion/scripts/fase_0_3_respaldo.sh
```

Comprueba en los dos repositorios si queda algo sin commitear, **sin subir**, o en un
**stash** (los stashes no viajan a un remoto y desaparecen con la tarjeta), respalda las
claves SSH, el netplan y un inventario de paquetes en `~/respaldo_pre_migracion`, y hace
`sync`.

**Copia `~/respaldo_pre_migracion` a un USB o a tu PC.** No va a git: contiene claves
privadas y la PSK del WiFi.

Luego:
```bash
sudo poweroff
```

---

## 1. Crear la imagen de respaldo (Fase 0.3 — hacer ANTES de reflashear)

Con la Raspberry Pi **apagada** y la microSD en un PC.

### Linux / WSL

```bash
# Identificar el dispositivo — CUIDADO, verifica que es la SD y no tu disco
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,MODEL

sudo dd if=/dev/mmcblk0 of=atriz_noetic_fallback.img bs=4M status=progress conv=fsync
sha256sum atriz_noetic_fallback.img > atriz_noetic_fallback.img.sha256
gzip -6 atriz_noetic_fallback.img          # 29 GB → ~4-6 GB
```

Sustituye `/dev/mmcblk0` por el dispositivo real (puede ser `/dev/sdb`, `/dev/mmcblk0`…).
**Un `of=` equivocado destruye el disco de destino.** Verifica dos veces.

### Windows  ← camino por defecto de este proyecto

**Herramienta: Win32DiskImager** — <https://sourceforge.net/projects/win32diskimager/>

> ⚠️ **Rufus, balenaEtcher y Raspberry Pi Imager NO sirven.** Solo *escriben* tarjetas; no
> saben *leerlas* a un fichero. Para crear la imagen hace falta Win32DiskImager (o USB
> Image Tool).

**Requisito:** ~35 GB libres en el disco. La imagen ocupa 29 GB aunque la tarjeta esté a
medias, porque copia también el espacio vacío.

#### 🔴 Advertencia crítica

Al insertar la microSD, **Windows dirá «Necesita formatear el disco de la unidad X: antes de
poder usarlo»**.

**PULSA CANCELAR. NO FORMATEES.**

Windows no entiende ext4, así que asume que la tarjeta está corrupta y ofrece «arreglarla».
Si aceptas, **destruyes el sistema que intentas respaldar**. El aviso puede salir una o dos
veces (hay dos particiones); cancélalo siempre.

#### Pasos

1. `sudo poweroff` en la Pi, esperar a que se apaguen los LEDs, y sacar la microSD.
2. Insertarla en el PC. **Cancelar** el aviso de formatear.
3. **Clic derecho en Win32DiskImager → «Ejecutar como administrador».** Sin permisos de
   administrador no puede leer el dispositivo en crudo.
4. En **Device**: la letra de la microSD. Comprobar en «Este equipo» qué letra apareció al
   insertarla.
5. En **Image File**: icono de carpeta, y **escribir un nombre que no existe todavía**, p. ej.
   `D:\respaldos\atriz_noetic_fallback.img`. Es normal que no exista: lo crea el programa.
6. Pulsar **Read**.
   ⚠️ **NO «Write»** — haría lo contrario y borraría la tarjeta.
7. Esperar **6-10 minutos** para 29 GB.

#### Comprimir

**7-Zip**: clic derecho en el `.img` → *7-Zip* → *Añadir al archivo* → formato **gzip**.
Queda en **4-6 GB**.

#### Verificar en Windows

No se puede montar ext4 con facilidad, así que la comprobación práctica es:

| Comprobación | Qué esperar |
|---|---|
| Tamaño del `.img` | **~29-31 GB**. Si pesa unos MB, falló |
| Abrirlo con 7-Zip (*Abrir archivo*) | Deben verse **dos particiones** dentro |
| (Opcional, más a fondo) DiskInternals Linux Reader | Navegar hasta `/home/sphero/atriz_git` |

**Guardarla en dos sitios distintos.** Una única copia en el mismo PC desde el que se va a
reflashear no es un respaldo.

### Linux / WSL — verificación a fondo

Una imagen sin verificar no es un respaldo. En Linux se puede comprobar de verdad, montándola:

```bash
sudo losetup -Pf --show atriz_noetic_fallback.img     # devuelve /dev/loopN
lsblk /dev/loopN                                       # deben verse 2 particiones
sudo mkdir -p /mnt/chk && sudo mount /dev/loopNp2 /mnt/chk
ls /mnt/chk/home/sphero/atriz_git/src/Atriz_rvr        # debe existir
sudo umount /mnt/chk && sudo losetup -d /dev/loopN
```

### Dónde guardarla

**Dos sitios distintos.** Un disco externo y una nube, o dos discos. Una copia
única en el mismo PC desde el que se reflashea no es un respaldo.

---

## 2. Restaurar (ruta A)

```bash
gunzip -c atriz_noetic_fallback.img.gz | sudo dd of=/dev/mmcblk0 bs=4M status=progress conv=fsync
sync
```

Insertar la SD en la Pi y arrancar. El sistema vuelve **exactamente** al estado
del momento en que se hizo la imagen: ROS Noetic, el workspace `atriz_git`
compilado, la configuración WiFi y las claves SSH.

**Comprobaciones tras restaurar:**
```bash
lsb_release -a                    # Ubuntu 20.04.6
rosversion -d                     # noetic
ls ~/atriz_git/devel/setup.bash   # workspace compilado
ls -l /dev/ttyS0                  # puerto serie del RVR
roscore                           # arranca sin errores
```

---

## 3. Ficheros respaldados aparte

Ya guardados en este repositorio, por si la imagen fallara o se necesitara solo una parte:

| Ruta en el repo | Qué es |
|---|---|
| `04_respaldo/configs/boot_cmdline.txt` | `/boot/firmware/cmdline.txt` |
| `04_respaldo/configs/boot_config.txt` | `/boot/firmware/config.txt` |
| `04_respaldo/configs/boot_syscfg.txt` | `/boot/firmware/syscfg.txt` |
| `04_respaldo/configs/boot_usercfg.txt` | `/boot/firmware/usercfg.txt` (vacío) |
| `04_respaldo/configs/udev_50-serial.rules` | Regla udev del puerto serie |
| `04_respaldo/configs/home_bashrc` | `~/.bashrc` con los `source` de ROS |
| `04_respaldo/configs/etc_fstab` | `/etc/fstab` |
| `04_respaldo/sin_commitear/` | Los 6 ficheros de `Atriz_rvr` sin commitear |

**No respaldado deliberadamente:**
- `/etc/netplan/*.yaml` — contiene la PSK del WiFi. Ver [NETPLAN_OMITIDO.md](../04_respaldo/configs/NETPLAN_OMITIDO.md).
- `~/.ssh/` — claves privadas. Cópialas a mano a un medio seguro antes de reflashear.

El código del robot está en GitHub (`Bura-hub/Atriz_rvr`); lo único que no está
allí son esos 6 ficheros sueltos, ya respaldados aquí.

---

## 4. Rehacer desde cero (ruta B)

Si no hay imagen, el procedimiento completo está en
[`../02_manual/MANUAL_SPHERO_transcripcion.md`](../02_manual/MANUAL_SPHERO_transcripcion.md)
y en el `.docx` original con sus 40 capturas.

**Correcciones a aplicar sobre el manual** (los bloques `⚠️ AUDITORÍA` de la
transcripción las explican en detalle):

1. Los comandos de ejecución usan nombres de paquete **obsoletos**:
   ```bash
   # El manual dice:     rosrun sphero_rvr_hw Atriz_rvr_node.py
   # Lo correcto es:     rosrun atriz_rvr_driver Atriz_rvr_node.py
   ```
2. Añadir `dtoverlay=disable-bt` a `/boot/firmware/usercfg.txt` — el manual lo omite.
3. Instalar `ros-noetic-ros-base` en vez de `desktop-full`, y **no** instalar
   `ubuntu-desktop` ni `xrdp` salvo que se necesite el escritorio remoto.
4. `apt-key add` está obsoleto; usar `/usr/share/keyrings/` con `signed-by=`.
5. Rotar la contraseña del usuario `sphero`: la del manual está comprometida.

---

## 5. Qué se pierde al revertir

Al volver a Noetic se pierde todo lo construido en las fases 1–6: la instalación
de ROS 2 Jazzy, el driver portado a `rclpy`, el URDF, el driver del LIDAR, SLAM,
Nav2 y rosbridge.

**No se pierde la documentación** — vive en este repositorio, no en la tarjeta.
Eso incluye la auditoría, el plan y todo lo aprendido por el camino. Una segunda
intentona parte de mucho más arriba que la primera.
