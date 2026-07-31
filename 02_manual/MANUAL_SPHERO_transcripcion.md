# MANUAL SPHERO — transcripción

> **Qué es este documento.** Transcripción fiel del texto de `MANUAL_SPHERO_original.docx`,
> el manual con el que se montó el sistema Ubuntu 20.04 + ROS Noetic que existe hoy.
>
> **Por qué existe.** El `.docx` es un binario de 5.6 MB: no se puede buscar desde un
> servidor, ni diffear, ni citar por línea. Esta versión sí. El original se conserva
> intacto porque **es el procedimiento de reversión** si la migración a ROS 2 falla.
>
> **Metadatos del original:** autor *DIANA SOFIA VALLEJO PARRA* · creado 2026-03-10 ·
> modificado 2026-03-17 · 38 páginas · 2.936 palabras · Word 16 · 40 imágenes embebidas
> (33 PNG, 2 JPEG, 5 HD Photo). Sin encabezados, pies ni notas al pie.
>
> **Convenciones de esta transcripción:**
> - Los comandos se reproducen **literalmente**, incluidas las erratas del original.
> - Los pies de figura aparecen en *cursiva* (las imágenes no se transcriben).
> - `«CONTRASEÑA»` sustituye a la credencial real. Ver [SEGURIDAD](#nota-de-seguridad).
> - Los bloques `> ⚠️ AUDITORÍA` **no están en el original**: son hallazgos añadidos
>   en julio de 2026 al auditar el sistema. Se distinguen tipográficamente a propósito.

---

## PRIMERA SECCIÓN

Instalación de Ubuntu 20.04 LTS. Se accede al repositorio oficial de Raspberry Pi OS a través del siguiente enlace https://www.raspberrypi.com/software/ , una vez se ingresa, se da clic en el botón "Download for Windows".

Posteriormente, abra la herramienta de instalación oficial de Raspberry Pi y acepte los permisos del administrador, después seleccione el idioma de su elección. Una vez iniciado el asistente de instalación seleccione el botón "siguiente" y acepte los términos y condiciones presentados, elija la ubicación del asistente, y continue aceptando hasta finalizar la instalación.

Después de abrir la herramienta, se observará la ventana principal de Raspberry Pi, en donde deberá seleccionar las siguientes opciones; a). En el dispositivo elegirá Raspberry Pi 4. b). En el sistema operativo, deberá bajar hasta encontrar la opción de "Other general – purpose OS", después, seleccione Ubuntu y elija la versión **Ubuntu server 20.04.5 LTS (64-bit)**.

*a). Dispositivo*
*b). Sistema operativo*

c). Para el Almacenamiento, deberá asegurarse primero de haber insertado una memoria microSD card de al menos 32GB en su computador, esta funcionará como el dispositivo de almacenamiento de imagen del sistema operativo. A continuación, seleccione el dispositivo de almacenamiento.

*c). Almacenamiento*

En el paso siguiente, se visualizará la ventana de ajustes personalizados del SO, aquí deberá seleccionar el botón de "editar ajustes". Primero diríjase al apartado general y establezca el nuevo nombre de usuario como ´sphero´, y contraseña ´«CONTRASEÑA»´, también se debe activar la configuración LAN poniendo las credenciales de su red de 2.4Ghz (Este apartado es importante para lograr que la comunicación SSH), después seleccione el apartado de servicios, elija la opción de Activar SSH, guarde los cambios y acepte los ajustes.

Para continuar, deberá permanecer en la interfaz hasta que finalice el proceso de escritura y verificación. Espere a que se muestre un cuadro de diálogo confirmando que la "escritura fue exitosa", verifique que la versión del sistema operativo y la ubicación de escritura sean correctas. Una vez completado el proceso, de clic en continuar, a partir de ahora ya puede retirar la memoria microSD de su computadora.

