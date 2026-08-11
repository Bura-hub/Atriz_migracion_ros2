# Gestión de la flota — 16 robots

> 🔴🔴 **ANTES DE CONSTRUIR LA IMAGEN DORADA, LEE ESTO.**
>
> 🔁 **ACTUALIZADO EL 2026-08-10: ya hay un segundo robot, y el guion se está ejecutando de
> verdad sobre él.** `rvr-02` existe, y `provision.sh` corre ahí sobre un Ubuntu limpio — sin
> tocar rvr-01. La suposición **se está levantando ahora mismo**, que es justo lo que faltaba.
>
> ⏳ **No ha terminado**, así que esta guía sigue sin poder darse por validada. Se quedó parado
> en `colcon build` con `Permission denied: 'log'`, y `fase_7_systemd.sh` se niega en cadena
> porque el workspace no compiló. Estado, diagnóstico y arreglo en
> [`ESTADO_ACTUAL.md`](ESTADO_ACTUAL.md).
>
> ✅ **Lo que ya está descartado:** que lo cause el guion. Compila con `sudo -u "$USUARIO"`
> (`provision.sh:519`) y crea el workspace con `install -d -o "$USUARIO"` (`:244`), así que un
> `~/atriz_ws` de `root` vendría de algo lanzado a mano con `sudo`. ⏳ **La causa real, sin
> determinar.**
>
> 📌 **Y la regla que hace que esto valga: lo que frene a rvr-02 va AL GUION**, no se arregla a
> mano. Si no, los catorce siguientes tropiezan con lo mismo.
>
> **Texto original, que sigue explicando por qué importa:** Lo verificado es sintaxis, una
> pasada con `--simular` y la comprobación de los binarios de Nav2. **De una pasada limpia no se
> ha probado nada de lo que instala o compila.**
>
> El riesgo no es que falle: es que falle **en el robot 7 de 16**, con seis ya desplegados.
> Detalle en `00_auditoria/evidencia_24_04/29_provision_sin_verificar.txt`.
>
> 🔴 **Y hay TRES bloqueantes más, auditados el 2026-08-01** (evidencia 38):
> 1. ✅ ~~**`~/.git-credentials` con el PAT viaja en la imagen.**~~ — **DECAE el 2026-08-11.**
>    👤 El usuario puso `Atriz_migracion_ros2` y `Atriz_rvr` en **público** a propósito, justo
>    para no tener que repartir un token personal en 16 microSD. **Medido ese día:** los dos
>    clonan sin credencial ninguna (`atriz-lab` sigue privado). Ya no hay PAT que filtrar.
>    🔴 Lo que **NO** arregla, y sigue abierto: las credenciales que ya están en el **historial**
>    de `Atriz_rvr` (PSK del WiFi y contraseña de `sphero`, `API_LABORATORIO.md` §«en público»).
>    Al ser público el repositorio, ese historial lo lee cualquiera. 👤 pendiente del usuario,
>    que lo tiene visto y lo abordará más adelante.
> 2. ✅ ~~rosbridge no está instalado~~ — **instalado el 2026-08-01**, va en `provision.sh` y lo
>    levanta `robot.launch.py`. Verificado desde un navegador. Texto original: y la web habla por ahí. Clonar antes de la Fase 5 significa
>    clonar dos veces.
> 3. ~~La imagen y `provision.sh` divergen~~ ✅ **RESUELTO 2026-08-01**: `provision.sh` instala el
>    arranque automático en su paso **8/9**. Ya no divergen.
>
> ⚠️ **CORRECCIÓN:** esta guía llegó a decir que «si se construye la imagen antes, los 16 saldrán
> sin arranque automático». **Es falso** — sí lo tendrían. El problema es la divergencia, no la
> ausencia.



> **Estado: DISEÑO. No implementado.** Se ejecuta en la Fase 6, después de tener **un**
> robot completamente funcional sobre ROS 2.
>
> Lo que sí es firme son las **restricciones descubiertas durante la Fase 0.1**, medidas
> sobre hardware real. Son el motivo de varias decisiones de este documento, y conviene
> leerlas antes de comprar nada.

---

## Restricciones descubiertas midiendo (no suposiciones)

### 1. 🔴 Los adaptadores USB del LIDAR no tienen serial único

Confirmado dos veces, en 20.04 y en 24.04, sobre la misma unidad:

```
$ udevadm info -q property -n /dev/ttyUSB0 | grep -E 'ID_SERIAL_SHORT|ID_PATH='
ID_SERIAL_SHORT=0001                                        ← genérico, inservible
ID_PATH=platform-fd500000.pcie-pci-0000:01:00.0-usb-0:1.2:1.0   ← el puerto físico, SÍ sirve
```

**Consecuencia:** si los 16 adaptadores reportan `0001`, **no se puede crear una regla udev
por número de serie**. Y sin regla, `/dev/ttyUSB0` no es determinista: con dos dispositivos
USB serie, el orden de enumeración depende del arranque.

**Tres salidas, en orden de preferencia:**

| Opción | Coste | Inconveniente |
|---|---|---|
| **a) Regla udev por ruta física del puerto** | 0 € | El lidar debe ir **siempre en el mismo puerto USB** de cada Pi. Documentar con foto |
| **b) Adaptadores FTDI con serial único** | ~5 €/robot | Hay que comprobar que expone **DTR** (el X2 alimenta el motor por ahí) |
| **c) Reprogramar el serial del CP2102** | 0 € | Requiere la herramienta de Silicon Labs y un paso manual por robot |

**Recomendación:** (a) para empezar, porque es gratis y funciona. Pasar a (b) si el
mantenimiento se vuelve molesto.

Para (a), la clave es **`ID_PATH`**, que sí identifica el puerto de forma única y estable.
Regla propuesta para `/etc/udev/rules.d/99-ydlidar.rules`:

```
# /dev/ydlidar -> el adaptador USB-serie conectado al puerto físico de SIEMPRE.
# No se puede usar el serial: los CP2102 genéricos reportan todos "0001".
# Obtén el ID_PATH de TU robot con:
#     udevadm info -q property -n /dev/ttyUSB0 | grep ID_PATH=
SUBSYSTEM=="tty", ENV{ID_VENDOR_ID}=="10c4", ENV{ID_MODEL_ID}=="ea60", \
  ENV{ID_PATH}=="platform-fd500000.pcie-pci-0000:01:00.0-usb-0:1.2:1.0", \
  SYMLINK+="ydlidar", MODE="0660", GROUP="dialout"
```

> ✅ **La regla está escrita, instalada y funcionando en rvr-01** (`/etc/udev/rules.d/99-ydlidar.rules`).
>
> ✅ **Y el `ID_PATH` SÍ es idéntico en otro Pi — CERRADO el 2026-08-11 con rvr-02.** Era la
> última incógnita grande antes de la imagen dorada. `provision.sh` lo comprobó solo, sobre el
> hardware, y lo dijo en su registro:
>
> ```
> ✓ regla udev de /dev/ydlidar instalada
> ✓ /dev/ydlidar existe: la regla CASA en este robot
> ```
>
> Confirmado en el robot: `/dev/ydlidar → ttyUSB0` y `/dev/rvr → ttyAMA0`. **La regla es
> clonable tal cual**: no hay que generarla en `first-boot.sh` ni tocarla robot por robot.
>
> ⚠️ Sigue vigente la condición que la hace funcionar: **el LIDAR va en el MISMO conector
> físico en los 16**. Lo que se ha demostrado es que ese conector da el mismo `ID_PATH` en
> otra placa, no que se pueda cambiar de puerto. Texto anterior, ya resuelto: *«⏳ NO
> VERIFICADO que el `ID_PATH` sea idéntico en otro robot … si no coincidiera, la regla no es
> clonable»*.

