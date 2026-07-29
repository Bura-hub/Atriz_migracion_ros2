# Recuperación — volver al sistema ROS Noetic

> **Estado: PARCIALMENTE VERIFICADO.** El procedimiento de respaldo de ficheros
> (§3) se ejecutó el 2026-07-29. La imagen `dd` de la microSD (§1) **todavía no
> se ha creado** — es la Fase 0.3 del plan y es **bloqueante** antes de reflashear.

Existen dos rutas de vuelta, de muy distinto coste.

| Ruta | Tiempo | Requiere |
|---|---|---|
| **A — Restaurar la imagen** | ~20 min | Haber hecho la imagen antes de reflashear |
| **B — Rehacer desde el manual** | 3–5 h | Solo el manual original |

**Haz la imagen.** Es la diferencia entre una tarde perdida y veinte minutos.

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

### Windows

Win32DiskImager → botón **"Read"** → guardar como `.img`.

### Verificar la imagen

Una imagen sin verificar no es un respaldo:

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