> ⚠️ **AUDITORÍA — se instala Ubuntu Server, y está bien.** El manual elige la
> edición *Server*, que es la correcta para un robot. El escritorio se añade
> después a mano (ver más abajo), y ahí es donde nace el mayor problema de
> rendimiento del sistema actual.

---

## Inicio y configuración del Sistema Operativo (SO)

Primero se presenta el diagrama con la identificación de los puertos y pines de la Raspberry.

*Puertos de la Raspberry Pi 4 Model B*

**Raspberry pi 4 Model B**
- Puerto microSD-card
- Puerto de alimentación (USB-C)
- Puertos de video micro HDMI
- Jack de Audio 3.5 mm
- Puertos USB
- Puerto Ethernet
- Pines GPIO

Para inicializar el sistema operativo se deben seguir los siguientes pasos; a). Se inserta la memoria microSD-card en la Raspberry pi 4 Model B. b). conecte el cable de alimentación y c). (1.) Conecte periféricos (pantalla y teclado) o acceda mediante (2.) Comunicación SSH.

*Conexión microSD*
*Conexión de la Fuente de alimentación*

### c.1 Conexión de periféricos

Para realizar la instalación mediante este método se debe conectar adicionalmente a la Raspberry Pi (a.) un cable desde un puerto micro HDMI a una pantalla externa. Además de esto (b.) un mouse (Opcional) y un teclado cada uno desde un puerto USB. Véase en la siguiente imagen

### c.2 Comunicación SSH

Después de conectar la fuente de alimentación debemos buscar la dirección IP a la que ha sido asignada la Raspberry Pi en nuestra red local para esto usaremos el programa Advanced IP scanner, disponible en este enlace https://www.advanced-ip-scanner.com/es/download/ Una vez ingresa se debe esperar unos segundos y la descarga iniciara automáticamente. Abra la herramienta de instalación y seleccione el idioma de su preferencia. Después de esto puede elegir si ejecutar la herramienta directamente o instalarla

Posteriormente ejecute el programa y antes de presionar el botón de "Explorar" desconecte la alimentación de la Raspberry Pi, ahora si (a.) Presionar el botón de explorar para listar todas las direcciones ip. Después de acabado el escaneo conecte la alimentación de la Raspberry Pi, y ahora si (b.) Presione nuevamente el botón para listar nuevamente direcciones ip. Finalmente (c.) viendo cual nueva ip se ha añadido al listado podremos determinar la dirección de la Raspberry pi en nuestra red local

*Escaneo con Raspberry apagada*
*2585501016635*  ← residuo de un cuadro de texto en el original
*Escaneo con Raspberry apagada*  ← pie repetido en el original

En este caso se observa que la nueva ip es 192.168.1.19 por lo cual esta debería ser la ip de la Raspberry Pi.

Bien en este punto ya tenemos todo listo para acceder a la consola de Ubuntu y poder instalar todas las herramientas necesarias para instalar los controladores.

> ⚠️ **AUDITORÍA — este método no escala a 16 robots.** Descubrir la IP comparando
> escaneos de red antes y después de encender es viable con un robot y frustrante
> con dieciséis. Ver §6.3 del plan de migración: reservas DHCP por MAC en el router,
> y hostname fijado en el primer arranque (`rvr-01` … `rvr-16`).

---

## Login e instalación de escritorio gráfico — Ubuntu

Si se ha escogido iniciar la instalación con una pantalla conectada a la Raspberry Pi se observará esto después de esperar que todo cargue e inicie.

En este apartado se debe poner el usuario y contraseña definidos en el proceso de grabado de imagen del sistema operativo:

```
Ubuntu login: sphero
Password: «CONTRASEÑA»
```

Si ha escogido iniciar la instalación a través de SSH debe realizar lo siguiente. A través del CMD podemos conectarnos a la consola de la Raspberry con los siguientes comandos, recordando la ip encontrada, usuario y contraseña definidos en el proceso de grabado de imagen.

```
ssh sphero@192.168.1.19
yes
«CONTRASEÑA»
```