> 🔴 **DECISIÓN DEL USUARIO, 2026-08-04: el puerto fijo se mantiene, y el lidar va en el
> MISMO conector en los 16.** Se ofreció la alternativa —quitar el `ID_PATH` y casar solo por
> `10c4:ea60`, que en este robot es inequívoco porque **hay un único dispositivo USB-serie**
> (el RVR habla por `ttyAMA0`, el UART del SoC)—, y se descartó por coherencia con la imagen
> dorada: un robot idéntico a otro, sin variables por unidad.
>
> 👤 **Consecuencia directa: la FOTO del conector pasa de recomendable a OBLIGATORIA.** Es lo
> único que le dirá a quien monte el robot 7 dónde va el cable. **Sigue sin existir.**
>
> 🔴 **Por qué importa, medido el 2026-08-04:** con el lidar en el conector equivocado, el
> launch **muere en ~1 s sin imprimir una palabra** y el único error visible es
> «`/stop_scan` no respondió en 30s. ¿está corriendo robot.launch.py?», que manda a mirar el
> launch —donde no está el problema—. Costó cuatro intentos de cable.
> ✅ `verificar_robot.sh` ya lo dice ahora en una línea: «el LIDAR está en el PUERTO USB 1.4,
> y la regla udev espera el 1.2». Evidencia 69, apartados 7 y 8.
>
> 📝 Y el error que lo provocó, que es fácil de repetir: se movió el cable **buscando que
> volviera a ser `/dev/ttyUSB0`**. Ese número **no importa** —lo asigna el kernel por orden de
> aparición— y la regla existe justamente para hacerlo irrelevante: el nodo abre
> `/dev/ydlidar`. Lo que importa es el conector.

> **Verificar primero:** puede que los 16 adaptadores **no** sean todos `0001`. Enchufa dos
> y compara `udevadm info -q property -n /dev/ttyUSB0 | grep ID_SERIAL_SHORT` antes de
> decidir. (Usa `udevadm`, no `dmesg`: en 24.04 `dmesg` requiere `sudo`.)

### 2. El techo de la telemetría es el firmware del RVR, no la red ni el UART

Medido con las 8 corrientes de sensores activas:

| `interval` | `/odom` |
|---|---|
| 250 ms | 3.85 Hz |
| 100 ms | 9.94 Hz |
| **60 ms** | **16.59 Hz** ← usar este |
| 50 ms | **no arranca** |

El firmware cuantiza a múltiplos de 20 ms y **no baja de 60 ms**. 125 paquetes/s caben de
sobra en 115200 baud (~11.5 KB/s), así que el UART no es el límite.

**Para la flota:** 16.5 Hz por robot es el máximo. Presupuestar la red y el servidor con ese
número, no con aspiraciones.

### 3. Consumo por robot, medido

| Recurso | Solo el driver | **Stack completo** (driver+LIDAR+SLAM+Nav2) |
|---|---|---|
| CPU | **33.6 %** de un núcleo | **~89 %** de **un** núcleo de cuatro |
| RAM | 53 MB, plana | ~477 MB |
| Temperatura | — | **58.9–64 °C**, `throttled=0x0` |

✅ **Ya está medido con todo puesto**, que era lo que faltaba. **Nav2 cabe**: el stack entero
consume menos de un núcleo de los cuatro del Pi 4.

⚠️ **La cifra anterior, «29.5 % de CPU y 55–58 °C», era del sistema VIEJO** — Ubuntu 20.04 con
el nodo de ROS Noetic — y estaba presentada como referencia actual. Mezclar las dos líneas base
es un error que este proyecto prohíbe explícitamente.

### 4. ✅ El riesgo de red, MEDIDO (era el principal)

Esta Pi, con **un** robot y sin rosbridge, ya registra:

```
Signal level = -62 dBm      Tx excessive retries = 797  (en 42 min)
```

✅ **MEDIDO el 2026-08-01 — el payload.** Un robot con todo publicando:

| topic | Hz | bytes/msg | kB/s |
|---|---|---|---|
| `scan` | 11.4 | 2220 | **24.8** ← 59 % |
| `odom` | 16.6 | 724 | 11.7 |
| `imu` | 16.5 | 324 | 5.2 |
| resto | | | 0.5 |
| **total** | | | **42.2 kB/s = 0.33 Mbit/s** |

**×16 = 5.3 Mbit/s.** Eso cabe en cualquier AP.

✅ **Y el multiplicador de JSON, medido el mismo día** con rosbridge ya instalado:

| | binario | por rosbridge | factor |
|---|---|---|---|
| `/odom` | 724 B | 820 B | 1.13× |
| `/scan` | 2220 B | **5532 B** | **2.49×** |
| odom+scan | 36.5 kB/s | **75.0 kB/s** | **2.05×** |

🔴 Se había estimado **3–5×**; el real es **~2×**. Es la diferencia entre «hay que comprar red» y
«cabe»: **16 robots simultáneos = 9.4 Mbit/s**.

✅ **Replicado desde el navegador del PC** (cliente distinto, máquina distinta), con el
barrido encendido: **80.7 kB/s → 16 robots = 10.3 Mbit/s**. Un 7.6 % por encima de los 75.0
del robot, y la diferencia se explica entera: el X2 **gira libre** (11.86 Hz contra 11.45,
+3.6 %) y el JSON de un float ocupa según sus dígitos (5661 B contra 5532, +2.3 %). El caudal
**varía con el giro del lidar y con lo que ve**, así que para dimensionar la red se usa el alto.

📐 **Cifra de diseño: 81 kB/s por robot navegando · 10.3 Mbit/s los 16.**

---

### 🔴 ~~✅ Estática y DHCP conviven — verificado el 2026-08-01~~ · RETIRADO, ver más abajo

> ⚠️ **Lo que sigue se conserva tal cual y NO describe el estado actual.** La medición es
> correcta; la conclusión que se sacó de ella, no. La retractación va inmediatamente después.

Era **la suposición sobre la que se apoyaba todo el diseño de red**, y estaba sin probar:

```
$ ip -4 -br addr show wlan0
wlan0  UP  10.14.7.7/21  192.168.1.200/24  192.168.1.58/24
            ^laboratorio  ^casa             ^DHCP

$ ip route | head -1
default via 192.168.1.1 dev wlan0 proto dhcp     ← la ruta la pone el DHCP
```

Tres direcciones IPv4 a la vez, y la estática del laboratorio **no rompe la salida a internet
en casa** — que era el riesgo concreto de `RUTA_POR_DEFECTO`.

🔴 **Un robot se muda del laboratorio a casa, y al revés, sin tocar un solo comando.**

---

## 🔴🔴 RETIRADO EL 2026-08-04: la medición de arriba era correcta y la conclusión NO

Todo lo anterior se midió **desde el punto de vista del ROBOT** —¿puede tener las tres
direcciones a la vez?— y **nunca desde el del CLIENTE**. Con la web ya construida, el usuario
avisó de que «no funciona nada en flota». Medido en el navegador, con el robot encendido y sano:

```
ws://rvr-01.local:9090     🔴 12 s sin abrir, sin error y sin cierre
ws://10.14.7.7:9090        🔴 12 s igual   <- LA MISMA FIRMA
ws://192.168.1.200:9090    ✅ abre
```

`rvr-01.local` resuelve a **cuatro** direcciones, y el navegador prueba en un orden donde las dos
primeras —el `fe80::` sin zona y la estática del laboratorio— **no fallan: se cuelgan** ~21 s cada
una. **El muro del profesor no encontraba NINGÚN robot.**

🔴 **Para un cliente, desde cualquier red al menos una dirección del robot es un agujero negro.**
En el aula pasa lo mismo al revés, y allí funcionaba **por suerte**: `10.14.7.7` ordena antes que
las de casa.

⚠️ **Y el diagnóstico fácil engaña:** `ping rvr-01.local` responde en **1 ms** —elige el `fe80::`
con su zona— y `Resolve-DnsName` lista las cuatro sin quejarse. **Las dos herramientas daban verde
con el fallo presente.** Solo se ve abriendo un TCP desde el navegador.

→ **Lo sustituye: una dirección por red**, emparejada por SSID en `systemd-networkd`, con `DHCP=no`
y avahi sin publicar el `fe80::`. Diseño completo en
[`00_auditoria/planes/2026-08-04-direccionamiento-flota.md`](../00_auditoria/planes/2026-08-04-direccionamiento-flota.md).

📝 **La lección, que vale más que el arreglo: «verificado» tiene que decir PARA QUIÉN.** Esta
decisión llevaba tres días con un ✅ y no era falsa — era incompleta, y por eso nadie volvió a
mirarla.

✅ **El riesgo nº4 queda cerrado.** Y aparece la palanca: `/scan` es el **83 %** del tráfico por
rosbridge. **Sin él, los 16 caben en 1.6 Mbit/s.**

**Las tres palancas, por orden:**
1. **¿Cuántos robots a la vez?** No es una pregunta técnica y es la que más cambia el resultado.
2. **`scan` es el 59 %.** Si la web no lo necesita crudo —le basta `/map` + la pose— un robot baja
   a **17.4 kB/s** y los 16 a 2.2 Mbit/s. La decisión de diseño más barata que queda.
   ⚠️ **Esas dos cifras son BINARIAS (DDS).** Por rosbridge, que es como habla la web, el
   mismo robot sin `/scan` son **13.6 kB/s** y los 16 **1.7 Mbit/s**. No mezclar las dos
   codificaciones: el JSON multiplica por ~2, y por 2.5 en `/scan`.
3. **La banda.** 2.4 GHz → 5 GHz cambia el problema.

✅ **El multiplicador JSON, medido** el 2026-08-01: **~2×**, no el 3–5× estimado. Un robot
navegando son **80.7 kB/s** → **10.3 Mbit/s** los 16. Evidencia 39.

---

## ~~✅ El diseño de red, verificado (2026-08-01)~~ — 🔴 SUSTITUIDO EL 2026-08-04

> 🔴 **Esta sección describe el diseño ANTERIOR y se conserva como registro.** Lo que hay hoy es
> **una dirección por red**, emparejada por SSID — ver la retractación de más arriba y la
> evidencia 74.
>
> **Lo medido seguía siendo cierto** (las tres direcciones convivían y el robot se mudaba sin
> tocar un comando); lo que estaba mal era darlo por bueno **mirándolo solo desde el robot**.
> Desde un cliente, tres direcciones significan que **al menos una es un agujero negro**, y el
> navegador se cuelga en ella sin dar error: el muro no encontraba ningún robot. Evidencia 75.

`wlan0` con **tres direcciones IPv4 a la vez**, y la ruta por defecto puesta por el DHCP:

```
wlan0  UP  10.14.7.7/21  192.168.1.200/24  192.168.1.58/24
            ^laboratorio  ^casa             ^DHCP
default via 192.168.1.1 dev wlan0 proto dhcp
```

Era la suposición marcada **«A VERIFICAR»** que sostenía todo lo demás: si estática y DHCP no
convivían, el diseño había que rehacerlo. Conviven. **Este robot se lleva al laboratorio sin
tocar un solo comando.**

Cómo se aplica, y por qué en dos pasos:

```bash
sudo bash scripts/first-boot.sh --solo-red   # genera y valida. NO aplica.
sudo netplan try --timeout 90                # aplica, y revierte solo si te deja sin SSH
```

🔴 **Y un fallo de seguridad que encontró el verificador:** `chmod 600` sobre `/boot/firmware`
**no hace nada** — es FAT, no guarda permisos de Unix, y devuelve 0 igualmente. La PSK del WiFi
queda legible por cualquier usuario, en los 16 robots. Se cierra en `/etc/fstab` con
`fmask=0177,dmask=0077`. Manual, cap. 19.3b.

## Asignación por robot

> ✅ **Sin columna `Namespace`** — decisión cerrada el 2026-08-01: los topics son `/odom`, no
> `/rvr_01/odom`. Y la IP **ya no es una reserva DHCP**: es estática, generada desde
> `/boot/firmware/red.txt`. Manual, cap. 19.

| Robot | Hostname | `ROS_DOMAIN_ID` | IP laboratorio (estática) | IP casa | MAC |
|---|---|---|---|---|---|
| 01 | `rvr-01` | 1 | `10.14.7.7/21` | `192.168.1.200/24` | `d8:3a:dd:d6:c1:ee` (wlan0) · `d8:3a:dd:d6:c1:ea` (eth0) |
| 02 | `rvr-02` | 2 | | | |
| … | … | … | | | |
| 16 | `rvr-16` | 16 | | | |

**Rellenar esta tabla a medida que se despliega cada robot.** Es el inventario, y sin él no
se puede diagnosticar nada a distancia.

🔴 **CORREGIDO EL 2026-08-04.** Aquí decía que no hacía falta reserva DHCP porque `rvr-01` tiene
«tres direcciones a la vez y responde a `rvr-01.local` por mDNS, verificado desde el PC». **Las
tres direcciones son justamente el problema**: el nombre resuelve a cuatro y el navegador se
cuelga en las que no sirven. Ver la retractación de arriba.

✅ **Lo que sigue siendo cierto:** no hace falta reserva DHCP —y además no se puede, las
direcciones del laboratorio **las asigna el administrador de red**, una por robot—, la IP se edita
metiendo la microSD en cualquier PC, y el robot se muda sin tocar un comando. **Lo que cambia es
que ahora lleva UNA dirección, la del sitio donde esté**, en vez de todas a la vez.

⚠️ **`LAB_BASE`/`LAB_OCTETO` quedan OBSOLETOS.** El esquema derivado daba `10.14.7.101` al robot
01 y su dirección real es `10.14.7.7`: **el robot de referencia no seguía su propio esquema**, y
eso se heredaba a la imagen dorada. `LAB_IP` pasa a ser obligatoria y `first-boot.sh` avisa a
gritos si alguien usa la derivada.

**Por qué un dominio DDS por robot** y no namespaces en un dominio común: ver
[ARQUITECTURA.md](ARQUITECTURA.md), Decisión 1. Resumen: ~160 participantes DDS sobre WiFi
saturan la red solo con el descubrimiento.

### Red: IP estática **desde la partición FAT**, no reservas DHCP

> 🔴 **CORREGIDO el 2026-08-01.** Aquí ponía «reservas DHCP por MAC, **no** IPs estáticas — un
> cambio de subred se hace en un sitio en vez de en dieciséis». El argumento era flojo y llevaba
> a la decisión equivocada.

