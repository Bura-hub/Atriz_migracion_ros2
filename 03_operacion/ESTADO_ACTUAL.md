# Estado actual

Fichero corto, para situarse en un minuto. **Es el canal de contexto entre el Claude del PC y el de
la Pi**, y el único que sobrevive cuando Claude Code se desinstale del robot.

`CLAUDE.md` son 107 KB (~26.800 tokens) y `TRASPASO.md` otros 72 KB: eso es para el detalle. Esto es
para saber por dónde vas.

> **Regla:** si algo importa y solo vive en un hilo de Claude, en `memory/` o en un transcripto,
> **no existe**. Se pierde al desinstalar. Lo que importe, aquí o en el repositorio.

---

**Última actualización:** 2026-08-03

## En qué estamos

Cerrado hoy: la **alineación del robot con los repositorios** (0 fallos en `verificar_robot.sh`) y
el **canal Claude↔Claude PC↔robot**, verificado de extremo a extremo dentro de la Pi.

## Lo siguiente

1. 👤 **Claves SSH desde el PC.** `~/.ssh/authorized_keys` está vacío: hoy entras con contraseña, y
   con eso **ningún canal automático funciona** — se cuelga esperándola. Es el único bloqueo real
   del canal. Ver `PC_Y_ROBOT.md` §1.
2. **Repetir el encargo por SSH** desde el PC. Todo se ha probado *en* la Pi; falta la trampa del
   `bash -lc`, que sin `-l` deja al delegado en el dominio DDS 0 viendo el robot muerto.
3. **La web** (Fase 5): cerrar rosbridge y rehacerla. El transporte ya está verificado.
4. **La imagen dorada y el robot 2** (Fase 6): ahí se comprueban por primera vez `provision.sh`
   entero y el parser de `robot_id.txt` con un ID distinto de 01.

## Lo que bloquea, y de quién es

| | |
|---|---|
| 🔐 **Rotar la PSK del WiFi y la contraseña de `sphero`** | 👤 tuyo. La credencial está en el historial de un repositorio público |
| **`red.txt` en 755** | 👤 tuyo. La PSK es legible por cualquier usuario; `chmod` no sirve, va `fmask=0177` en `/etc/fstab` |
| **El mapa del aula** | 👤 tuyo, en el laboratorio. Bloquea la tarea 4 del plan de navegación |
| **`~/.ssh/authorized_keys` vacío** | 👤 tuyo, desde el PC |

## Marcado NO VERIFICADO

- **`provision.sh` no se ha recorrido entero en ningún robot.** El SDK de rvr-01 se compiló a mano
  (md5 idéntico al de `src_externos`, y `~/YDLidar-SDK` no existe).
- **El parser de `robot_id.txt`** no se puede probar con `ROBOT_ID=01`: los dos parsers coinciden por
  casualidad.
- **El encargo por SSH desde el PC** — probado solo dentro de la Pi.
- **`atriz-nav.service`** nunca se ha arrancado bajo systemd: exige un mapa.
- **Las diez prácticas** de `estudiantes/` no se han ejecutado con el robot moviéndose.

## Suelto, sin dueño claro

- **`/ambient_light` no publica** (manual, cap. 18.4b). Intermitente: publicaba a las 14:30 del
  2026-08-03 y no a las 15:41, con `/odom` a 16,7 Hz y `/encoders` a 16,3 Hz sanos.