Para ambos casos, sea directamente desde la Raspberry Pi o desde conexión SSH al finalizar el login podremos ver lo siguiente. En este punto ya podemos empezar a configurar directamente desde consola.

### Instalación de controladores y actualizaciones

La primera vez que se abre la consola es necesario escribir la contraseña después de una instrucción "sudo".

```bash
sudo dpkg --configure -a
```
Este comando repara instalaciones o actualizaciones de paquetes que quedaron incompletas en sistemas basados en Debian (como Ubuntu).

```bash
sudo apt-get update
```
Este comando actualiza la lista de paquetes disponibles en los repositorios configurados en tu sistema. No instala ni actualiza programas, solo sincroniza la base de datos de apt con los servidores.

```bash
sudo apt-get upgrade
```
Este comando actualiza los paquetes instalados en tu sistema a las versiones más recientes disponibles (según lo encontrado con update).

En algunas instrucciones el sistema pide permiso para descargar paquetes necesarios, en los cuales se debe aceptar [Y/n] con Y

```bash
sudo apt install ubuntu-desktop
```
Este comando instala el entorno gráfico completo de Ubuntu (la interfaz de escritorio) en un sistema que no lo tiene o que necesita ser restaurado.

```bash
sudo apt install xrdp
```
Este comando instala XRDP, un servidor de escritorio remoto para sistemas Linux que permite conectarte gráficamente a tu máquina Ubuntu desde otro dispositivo usando el protocolo RDP (Remote Desktop Protocol), el mismo que usa Windows.

Ahora instalado este módulo grafico podemos conectar a través "Remote Desktop Connection" esto es posible gracias al último paquete instalado.

Aquí se ingresa la dirección ip de la Raspberry pi que se ha encontrado en pasos anteriores 192.168.1.19 y se acepta la conexión remota en la ventana siguiente. Para finalmente en la siguiente ventana poner el username y password, como se ha definido en los pasos anteriores.

*Login en ubuntu*
*Pantalla principal en el escritorio*

En la pantalla de bienvenida, se deben completa los pasos de configuración inicial y el escritorio de Ubuntu quedaría listo para el manejo, conexión e instalación de paquetes adicionales.

> 🔴 **AUDITORÍA — estos dos comandos son la causa nº1 de la lentitud del sistema.**
> `ubuntu-desktop` + `xrdp` sobre una Server convierten el robot en un escritorio.
> Estado medido en julio de 2026:
> - `systemctl get-default` → `graphical.target`
> - **Dos** sesiones gráficas simultáneas: `gdm` (Xorg vt1 + gnome-shell 208 MB) y
>   `sphero` (Xorg vt2 + gnome-shell **395 MB**)
> - ~120 procesos GUI (`gsd-*`×25, `ibus-*`×6, `gvfs*`×10, `evolution-*`×4,
>   `tracker-miner-fs` indexando la microSD)
> - **273 tareas totales** con ROS parado
> - `gdm.service` 10.8 s + `plymouth-quit-wait` 13.3 s del arranque
> - `xrdp` escuchando en **0.0.0.0:3389** y **:3350**
>
> Ninguno de estos recursos sirve al robot. En la migración a ROS 2 se instala
> Ubuntu **Server** y no se añade escritorio: el acceso es por SSH y la
> visualización (RViz2) se hace desde un portátil, no en la Pi.

---

## Configuración de Ubuntu para adaptación del Sphero RVR

En este apartado a través de la consola vamos a seguir algunas configuraciones para poder completar correctamente la comunicación serial UART que básicamente se encarga de enviar y recibir datos en serie, es decir, bit por bit, a través de dos líneas principales:

- **TX** (transmit): línea de transmisión de datos.
- **RX** (receive): línea de recepción de datos.

Opcionalmente puede incluir:
- **GND**: tierra común entre dispositivos.
- **RTS/CTS**: para control de flujo (en versiones avanzadas).

### Configuración de la comunicación UART