**El argumento fuerte contra las estáticas es otro:** una IP equivocada deja el robot **sin
dirección en esa LAN y sin SSH para arreglarla**. Te quedas fuera. Y con imagen dorada, los 16
clones nacerían con la misma IP.

✅ **Las dos objeciones desaparecen si la configuración vive en la partición FAT**
(`/boot/firmware/red.txt`), que se edita metiendo la microSD en cualquier PC **sin arrancar la
Pi**. Es el mismo mecanismo que ya usa `robot_id.txt`.

Y así **no dependes del administrador de la red**: puedes entrar al aula con 16 robots y un AP sin
DHCP, y funcionan. En una red universitaria gestionada por un tercero, eso es la diferencia entre
trabajar y esperar.

**Cómo queda:** `first-boot` genera un netplan con **los dos puntos de acceso** (casa y
laboratorio tienen SSID distintos) y **las dos direcciones estáticas más DHCP**. En cada sitio
funciona la que toca. **Cero toques al mudarse.** Manual, cap. 19.

⚠️ **La ruta por defecto NO se duplica.** Una ruta hacia un gateway que no existe en la red actual
rompe el tráfico de salida en silencio, porque tener la dirección configurada lo hace «on-link».
Por eso `red.txt` tiene `RUTA_POR_DEFECTO`, y por defecto la deja al DHCP.

**Y mDNS como red de seguridad:** cada robot responde a `rvr-NN.local` en cualquier red. Si una
estática está mal, sigues llegando al robot. Evidencia 39.

---

## Cómo NO repetir el proceso 16 veces

**El trabajo se hace UNA vez.** Perfeccionas un robot, conviertes su tarjeta en imagen, y
cada robot nuevo cuesta **~3 minutos atendidos**.

### Las cuatro herramientas

Escritas el 2026-07-30, después de instalar `rvr-01` a mano y descubrir que el proceso tiene
más trampas de las que caben en una lista de pasos.

| Script | Dónde corre | Qué hace |
|---|---|---|
| **`provision.sh`** | en el robot | De un 24.04 recién instalado a robot terminado. Idempotente. **Es la fuente de verdad**: la imagen dorada se construye ejecutándolo |
| 🔴 **`preparar_tarjeta.sh`** | en el **PC** (Linux/WSL) | **OBLIGATORIO antes del primer arranque**, no es comodidad: `cmdline.txt` (si no, el UART queda para la consola y **el RVR no habla**), `config.txt` bajo `[all]`, y `robot_id.txt` — que **`provision.sh` necesita**. 🔴 `provision.sh` **no toca `cmdline.txt`** |
| **`verificar_robot.sh`** | en el robot | **105 aserciones** con `--hardware` (102 sin él). Sale con código ≠ 0 si algo falla. **Es quien decide si un robot está listo** |
| **`fase_6_preparar_imagen_dorada.sh`** | en el robot de referencia | Le quita la identidad para poder clonarlo |

### Por qué imagen dorada y no aprovisionar 15 robots por red

Es una decisión de **ancho de banda**, no de comodidad. Y esta vez con cifras medidas, no
estimadas.

**Medido el 2026-07-30 aprovisionando `rvr-01`:**

| Paso | Descarga | En disco |
|---|---|---|
| `ros-jazzy-ros-base` + `ros-dev-tools` | **157 MB** (509 paquetes) | 703 MB |
| `apt full-upgrade` inicial + kernel nuevo | ~120 MB | — |
| `iw`, `python3-pip`, `python3-aiohttp`, `pyserial-asyncio` | ~2.5 MB | ~11 MB |
| Las 46 actualizaciones pendientes de `noble-updates` | pendiente de medir | — |

**Del orden de 300 MB de descarga por robot**, y eso *antes* de compilar el workspace o de
instalar el driver del LIDAR y Nav2, que vendrán después.

> ⚠️ Una versión anterior de este documento decía «~1.5 GB por robot». Era una **estimación
> presentada como dato**, y estaba inflada unas cinco veces. Corregido el 2026-07-30 con las
> cifras reales de `apt`. La conclusión no cambia, pero el número sí: **mide antes de
> afirmar.**

