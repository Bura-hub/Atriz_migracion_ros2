# `scripts/sistema/` — los ficheros de sistema que el repositorio posee enteros

## Por qué existe este directorio

El 2026-08-03 se midió que `fase_7_systemd.sh` llevaba tres días sin ejecutarse:
`/usr/local/bin/atriz-robot.sh` instalado era viejo y **`atriz-nav.{sh,service}` no estaban
instalados**, mientras el `CHANGELOG.md` afirmaba que sí. Una imagen dorada hecha ese día habría
salido sin navegación, en los 16 robots. Evidencia: `00_auditoria/evidencia/63_alineacion_ANTES.txt`.

Lo que faltaba no era un fichero: era **poder comparar**. `atriz-robot.sh` se pudo detectar porque
el repo tiene el fichero y basta un `cmp`. Los ficheros que un script escribía con un heredoc no
tenían referencia contra la que compararse, así que su deriva era invisible por construcción.

Este directorio guarda esos ficheros. Y `MANIFIESTO.tsv` es la lista que leen a la vez los
instaladores y `verificar_robot.sh` sección 13.

## El criterio: A, B o C

Es sintáctico. Se decide mirando el código que escribe el fichero, no opinando sobre él.

### A — el repositorio tiene el FICHERO → va aquí, y va al manifiesto

Un heredoc con **delimitador entrecomillado** (`<<'EOF'`), que escribe un fichero **completo**,
**propio de Atriz** y **con el mismo contenido en los 16 robots**.

El fichero se **mueve** a este directorio y el heredoc **desaparece**; el script pasa a hacer
`install -m … "$SCRIPTS_DIR/sistema/…"`. No se duplica: se mueve. Si se dejara el heredoc y además
una copia aquí, habría dos fuentes de verdad y divergirían — que es exactamente el problema que este
directorio viene a resolver.

Detección de deriva: **`cmp`**.

| Fichero | Lo instala |
|---|---|
| `99-rvr.rules` | `fase_0_1_fix_uart.sh` |
| `cpu-performance.service` | `fase_1_higiene_so.sh` |

### B — el repositorio tiene el GENERADOR → NO va aquí

Un heredoc **sin comillas** (interpola estado de la máquina), o un `sed -i` / un append sobre un
fichero que pertenece a la distribución.

Nunca se versiona copia. Detección de deriva: **una aserción de efecto**, no un diff.

| Fichero | Por qué es B | Cómo se comprueba |
|---|---|---|
| `/etc/profile.d/atriz-robot.sh` | interpola el `ROBOT_ID`: **distinto en cada robot** | sección 12, contra `robot_id.txt` |
| `/etc/systemd/system/wifi-no-powersave.service` | interpola la interfaz y la ruta de `iw` **detectadas** | sección 4: `iw … power_save` |
| bloque de `/etc/systemd/journald.conf` | es un append a un fichero de la distro | sección 4: tamaño del journal |
| `noatime` en `/etc/fstab` | es un `sed -i` sobre un fichero de la distro | sección 4: `findmnt` |
| `/boot/firmware/cmdline.txt` | edición parcial | sección 12 |
| `/etc/netplan/60-atriz.yaml` | lo genera `first-boot.sh` desde `red.txt` | **y lleva la PSK del WiFi: jamás al repositorio** |

Versionar una copia de `wifi-no-powersave.service` sería el error que este criterio evita: la copia
diría `wlan0` para siempre, y en el primer robot cuya interfaz se llame `wlan1` sería falsa.

### C — es una ENTRADA del operador → solo el `.ejemplo`

`/boot/firmware/robot_id.txt` y `/boot/firmware/red.txt`. Se versiona la plantilla; el fichero real,
nunca. El de red lleva la PSK.

## Cómo añadir un fichero

1. Comprueba que es categoría A con el criterio de arriba.
2. Ponlo aquí y **borra el heredoc** del script que lo generaba, sustituyéndolo por `install`.
3. Añade la línea al `MANIFIESTO.tsv`.
4. **Antes de nada**, comprueba que lo que has extraído es byte a byte lo que hay instalado:
   ```
   cmp scripts/sistema/EL_FICHERO /ruta/del/sistema
   ```
   Si no coincide, **el fichero extraído está mal**. Se corrige el repositorio; no se reinstala nada
   sobre el sistema para «igualarlo».
5. `bash scripts/verificar_robot.sh` — la sección 13 debe cubrirlo ya, sin tocar el verificador.

## Lo que este directorio NO comprueba

`99-ydlidar.rules` nace en el otro repositorio (`Atriz_rvr/atriz_rvr_bringup/udev/`) y su
comprobación en `verificar_robot.sh:550` mira si existe `/dev/ydlidar`. Eso es **mejor** que un
`cmp`: la regla está anclada al `ID_PATH` del puerto USB de rvr-01, así que un fichero idéntico en
otro robot con el lidar en otro puerto no crea el enlace — y el `cmp` diría que todo está bien.
Es un recordatorio de que comparar ficheros nunca sustituye a comprobar el efecto.