```bash
sudo nano /boot/firmware/cmdline.txt
```
Es un archivo de texto que contiene una única línea con los parámetros que se le pasan al kernel de Linux durante el arranque. Define cómo debe iniciar el sistema, qué partición usar como raíz, opciones de consola, y más.

Dentro del editor de texto nano, se observa la línea de configuración que debe quedar así, se puede copiar y pegar con Ctrl+C y Ctrl+V

```
elevator=deadline net.ifnames=0 dwc_otg.lpm_enable=0 console=tty1 root=LABEL=writable rootfstype=ext4 fsck.repair=yes rootwait fixrtc quiet splash
```

Después se guarda con Ctrl+O y enter, y finalmente se puede salir con Ctrl+X.

Lo más importante en este apartado de configuración es la eliminación de `console=serial0,115200` ya que cuando se tiene esta línea, el sistema reserva el puerto serie serial0 (UART) para la consola del sistema, lo que significa que:
- El sistema envía mensajes de arranque y logs por ese puerto.
- Puede abrir una terminal de login en él.
- No se podrá usar libremente para comunicarse con otros dispositivos como el Sphero RVR, porque estará ocupado.

Aquí se libera el puerto serial (serial0, que usualmente apunta a ttyS0)

> ✅ **AUDITORÍA — este paso es correcto y hay que conservarlo.** Quitar
> `console=serial0,115200` es imprescindible, y la imagen de Ubuntu 24.04 lo
> vuelve a traer por defecto: habrá que repetirlo tras reinstalar. Verificado:
> el `cmdline.txt` actual usa `console=tty1` y `serial-getty@ttyS0` está
> `disabled`. El puerto está libre.
>
> Dos apuntes menores: `elevator=deadline` es un parámetro **obsoleto e ignorado**
> en kernel 5.4 con blk-mq, y la afirmación "serial0 usualmente apunta a ttyS0"
> es cierta **solo porque falta `disable-bt`** — ver el bloque siguiente.

```bash
sudo usermod -a -G dialout $USER
```
Este comando sirve para agregar tu usuario al grupo dialout, lo cual te da permiso para acceder a los puertos seriales sin necesidad de usar sudo.

```bash
sudo nano /etc/udev/rules.d/50-serial.rules
```
Dentro del editor de texto nano ponemos:
```
KERNEL=="ttyS0", MODE="0666"
```
Esto crea una regla que automatiza un cambio de permisos. Así, cada vez que el sistema crea /dev/ttyS0 (por ejemplo, al arrancar), lo hace ya con permisos 0666.

```bash
sudo udevadm control --reload-rules && sudo udevadm trigger
```
Este comando se usa para recargar las reglas de udev y aplicarlas inmediatamente, sin necesidad de reiniciar el sistema.

```bash
sudo systemctl stop serial-getty@ttyS0.service
sudo systemctl disable serial-getty@ttyS0.service
```
Detiene temporalmente el servicio que proporciona una consola de login sobre el puerto serial ttyS0, ya que si está activo, el sistema podría seguir usando el UART para login serial, y eso interferiría con la comunicación con el Sphero RVR. `disable` lo desactiva permanentemente al iniciar el sistema.