Con 15 robots eso es del orden de **4-5 GB sobre la única AP del laboratorio**, que es justo el
[riesgo nº4 de esta página](#4--el-riesgo-de-red-sigue-sin-medir-y-es-el-principal) — el que
sigue sin medir y el más probable. Con imagen dorada son **0 GB de red**: se escriben por SD
desde el PC.

Y hay un segundo argumento, más fuerte que el ancho de banda: **el tiempo**. En el Pi 4, esos
509 paquetes tardan del orden de 15-20 minutos en desempaquetarse e instalarse. Por 15 robots
son varias horas de espera; grabar una imagen son ~8 minutos desatendidos por tarjeta, y se
pueden grabar varias en paralelo con varios lectores USB.

**Pero una imagen que nadie sabe reconstruir es una caja negra**, y ese es exactamente el
problema del `MANUAL SPHERO.docx` original: describía un sistema que nadie podía rehacer. De
ahí la relación entre las dos piezas:

```
   provision.sh ──(una vez, en el robot de referencia)──►  robot terminado
                                                                  │
                                            fase_6_preparar_imagen_dorada.sh
                                                                  │
                                                                  ▼
                                                          IMAGEN DORADA
                                                                  │
                                          preparar_tarjeta.sh --id NN
                                                                  │
                                                                  ▼
                                                      robots 02 … 16
```

**La imagen es el atajo. El script es la verdad.** Si divergen, gana el script: se
reconstruye la imagen. Y como `provision.sh` es idempotente, sirve además para **actualizar**
un robot ya en marcha (`git pull && sudo bash provision.sh`), que es lo que evita la deriva
de configuración — lo que mata las flotas.

### Lo que se hace una sola vez

```bash
# En el robot de referencia, cuando pasa verificar_robot.sh --hardware SIN FALLOS
# y ha superado la verificación de extremo a extremo del plan:
sudo bash ~/atriz_migracion/scripts/fase_6_preparar_imagen_dorada.sh
sudo poweroff       # NO volver a arrancar esta tarjeta antes del dd

# Desde un PC, con la tarjeta fuera:
sudo dd if=/dev/mmcblk0 of=atriz_jazzy_v1.img bs=4M status=progress conv=fsync
sha256sum atriz_jazzy_v1.img > atriz_jazzy_v1.img.sha256
sudo pishrink.sh -Z atriz_jazzy_v1.img     # reduce al tamaño usado: 29 GB -> ~4-6 GB

# Y etiqueta el código, para saber qué corre cada robot:
git tag -a v1.0-jazzy -m "Primera imagen dorada validada" && git push origin v1.0-jazzy
```

🔴 **La imagen dorada contiene la PSK del WiFi** (en `/etc/netplan/50-cloud-init.yaml`) y la
contraseña del usuario `sphero`. Es lo deseable —así los 16 robots entran solos en la red—
pero significa que **la imagen es material sensible**: no sale del laboratorio, no va a git,
y no se comparte por servicios en la nube.

### Lo que se hace por robot

| Paso | Tiempo | ¿Atendido? |
|---|---|---|
| 1. Grabar la imagen en la microSD | ~8 min | no |
| 2. `sudo bash preparar_tarjeta.sh --id NN` (en el PC) | ~15 s | **sí** |
| 3. Escribir `red.txt` en la partición FAT (IP del robot) | ~1 min | **sí** |
| 4. Arrancar — `atriz-first-boot` hace el resto | ~2 min | no |
| 5. `bash verificar_robot.sh --hardware` | ~1 min | **sí** |
| 6. Rellenar la fila de la tabla de asignación | ~15 s | **sí** |

**Total atendido: unos 3 minutos por robot.** Los 16 caben en una tarde, y con **varios
lectores de tarjetas USB** se graban tres o cuatro en paralelo mientras se verifican las
anteriores.

El paso 2 sustituye a lo que antes era «editar `robot_id.txt` con el Bloc de notas». Sigue
siendo posible hacerlo a mano —la partición es FAT y se abre desde cualquier PC— pero el
script comprueba además que `cmdline.txt` y `config.txt` están bien, y esos dos **fallan en
silencio**: un `[all]` olvidado no da ningún error, el robot simplemente no habla con el RVR.

Si en lugar de la imagen dorada partes de una **instalación limpia** de Ubuntu Server, el
paso 4 pasa a ser `sudo bash provision.sh` y sube a ~25 minutos, casi todos desatendidos.

📝 **`provision.sh` deja el robot COMPLETO**: sus **9 pasos** (0/9 … 9/9) incluyen ya la
Etapa F (xacro, `slam_toolbox`, `YDLidar-SDK` compilado desde fuentes, `ydlidar_ros2_driver`,
la regla udev de `/dev/ydlidar` y `colcon build`). Antes se quedaba en «ROS 2 instalado y el
código clonado», que no arranca.

🔴 **Y clonaba la rama equivocada** (`migracion-ros2`, la vieja con código de ROS 1, que no
compila con colcon). Corregido a **`ros2`**. Si reconstruyes la imagen dorada desde un
`provision.sh` anterior a esa fecha, el robot no funcionará.

### Por qué hace falta el paso de «preparar»

Clonar una tarjeta tal cual produce 16 robots con la **misma identidad**, y eso rompe cosas
de formas confusas:

| Duplicado | Qué provoca |
|---|---|
| `machine-id` | El DHCP puede dar la **misma IP a dos robots** |
| Claves SSH de host | `REMOTE HOST IDENTIFICATION HAS CHANGED` al saltar de robot a robot — y ningún aviso real si algún día hay un intruso |
| `hostname` | Imposible saber a qué robot estás conectado |
| `ROS_DOMAIN_ID` | **Los robots se ven entre sí en DDS.** Es exactamente lo que la Decisión 1 evita |

`fase_6_preparar_imagen_dorada.sh` borra todo eso e instala
**`atriz-first-boot.service`**, que lo regenera en el primer arranque leyendo
`robot_id.txt`.

Detalles del servicio que importan:

- Corre **antes de `network-pre.target`**: el hostname queda fijado antes de que el DHCP
  pida IP, así el router registra el nombre correcto desde el principio.
- Si `robot_id.txt` falta o es inválido, **no adivina**: registra el problema en
  `/var/log/atriz-first-boot.log`, deja el sistema intacto y **se reintenta en el siguiente
  arranque**. Es preferible a que dos robots acaben con la misma identidad en silencio.
- Escribe la identidad en `/etc/profile.d/atriz-robot.sh` (no en `.bashrc`), así es
  idempotente y fácil de inspeccionar.
- Se deshabilita solo, dejando la marca `/var/lib/atriz-first-boot.done`.

**Para cambiar el número de un robot ya desplegado:** edita `robot_id.txt`, borra
`/var/lib/atriz-first-boot.done` y reinicia.

> 📝 **NO VERIFICADO.** Estos scripts se escribieron **antes** de disponer de un segundo
> robot. Al clonar el primero, comprueba cada paso y corrige este documento. La lógica de
> parseo de `robot_id.txt` sí se probó de forma aislada, incluido el caso trampa de `08`
> (que sin `10#` bash interpretaría como octal).

---

## Imagen dorada — detalle

### Crearla

Desde el robot de referencia ya validado (Fase 0.3 → Fase 5 completas):

> 🔴 **ESTE PROCEDIMIENTO ESTABA MAL HASTA EL 2026-08-01, y el fallo era grave.** Omitía
> `fase_6_preparar_imagen_dorada.sh` y ponía «antes de clonar, quitar lo único de cada robot»
> **después del `dd` que ya había clonado**. Siguiéndolo al pie de la letra salían **16 robots
> con el mismo `machine-id`, las mismas claves SSH de host, el mismo hostname y sin
> `first-boot.service`** — o sea, sin ninguna forma de personalizarse.
>
> Y el mismo documento tenía el procedimiento correcto en otra sección. **Dos procedimientos
> contradictorios, y el malo era el que estaba bajo el título «Imagen dorada — detalle».**

```bash
# ── 1. EN LA PI ──────────────────────────────────────────────────────────
# Comprobar que no queda trabajo sin subir. Mira los DOS repositorios.
bash ~/atriz_migracion/scripts/fase_0_3_respaldo.sh

# 🔴 EL PASO QUE FALTABA. Borra la identidad de ESTE robot e instala
#    atriz-first-boot.service, que es quien personaliza cada clon al arrancar.
#    Sin esto, los 16 clones son el robot 01 dieciséis veces.
sudo bash ~/atriz_migracion/scripts/fase_6_preparar_imagen_dorada.sh

# ⚠️ A partir de aquí el robot YA NO TIENE IDENTIDAD: no vuelvas a arrancarlo
#    antes del dd, o first-boot se ejecutará y se la volverá a dar.
sudo poweroff

# ── 2. CON LA microSD EN UN PC ───────────────────────────────────────────
sudo dd if=/dev/mmcblk0 of=atriz_jazzy_v1.img bs=4M status=progress conv=fsync
sha256sum atriz_jazzy_v1.img > atriz_jazzy_v1.img.sha256
pishrink.sh atriz_jazzy_v1.img          # reduce la imagen al tamaño usado
```

**Qué borra `fase_6_preparar_imagen_dorada.sh`** (no lo hagas a mano: es la lista que se
olvida):
- claves SSH de host (`/etc/ssh/ssh_host_*`) → se regeneran en el primer arranque
- `machine-id` (`/etc/machine-id` vacío → systemd lo regenera)
- hostname y `/etc/profile.d/atriz-robot.sh` (el `ROS_DOMAIN_ID`)
- la marca `/var/lib/atriz-first-boot.done`, para que first-boot vuelva a correr
- `~/.bash_history`, logs

🔴 **La imagen es material sensible:** lleva la PSK del WiFi y la contraseña del usuario. No
sale del laboratorio, no va a git, y no se comparte por servicios en la nube.

### Personalizar en el primer arranque

Un fichero de texto en la partición `/boot/firmware` —**editable desde cualquier PC, sin
arrancar la Pi**— y un servicio que lo lee:

```
# /boot/firmware/robot_id.txt
ROBOT_ID=03
```

`first-boot.service` ✅ (ya escrito, `scripts/first-boot.service`) lee ese fichero y fija hostname,
`ROS_DOMAIN_ID`, namespace y claves; luego se deshabilita solo.

**Por qué en `/boot/firmware`:** es la partición FAT, legible desde Windows, macOS y Linux.
Grabas 16 tarjetas, editas un número en cada una, y listo. Sin sesiones SSH manuales.

---

## Versionado: los robots siguen etiquetas, no ramas

**Regla:** los robots se despliegan desde **tags**, nunca desde `main` ni desde ramas de
trabajo.

```bash
# Al validar una versión:
git tag -a v1.0-jazzy -m "Primer despliegue ROS 2 Jazzy validado"
git push origin v1.0-jazzy

# En cada robot:
git fetch --tags && git checkout v1.0-jazzy

# Para saber qué corre un robot:
git describe --tags
```

**Por qué.** Una rama se mueve bajo tus pies; un tag es inmutable. Cuando el robot 7 se
comporte distinto al 3, `git describe` responde en un segundo.

**Aprendido por las malas el 2026-07-29:** el clon de `Atriz_rvr` en esta Pi estaba **5
commits por detrás** de GitHub y **nunca se le había hecho `git fetch`**. Se auditó código
de nueve meses de antigüedad y tres hallazgos resultaron falsos. Con 16 máquinas y sin
disciplina de versiones, ese problema se multiplica por dieciséis y se vuelve imposible de
razonar.

---

## Longevidad de las microSD

Con 16 tarjetas, la mortalidad pasa de anécdota a tarea de mantenimiento. En la auditoría
original se midieron **47 segundos de bloqueo global por I/O en 42 minutos** con el sistema
ocioso, y **784 MB de journal** sin límite.

Obligatorio en la imagen dorada:

| Medida | Por qué |
|---|---|
| `journald.conf`: `Storage=volatile` o `SystemMaxUse=32M` | Era el mayor generador de escrituras |
| `log2ram` o `/var/log` en tmpfs | Idem |
| `noatime` en `/etc/fstab` | Evita una escritura por cada lectura |
| Sin swap | Evita bloqueos y desgaste |
| Timers `apt-daily` desactivados | 1 min 27 s + 1 min 14 s martilleando la tarjeta |
| Sin `tracker-miner-fs` (no habrá, con Server) | Indexaba la tarjeta continuamente |
| `chmod 600 /etc/netplan/*.yaml` | En 20.04 estaba en **`-rw-r--r--`**: la **PSK del WiFi era legible por cualquier usuario** del sistema. Con 16 robots y estudiantes con acceso, importa |

**Presupuestar tarjetas de repuesto** y tener la imagen dorada lista para reflashear. Con 16
robots, reflashear será rutina, no emergencia.

---

## 🔴 Robot 2: instalación LIMPIA, paso a paso

> **Este es el procedimiento de HOY**, y es distinto del «alta de un robot nuevo» de más abajo,
> que parte de la **imagen dorada**. Esa imagen **todavía no existe** y no debe construirse
> hasta que `provision.sh` se haya ejecutado entero al menos una vez — que es justamente lo que
> hace el robot 2.
>
> 🔴 **Hasta el 2026-08-01 esta sección no existía y el camino era circular**: el `README` decía
> «migra el robot 2 con `provision.sh`», `INSTALACION.md` decía «no sigas esta ruta a mano, ve a
> `FLOTA.md`», y `FLOTA.md` empezaba por «graba la imagen dorada». Nadie enumeraba los pasos en
> un solo sitio.

### Lo que hay que tener antes de empezar

- **El robot montado y cableado**: TX/RX **cruzados** entre la Pi y el RVR, **GND común**, y el
  LIDAR enchufado. Batería del RVR cargada — el paso 7 le habla al RVR y al LIDAR de verdad.
- Una microSD (16 GB o más) y un lector en el PC.
- **Un PC con Linux o WSL**, con `sudo`, y **este repositorio ya clonado ahí** — `preparar_tarjeta.sh`
  y `red.txt.ejemplo` viven en él. **Ya NO hace falta PAT**: desde el 2026-08-11 el repositorio es
  público (👤 decisión del usuario, justo para no repartir un token en 16 tarjetas). Medido ese
  día: `git clone` sin credencial ninguna, y lo mismo `Atriz_rvr`, del que clona `provision.sh`.
- ⚠️ **Si el PC es Windows, necesitas WSL** — este guion es de Linux. Ver §«Windows: preparar la
  tarjeta desde WSL» más abajo.
- Los datos de red: SSID y contraseña, y **la IP que le toca a este robot**.

### Los pasos

**1. Grabar Ubuntu Server 24.04 LTS arm64** con Raspberry Pi Imager. En sus opciones avanzadas:
hostname `rvr-02`, usuario `sphero`, **habilitar SSH con «usar contraseña para autenticar»**
(🔴 **NO «permitir sólo autenticación por clave pública»**), y 🔴 **CONFIGURAR LA WIFI** (SSID y
contraseña; preferir 5 GHz).

⚠️ **Sin WiFi aquí no hay forma de entrar.** El Pi 4 va headless: sin red no hay SSH, y sin SSH
no hay pasos 5 a 8. La primera vez lo encuentras por `ping rvr-02.local` o mirando el router.

🔴 **Y por contraseña, no por clave pública.** El Imager ofrece las dos, y la de clave pública
deja fuera igual de bien que no configurar la WiFi: el robot arranca headless, sin teclado ni
pantalla, y si la clave no es la del PC desde el que entras **la única salida es sacar la tarjeta
y volver al PC**. Así está rvr-02 y así está **rvr-01, medido el 2026-08-11**:

```
/etc/ssh/sshd_config:  #PasswordAuthentication yes   ← comentado, o sea el "yes" por defecto
~/.ssh/authorized_keys: existe, 0 bytes, 0 claves
```

o sea que **a rvr-01 sólo se entra por contraseña**, porque no tiene ninguna clave instalada.
Deja los dos robots iguales; que uno vaya por clave y otro por contraseña es la clase de
diferencia que aparece dentro de seis meses, con el robot montado y sin nadie que recuerde por
qué. 📌 Y para la imagen dorada: las claves de **host** se regeneran en el primer arranque
(§«qué se borra»), pero `~/.ssh/authorized_keys` **NO** — se clona tal cual. Si algún día se
instala una clave en el robot de referencia antes de sacar la imagen, esa clave abre **los 16**.

**2. 🔴 `preparar_tarjeta.sh`, CON LA TARJETA EN EL PC. NO ES OPCIONAL.**

```bash
sudo bash ~/atriz_migracion/scripts/preparar_tarjeta.sh --id 02
```

Hace cuatro cosas que **nada más hace**, y las cuatro fallan en silencio si faltan:

| | Si falta |
|---|---|
| **comprueba `ssh_pwauth` en `user-data`** y **aborta** si el Imager quedó en «solo clave pública» | el robot arranca headless, sin consola serie (se la quita este mismo script) y **sin forma de entrar**: hay que volver a grabar la tarjeta. Aquí todavía está en el PC, así que aquí es gratis |
| quita `console=serial…` de `cmdline.txt` | el UART queda reservado para la consola del kernel y **el RVR no habla**. 🔴 `provision.sh` **no toca `cmdline.txt`**: `fase_0_1_fix_uart.sh` solo **avisa** de que hay que quitarlo a mano |
| `dtoverlay=disable-bt` bajo `[all]` en `config.txt` | el PL011 no llega a los pines GPIO14/15 donde está cableado el RVR. ⚠️ Sin la cabecera `[all]` **no da error** y no hace nada |
| crea `/boot/firmware/robot_id.txt` | 🔴 **`provision.sh` lo NECESITA**: su paso 8/9 falla al instalar el arranque automático, y sin él no hay hostname ni `ROS_DOMAIN_ID` |

#### Windows: preparar la tarjeta desde WSL — ✅ recorrido el 2026-08-11

`preparar_tarjeta.sh` es un guion de Linux y el PC del laboratorio es Windows. Esto es lo que
costó dejarlo listo, con las dos zancadillas que salieron de verdad:

```powershell
wsl --install                 # admin. Reinicia al acabar
wsl --list --verbose          # ← MÍRALA antes de dar nada por hecho
wsl --set-default Ubuntu      # ⚠️ ver la trampa de Docker, justo debajo
wsl -d Ubuntu
```

🔴 **Trampa 1 — Docker Desktop secuestra `wsl`.** Si el PC tiene Docker Desktop, su distro
`docker-desktop` puede ser la predeterminada, y `wsl` a secas te mete ahí. Se reconoce en el acto:

```
LAPTOP-XXXX:/mnt/host/c/Users/tu# sudo apt update
-sh: sudo: not found
```

prompt `#` (ya eres root), `-sh` en vez de bash, `sudo` inexistente y **`/mnt/host/c/`** en vez de
`/mnt/c/`. No se trabaja ahí: Docker borra y recrea esa distro en cada actualización. `wsl
--set-default Ubuntu` lo arregla para siempre.

🔴 **Trampa 2 — `wsl --install -d Ubuntu` falla si Ubuntu ya está instalado** (`ERROR_ALREADY_EXISTS`),
aunque salga `Stopped` en la lista. No hay que instalarlo: hay que **arrancarlo**. Por eso el
`wsl --list --verbose` va antes.

Ya dentro de Ubuntu (📌 salió la 26.04; da igual, es el WSL del PC, no el robot):

```bash
whoami; echo $SHELL; ls /mnt/c >/dev/null && echo "/mnt/c OK"   # tu usuario · /bin/bash · OK
sudo apt update && sudo apt install -y git
cd ~ && git clone https://github.com/Bura-hub/Atriz_migracion_ros2.git atriz_migracion
cd ~/atriz_migracion && bash -n scripts/preparar_tarjeta.sh && echo "SCRIPT OK, sin CRLF"
```

⚠️ **Clona DENTRO de WSL, no uses la copia de Windows por `/mnt/c`.** Git en Windows suele
convertir los finales de línea a CRLF y bash muere con `$'\r': command not found`. El `bash -n`
del final es la comprobación: no ejecuta nada, sólo valida la sintaxis.

Y la tarjeta, que WSL2 **no automonta** por ser extraíble (suponiendo que Windows le dé la `E:`):

```bash
sudo mkdir -p /mnt/e && sudo mount -t drvfs E: /mnt/e
ls /mnt/e                                    # cmdline.txt y config.txt deben estar
sudo bash ~/atriz_migracion/scripts/preparar_tarjeta.sh --id 02 --particion /mnt/e --simular
```

⏳ **NO VERIFICADO**: el montaje `drvfs` y el guion sobre una tarjeta física. En `drvfs` el
respaldo (`cp -a`) puede no crearse **sin que el guion pare** —no lleva `set -e`—, así que tras la
pasada de verdad hay que comprobar a mano que aparecen `cmdline.txt.bak-…` y `config.txt.bak-…`.

**3. `red.txt` en la misma partición FAT**, copiando `scripts/red.txt.ejemplo` y rellenándolo con
la IP de este robot. Manual, cap. 19.3. ⚠️ Lleva la PSK del WiFi: **no va a git**.

**4. Meter la tarjeta, arrancar, y entrar por SSH.** Comprobar el UART antes de nada:

```bash
cat /proc/device-tree/soc/serial@7e215040/status   # debe decir: disabled
cat /proc/device-tree/aliases/serial0              # /soc/serial@7e201000 (PL011)
```

🔴 **Si el mini-UART NO dice `disabled`, el paso 2 no se aplicó. Párate aquí.**

> ⚠️ **La primera versión de este procedimiento comprobaba `aliases/uart0` y `ls /dev/serial0`, y
> las dos estaban mal.** `aliases/uart0` da `/soc/serial@7e201000` **siempre** —es un alias fijo
> del DTB base, no lo cambia `disable-bt`— así que la comprobación **no podía fallar nunca**. Y
> `/dev/serial0` **no existe en Ubuntu**: es de Raspberry Pi OS. Habrías pasado el control con el
> `cmdline.txt` sin arreglar y te enterarías 40 minutos después, cuando el RVR no conteste.
> Encontrado en auditoría el 2026-08-01, midiéndolo en rvr-01.

**5. Clonar el repositorio.** ✅ **Ya no hacen falta credenciales** — desde el 2026-08-11
`Atriz_migracion_ros2` y `Atriz_rvr` son públicos (👤 decisión del usuario, justo para no repartir
un PAT en 16 microSD). Medido ese día: los dos clonan sin credencial ninguna.

```bash
git clone https://github.com/Bura-hub/Atriz_migracion_ros2.git ~/atriz_migracion
```

> Texto anterior, que ya no aplica: *«el repositorio es privado y sin esto `provision.sh` no puede
> clonar»*, seguido de `credential.helper store` y `chmod 600 ~/.git-credentials`. **No lo hagas:**
> guardar un PAT que no hace falta es justo lo que convertía `~/.git-credentials` en el bloqueante
> nº 1 de la Fase 6.

**6. Aprovisionar.** Son ~40 min, la mayoría compilando:

```bash
sudo bash ~/atriz_migracion/scripts/provision.sh
```

⚠️ **Es la primera vez que este script se ejecuta entero.** Es exactamente el objetivo del robot
2: hasta ahora solo se ha probado con `--simular`, que convierte en no-operación justo lo que
instala. **Anota cualquier fallo**: es la suposición más peligrosa que le queda al proyecto.

**6-bis. 🔴 LA RED, que `provision.sh` NO configura.** El `red.txt` del paso 3 lo lee
`atriz-first-boot`, y ese servicio **solo lo instala `fase_6_preparar_imagen_dorada.sh`** — que en
una instalación limpia todavía no se ha ejecutado. Sin este paso el robot se queda en **DHCP puro**,
sin su IP de laboratorio:

🔴 **Y aquí es donde `red.txt` deja de poder aplazarse.** Si en el paso 3 se dejó para luego —es
legítimo: sin él `first-boot` no adivina, deja el DHCP de cloud-init y el robot arranca igual—,
**este paso no tiene de dónde leer la IP**. Créalo ahora, en el propio robot, antes de seguir:

```bash
sudo cp ~/atriz_migracion/scripts/red.txt.ejemplo /boot/firmware/red.txt
sudo nano /boot/firmware/red.txt     # LAB_SSID, LAB_PASS y LAB_IP como mínimo
```

⚠️ Lleva la PSK: **no va a git**, y `chmod 600` sobre la FAT **no hace nada** (ver la plantilla).

```bash
sudo bash ~/atriz_migracion/scripts/first-boot.sh --solo-red
sudo netplan try --timeout 90        # revierte solo si pierdes la conexión
```

**6-ter. ⚠️ EL LIDAR: la regla udev lleva el puerto de rvr-01 a fuego.** Si el LIDAR de este robot
no va **exactamente en el mismo puerto USB físico**, no habrá `/dev/ydlidar` → sin `/scan` → el
`collision_monitor` bloquea el movimiento → **el robot parecerá averiado**. Comprueba y corrige:

```bash
ls -l /dev/ydlidar || udevadm info -q property -n /dev/ttyUSB0 | grep ID_PATH=
# si el ID_PATH no coincide con el de 99-ydlidar.rules, edítalo y:
sudo udevadm control --reload-rules && sudo udevadm trigger
```

**7. Reiniciar y verificar** — en ese orden, que es el que dice `provision.sh`:

```bash
sudo reboot
```

⚠️ `fase_7` deja el servicio **habilitado pero sin arrancar**, así que antes del reinicio no corre
nada y media docena de comprobaciones de ROS saldrían mal **sin que el robot esté mal**.

Y entonces, lo que decide si el robot está listo:

```bash
bash ~/atriz_migracion/scripts/verificar_robot.sh --hardware
```

**8. Comprobar que vuelve solo:**

```bash
systemctl status atriz-robot
atriz-escaneo on          # sin barrido el collision_monitor no deja conducir
```

📝 **Si `provision.sh` falló en algún paso:** no aborta, **acumula** los fallos y los lista al
final bajo `PASOS CON PROBLEMAS`. Es **idempotente**: arregla la causa y vuelve a ejecutarlo. ⚠️ Un
`provision.sh` que «termina» puede haber dejado Nav2 sin instalar o el workspace sin compilar —
**lee esa lista**, no solo el código de salida.

### Y entonces sí, la imagen dorada

Con el robot 2 funcionando, `provision.sh` deja de ser una suposición. **Ese es el momento** de
construir la imagen dorada (sección de abajo) y clonar los 14 restantes.

---

## Alta de un robot nuevo — **desde la imagen dorada**

> ⚠️ **Esto es para los robots 3 a 16**, cuando la imagen dorada ya exista. Para el **robot 2**,
> que es una instalación limpia y el que valida `provision.sh`, usa la sección de arriba.

**1. Grabar** la imagen dorada en la microSD (Raspberry Pi Imager o `dd`).

**2. Preparar la tarjeta**, con ella todavía en el PC:
```bash
sudo bash ~/atriz_migracion/scripts/preparar_tarjeta.sh --id NN
```
Fija `robot_id.txt` y comprueba `cmdline.txt` y `config.txt`. Lleva `--simular` si quieres ver
qué haría antes de que lo haga.

**3. Montar el hardware.** RVR por UART: **TX y RX van CRUZADOS** (GPIO14→RX, GPIO15→TX) y el
**GND común es obligatorio** — sin él la comunicación falla de forma errática, no limpia, que
es mucho peor para diagnosticar. El LIDAR, **en el mismo puerto USB físico que en los demás
robots** (ver restricción 1: los CP2102 no tienen serial único).

**4. Arrancar.** `atriz-first-boot` lee `robot_id.txt` y fija hostname, `ROS_DOMAIN_ID`,
`machine-id` y claves SSH de host. Espera ~2 minutos.

> Tu PC avisará de una **huella SSH nueva** al conectarte. Es lo esperado: cada robot genera
> sus claves en el primer arranque. Si **no** avisara, es señal de que las claves se clonaron
> y todos los robots comparten identidad — eso sí es un problema.

**5. Comprobar que responde por su nombre.** Desde tu PC, no desde el robot:

```bash
ping rvr-NN.local
```

✅ **Ya no hacen falta reservas DHCP.** Cada robot lleva su IP estática en
`/boot/firmware/red.txt` —editable metiendo la microSD en cualquier PC— **y** responde a
`rvr-NN.local` por mDNS. No dependes de que nadie configure el router, y el robot funciona
igual en el laboratorio que en una red que no conocías.

⚠️ Sí conviene **anotar la MAC** en el inventario: sigue siendo lo único que identifica al
hardware si hay que reclamar algo al administrador de red.

**6. Verificar.** Un solo comando decide si el robot está listo:
```bash
bash ~/atriz_migracion/scripts/verificar_robot.sh --hardware
```
36+ comprobaciones y **código de salida ≠ 0 si algo falla**. No des el robot por bueno sin
esto: los fallos de este proyecto son los que no se manifiestan como error. Si sale limpio,
comprueba además las frecuencias, que dependen de ROS 2:
```bash
# 🔴 NI namespace NI `topic hz`: los topics son /odom y /scan (sin namespace), y
#    `ros2 topic hz` da 0 Hz sobre ellos SIEMPRE porque son BEST_EFFORT y él se
#    suscribe RELIABLE. Este comando habría hecho parecer averiado a un robot sano.
python3 ~/atriz_migracion/00_auditoria/evidencia/mediciones_banco/medir_ritmo_ros2.py
#    → /odom ≈ 16.5 Hz · /scan 10.1–11.9 Hz (con `atriz-escaneo on`)
```

**7. Rellenar la fila** de la tabla de asignación de este documento. Sin inventario no se
diagnostica nada a distancia.

**8. Registrar el robot** en la plataforma web.

### Lo que la imagen dorada NO resuelve

Conviene tenerlo claro para no confiarse:

| | |
|---|---|
| **Deriva posterior** | La imagen iguala los robots el día 1. A partir de ahí divergen en cuanto alguien toca uno. La respuesta es `git pull && sudo bash provision.sh` en los 16, o Ansible |
| **Actualizaciones de seguridad** | La higiene deshabilita `unattended-upgrades` a propósito (no queremos que un robot se actualice a mitad de un experimento). Eso significa que **actualizar los 16 es una tarea manual y periódica** |
| ~~**La regla udev del LIDAR**~~ | ✅ **CERRADO el 2026-08-11 con rvr-02**: el `ID_PATH` ES idéntico en otro Pi, `provision.sh` lo comprobó sobre el hardware (`✓ /dev/ydlidar existe: la regla CASA en este robot`). La regla **es clonable tal cual**. Sigue vigente que el LIDAR vaya en el mismo conector físico en los 16. Ver restricción 1 |
| **El ancho de banda en operación** | La imagen ahorra el tráfico de *instalación*, no el de *telemetría*. El riesgo nº4 sigue intacto y sin medir |
| **Las tarjetas microSD** | Mueren. Con 16 unidades es mantenimiento periódico. Tener la imagen lista es precisamente lo que convierte eso en 10 minutos |

---

## Salud de la flota

Pendiente de la Fase 6: un endpoint que agregue de los 16 robots batería, uptime,
temperatura, y si `/odom` y `/scan` están vivos. Con alerta de batería baja.

Umbrales de referencia, de las mediciones de la Fase 0.1:

| Señal | Normal | Sospechoso |
|---|---|---|
| `/odom` | 16.5 Hz | < 12 Hz |
| `/scan` | **10.1–11.9 Hz** | **< 9.5 Hz** |
| Temperatura | 58–64 °C con el stack | > 75 °C |
| RSS del driver | ~53 MB, plano | crecimiento sostenido = fuga |
| CPU del driver | **~34 %** | > 55 % sin causa |

🔴 **El umbral de `/scan` estaba mal y no habría saltado nunca.** Decía «normal ~10 Hz,
sospechoso < 8». El X2 **gira libre** y lo normal son **11.5 Hz**, así que un LIDAR degradado
un 22 % —a 9 Hz— quedaba dentro de «normal». Un umbral que no puede dispararse es peor que no
tenerlo.

⚠️ **Y no midas `/odom` ni `/scan` con `ros2 topic hz`**: los dos son BEST_EFFORT y esa
herramienta se suscribe RELIABLE, así que da **0 Hz siempre** con el robot perfecto. Usa
`medir_ritmo_ros2.py`.