> 🔴 **AUDITORÍA — AQUÍ ESTÁ LA LAGUNA MÁS GRAVE DEL MANUAL.**
>
> **El manual nunca toca `/boot/firmware/config.txt`.** Falta `dtoverlay=disable-bt`.
> Sin él, en la Raspberry Pi 4 el reparto de UARTs es:
>
> | UART | Hardware | Asignación por defecto |
> |---|---|---|
> | `ttyAMA0` | **PL011** (bueno: FIFO de 32 B, reloj estable) | reservado al **Bluetooth** |
> | `ttyS0` | **mini-UART** 16550 (FIFO de 8 B) | pines GPIO14/15 → **el RVR** |
>
> El mini-UART deriva su baudrate del **reloj del núcleo VPU**, que es variable.
> Sin `core_freq` fijo, el baudrate real de `/dev/ttyS0` **deriva cuando el VPU
> cambia de frecuencia** → bytes corruptos, checksums inválidos y desconexiones
> intermitentes con el RVR.
>
> Estado verificado en julio de 2026:
> - `usercfg.txt` está **completamente vacío** (solo comentarios)
> - No hay `disable-bt`, ni `miniuart-bt`, ni `core_freq` en ningún fichero de boot
> - `bluetoothd` lleva **2 meses y 21 días** corriendo — y `hciconfig -a` no devuelve
>   **nada**: no hay ningún adaptador Bluetooth registrado
>
> Es decir: se paga el coste (perder el UART bueno) sin obtener el beneficio.
>
> **Corrección** — en `usercfg.txt` (o `config.txt` en 24.04):
> ```
> dtoverlay=disable-bt
> enable_uart=1
> ```
> Esto devuelve el **PL011 a GPIO14/15**, cuyo reloj no depende del VPU: elimina
> el problema de raíz, mejor que fijar `core_freq`. Después, deshabilitar
> `bluetooth.service` y `serial-getty@ttyAMA0`.
>
> **Segundo hallazgo:** `/dev/serial0` **no existe en Ubuntu**. A diferencia de
> Raspberry Pi OS, Ubuntu no instala las reglas udev que crean ese symlink. El
> manual lo menciona como si existiera. Verificado:
> `ls /dev/serial*` → `No such file or directory`.
>
> **Corrección** — regla propia en `/etc/udev/rules.d/99-rvr.rules`:
> ```
> SUBSYSTEM=="tty", KERNEL=="ttyAMA0", SYMLINK+="rvr", MODE="0660", GROUP="dialout"
> ```
> Y que todo el código use `/dev/rvr`. Hoy `/dev/ttyS0` está **hardcodeado en 4
> sitios** del repositorio `Atriz_rvr` (`serial_async_dal.py:15`,
> `serial_observer_dal.py:17`, `sphero_rvr_hw_interface.cpp:29`,
> `base_controller.cpp:40`), sin forma de cambiarlo por parámetro.

---

## Instalación ROS Noetic

Ahora ya configurado instalaremos el núcleo central de funcionamiento ROS Noetic. Esto es una distribución del sistema operativo robótico ROS (Robot Operating System), específicamente: ROS Noetic Ninjemys es la última versión oficial de ROS 1, lanzada en mayo de 2020 y diseñada para ejecutarse en Ubuntu 20.04 LTS (Focal Fossa).

```bash
sudo sh -c 'echo "deb http://packages.ros.org/ros/ubuntu $(lsb_release -sc) main" > /etc/apt/sources.list.d/ros-latest.list'
```
Este comando agrega el repositorio oficial de ROS a Ubuntu.

```bash
curl -s https://raw.githubusercontent.com/ros/rosdistro/master/ros.asc | sudo apt-key add -
```
Este comando sirve para agregar la clave GPG del repositorio oficial de ROS.

```bash
sudo apt update
```
hace faltar ahora actualizar la paqueteria

```bash
sudo apt install ros-noetic-desktop-full
```
Es un metapaquete, es decir, un paquete que agrupa muchos otros paquetes esenciales y avanzados de ROS Noetic

```bash
source /opt/ros/noetic/setup.bash
```
sirve para configurar temporalmente el entorno de ROS Noetic en la terminal actual.

```bash
echo "source /opt/ros/noetic/setup.bash" >> ~/.bashrc
source ~/.bashrc
```
Este conjunto de comandos sirve para activar automáticamente el entorno de ROS Noetic cada vez que abras una terminal, sin tener que escribir el comando manualmente.

```bash
sudo apt install python3-rosdep python3-rosinstall python3-rosinstall-generator python3-wstool build-essential ros-noetic-rosparam-shortcuts
```
Este commando sirve para instalar herramientas necesarias para gestionar, compilar y trabajar con proyectos ROS Noetic en Python 3, especialmente cuando estás configurando tu propio espacio de trabajo (atriz_git).

```bash
sudo rosdep init
rosdep update
```
`init` crea un archivo de configuración global. `update` descarga o actualiza la base de datos de dependencias de ROS desde GitHub, para que rosdep sepa qué paquetes del sistema necesita instalar según los `package.xml`.

```bash
sudo reboot
```
Reiniciamos todo el sistema para aplicar cambios

> ⚠️ **AUDITORÍA — `desktop-full` es un exceso considerable en un robot.**
> Arrastra Gazebo, RViz, rqt completo y perception/OpenCV. Estado medido:
> **236 paquetes `ros-noetic-*`** instalados, con `ros-noetic-desktop-full`,
> `ros-noetic-desktop` **y** `ros-noetic-ros-base` presentes **a la vez**.
> Para un RVR por UART basta `ros-base`. En ROS 2 se instalará
> `ros-jazzy-ros-base` y RViz2 se ejecutará desde un portátil.
>
> Nota adicional: `apt-key add` está **obsoleto** desde Ubuntu 22.04. El
> procedimiento actual usa `/usr/share/keyrings/` con `signed-by=`.

---

## Instalación del controlador Sphero RVR

Ahora ya instalado ROS descarguemos el controlador del Sphero RVR, guardado en el repositorio oficial del proyecto Atriz: https://github.com/Bura-hub/Atriz_rvr.git

```bash
mkdir -p ~/atriz_git/src
cd ~/atriz_git/src
git clone https://github.com/Bura-hub/Atriz_rvr.git
cd ~/atriz_git/
catkin_make
source devel/setup.bash
echo "source ~/atriz_git/devel/setup.bash" >> ~/.bashrc
```

`catkin_make` compila y activa el espacio de trabajo. `source devel/setup.bash` carga el entorno ROS específico del workspace: agrega tus paquetes al `ROS_PACKAGE_PATH` y permite `rosrun`/`roslaunch` desde el workspace. Este paso es temporal, solo dura mientras la terminal esté abierta; el `echo` lo hace permanente.

Ahora vamos a instalar las dependencias de la SDK de Sphero

```bash
sudo apt install python3-pip
pip install aiohttp requests websocket-client pytest-asyncio pytest twine pyserial pyserial-asyncio
pip install --upgrade packaging
```

Bibliotecas necesarias para comunicación HTTP, websockets, serial UART/USB, asynchronous I/O, pruebas automáticas y publicación de paquetes Python.

> ⚠️ **AUDITORÍA — dos observaciones.**
>
> 1. El manual dice "clona el repositorio **ros_sphero_rvr**" pero la URL es
>    `Atriz_rvr`. Es el nombre antiguo del proyecto, y esa confusión sobrevive
>    dentro del repo: `README.md` todavía documenta rutas `src/ros_sphero_rvr/`,
>    y `build/` conserva artefactos de `ros_sphero_rvr`, `sphero_rvr_hw` y
>    `sphero_rvr_msgs` que nunca se limpiaron.
> 2. `pip install` sin `--user` ni entorno virtual instala en el Python global,
>    mezclándose con los paquetes de ROS y del sistema. En Ubuntu 24.04 esto ya
>    **no está permitido** (PEP 668): habrá que usar `python3-venv` o
>    `--break-system-packages` de forma deliberada.
>
> **Buena noticia para la migración:** el SDK de Sphero vendorizado en el repo
> (103 ficheros) es **100 % agnóstico a ROS** — cero imports de `rospy`/`rclpy` —
> y está limpio para Python 3.12: cero `@asyncio.coroutine`, cero kwargs `loop=`,
> cero `yield from`. Solo 4 `asyncio.get_event_loop()`, de los cuales 3 están en
> el backend `observer` que no se usa. Portarlo es un parche de ~4 líneas.

---

## (Opcional) Instalación de joy_node

Para poder realizar una prueba de teleoperación con un Joystick.

```bash
sudo apt-get install ros-noetic-joy
ls /dev/input/
```

La primera vez que se ejecute `ls /dev/input/` se debe tener **desconectado** el Joystick de la Raspberry; la segunda vez debe estar conectado, para así lograr ubicar el nombre del Joystick en las entradas. Los dispositivos de joystick se identifican como `jsX`; en este caso, nuestro joystick es `js0`.

```bash
sudo jstest /dev/input/jsX     # js0 en este caso
```
Al mover o presionar los botones del Joystick debería mostrar actualizaciones en los estados de la consola; en cuanto se verifique que responde se puede salir con Ctrl+C.

```bash
ls -l /dev/input/jsX
sudo chmod a+rw /dev/input/jsX
```
Permisos de lectura y escritura para todos los usuarios sobre el dispositivo de joystick.

> ⚠️ **AUDITORÍA — `chmod` manual no sobrevive a un reinicio.** Igual que con el
> puerto serie, lo correcto es una regla udev. Y `/dev/input/js0` no es
> determinista si hay varios dispositivos de entrada.

---

## Ejecución

Tanto en Windows con Remote Desktop Connection como directamente en Ubuntu se pueden crear diversas terminales. En Windows se abre otra ventana del CMD y se crea la conexión SSH en cada ventana; en Ubuntu con Ctrl+Alt+T se crean nuevas ventanas.

| | Comando |
|---|---|
| **Ventana 1** | `roscore` |
| **Ventana 2** | `rosrun sphero_rvr_hw Atriz_rvr_node.py` |
| **Ventana 3** | `rosrun sphero_rvr rvr_joystick_control.py` |
| **Ventana 4** | `rosrun joy joy_node` |

- `roscore` — núcleo de ROS 1, inicia los servicios que permiten que los nodos se comuniquen.
- Ventana 2 — ejecuta el nodo `Atriz_rvr_node.py` del paquete `sphero_rvr_hw`.
- Ventana 3 — nodo de control por joystick del paquete `sphero_rvr`.
- Ventana 4 — `joy_node` lee el gamepad y publica en `/joy`.

Finalmente, al tener estas 4 ventanas o Nodos en ejecución se logrará teleoperar el Sphero RVR con un Joystick:
- Con el **Trigger derecho (RT)** se acelera
- Con el **Trigger izquierdo (LT)** se acelera en reversa
- Con la **palanca izquierda (LS)** se gira el robot en su propio eje, hacia la derecha o la izquierda

> 🔴 **AUDITORÍA — los nombres de paquete de este apartado ya no existen.**
> Los paquetes reales del workspace son `atriz_rvr_driver`, `atriz_rvr_msgs` y
> `atriz_rvr_serial`. `sphero_rvr_hw` y `sphero_rvr` son los nombres **anteriores
> al rename**. Los comandos, tal como están escritos, **fallan**. Los correctos:
> ```bash
> rosrun atriz_rvr_driver Atriz_rvr_node.py
> rosrun atriz_rvr_driver rvr_joystick_control.py
> ```
> (existe `start_ros.sh` en la raíz del repo, que hace esto mismo con un `sleep 5`
> tras lanzar `roscore` en segundo plano).
>
> **Además: nada de esto arranca solo.** No hay ninguna unidad systemd en
> `/etc/systemd/system/` que lance el robot; hay que abrir cuatro terminales a
> mano en cada arranque. Con 16 robots es inviable. El propio manual lo reconoce
> como pendiente ("Automatización de inicio del start_ros_sh"), y es justo lo que
> resuelve la Fase 1 del plan de migración.
>
> ✅ **RESUELTO el 2026-07-31**, ya en ROS 2: `atriz-robot.service` levanta el robot al
> encender, probado con un reinicio real. Ver el manual de migración, cap. 17. Este párrafo
> describe el sistema **Noetic**, y se conserva como tal.

---

## Conexión física

Ya instalados todos los paquetes podemos realizar la conexión serial entre el Sphero RVR y la Raspberry Pi. Para esto necesitamos **3 jumpers** y cable de alimentación USB para conectar el **GND**, **TX** y **RX**, y la alimentación de la Raspberry.

*Conexión de los Jumpers entre Raspberry pi y Sphero RVR*
*Conexión de los Jumpers a GND, RX y TX*
*Ajuste de la Raspberry pi al cover del Sphero*

Finalmente se conecta el cable de alimentación entre USB Sphero RVR y USB-C a la Raspberry pi, se abre el puerto lateral izquierdo y se inserta la batería.

*Apertura del puerto de la batería*
*Instalación de la batería*

> ℹ️ **AUDITORÍA — recordatorio de cableado.** TX y RX van **cruzados**:
> TX de la Pi (GPIO14, pin 8) → RX del RVR, y RX de la Pi (GPIO15, pin 10) → TX
> del RVR. GND común es obligatorio. Este detalle **solo aparece en las imágenes**
> del manual, no en el texto — conviene escribirlo explícitamente en el manual
> nuevo, porque es el error de montaje más común y el más difícil de diagnosticar.

---

## Sección final del original — lista de pendientes

Estos ocho puntos aparecen al final del documento **sin desarrollar**, como índice de trabajo futuro:

- Manual de la app Web
- Automatización de inicio del `start_ros_sh`
- Tutorial de esto - Configurar ip Estaticas
- Y del Ylidar
- Configuración del Lydar tracking
- Recuperación de todo el código de la web
- Calcular estadísticas a partir del acceso al Sphero
- Base 3D para la raspberry pi y el lydar

> 🔴 **AUDITORÍA — esta lista explica el estado actual del sistema.** Los cuatro
> primeros puntos son exactamente los que hoy están rotos o ausentes:
>
> | Pendiente del manual | Estado verificado en julio 2026 |
> |---|---|
> | Automatización de arranque | **No existe.** Ninguna unidad systemd propia |
> | IPs estáticas | **No configuradas.** IP por DHCP (192.168.1.200) |
> | YDLIDAR | **El driver no está instalado.** `ydlidar_ros_driver` y `YDLidar-SDK` no existen en el sistema, pese a que 3 launch files y `LIDAR_INTEGRATION_SUMMARY.md` los dan por instalados. Los launch **fallan** |
> | Lidar tracking | Sin integrar: el árbol TF está partido (`base_link` vs `rvr_base_link`), no hay URDF, no hay SLAM |
> | App web | Existe (`Atriz_web_server`) pero controla los robots por SSH con contraseña en texto plano y sin telemetría en streaming |

---

## Nota de seguridad

La contraseña real del usuario `sphero` aparece **tres veces** en el `.docx` original
y está además **commiteada en texto plano** en el repositorio **público**
`Bura-hub/Atriz_web_server` (`swarm_lab_api/app/core/raspberry_config.py`), junto con
las IPs de dos Raspberry Pi.

**Debe considerarse comprometida y rotarse.** Ver §5.1 del plan de migración.

En esta transcripción está redactada como `«CONTRASEÑA»`. El `.docx` original la
conserva — es una de las razones por las que este repositorio debería ser **privado**.

---

## Veredicto sobre el manual

Es un documento **cuidado y didáctico**: explica cada comando, no solo lo lista, e
incluye 40 capturas. Acierta en lo esencial (Ubuntu Server, liberar la consola serie,
`dialout`, la conexión física). Sus problemas son de dos tipos:

**Una laguna técnica con consecuencias reales:** no configurar `config.txt` deja el
RVR sobre el mini-UART, lo que produce fallos intermitentes difíciles de atribuir.

**Deriva respecto al código:** los nombres de paquete cambiaron y el manual no. Los
comandos de ejecución, tal como están escritos, ya no funcionan.

El manual nuevo (`MANUAL_ATRIZ_ROS2.md`) hereda su estructura y su tono explicativo,
corrige la laguna del UART, y añade lo que aquí quedó como lista de pendientes.
