#!/usr/bin/env python3
"""vigia_dds.py — ¿cruza DDS en este robot? Y si no, UN reinicio y solo uno.

Existe por la evidencia 109: rvr-01 puede nacer MUDO en DDS tras un arranque
en frío —driver vivo, RVR hablando, y ni un mensaje cruzando ni en la propia
Pi— con las esperas de red y reloj CUMPLIDAS. Es intermitente (2 de 3
arranques fríos con salto grande de reloj), la causa próxima no se conoce, y
el remedio medido (2 de 2) es reiniciar el stack con el reloj ya bueno.

CÓMO DECIDE (lógica pura en `decidir()`, con tests en scripts/pruebas/):

    ¿llegó un mensaje de /estado_robot en el plazo?
      sí               → SANO (y la marca, si existe, SE QUEDA — ver abajo)
      no, sin marca    → REINICIAR: deja la marca y manda SIGINT al proceso
                         principal de atriz-robot; `Restart=always` hace el
                         resto. Una sola vez por arranque.
      no, con marca    → RENDIRSE: fallo ABIERTO. Se queda corriendo y se
                         escribe a gritos en el journal.

POR QUÉ SIGINT AL PROCESO Y NO `systemctl restart`:
  El vigía corre como `sphero` (ExecStartPost de atriz-robot, sin `+`) y la
  regla de polkit 49-atriz-unidades SOLO concede start|stop de slam/nav — a
  propósito, y no se amplía por esto. Pero `sphero` ES el dueño del proceso:
  un SIGINT al MainPID (que es `ros2 launch`, el wrapper hace exec) produce
  el MISMO cierre limpio que un stop de systemd (KillSignal=SIGINT) y
  `Restart=always` —ejercitado en la F0— levanta el stack de cero.

POR QUÉ LA MARCA NO SE REARMA TRAS UNA CURA:
  StartLimitBurst=5/300 s en atriz-robot. Un ping-pong mudo→cura→mudo con
  rearme quemaría el presupuesto y convertiría un robot mudo en uno MUERTO.
  La marca vive en /run/atriz (RuntimeDirectory con Preserve): sobrevive a
  los reinicios de la unidad y desaparece sola al reiniciar la Pi.

VERIFICACIÓN (evidencia 113):
  La rama sana y la forzada se prueban con ATRIZ_VIGIA_FORZAR_MUDO=1; la
  detección REAL solo la validará el próximo mudo de verdad — es
  intermitente y no se sabe provocar. Queda escrito, no prometido.
"""
import os
import sys
import time

MARCA = '/run/atriz/vigia-dds.reinicio'
TOPIC = 'estado_robot'          # 1 Hz, el canal barato (evidencia 110)
PLAZO_S = float(os.environ.get('ATRIZ_VIGIA_PLAZO_S', '90'))

SANO, REINICIAR, RENDIRSE = 'SANO', 'REINICIAR', 'RENDIRSE'


def decidir(mensaje_llego: bool, marca_existe: bool) -> str:
    """Pura, sin ROS ni disco: la política del vigía en cuatro casos."""
    if mensaje_llego:
        return SANO
    return RENDIRSE if marca_existe else REINICIAR


def esperar_mensaje(plazo_s: float) -> float | None:
    """Segundos hasta el primer /estado_robot, o None si no llegó.

    BEST_EFFORT + VOLATILE: empareja con el RELIABLE + TRANSIENT_LOCAL del
    publicador (lo pedido ≤ lo ofrecido). En el estado mudo medido, ni un
    suscriptor local recibe nada — por eso esto lo detecta desde dentro.
    """
    if os.environ.get('ATRIZ_VIGIA_FORZAR_MUDO') == '1':
        return None
    import rclpy
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.node import Node
    from rclpy.qos import QoSProfile, QoSReliabilityPolicy
    from atriz_rvr_msgs.msg import EstadoRobot

    rclpy.init()
    try:
        nodo = Node('vigia_dds')
        llego = []
        nodo.create_subscription(
            EstadoRobot, TOPIC, lambda _m: llego.append(True),
            QoSProfile(depth=1,
                       reliability=QoSReliabilityPolicy.BEST_EFFORT))
        ex = SingleThreadedExecutor()
        ex.add_node(nodo)
        t0 = time.monotonic()
        while time.monotonic() - t0 < plazo_s:
            ex.spin_once(timeout_sec=0.5)
            if llego:
                return time.monotonic() - t0
        return None
    finally:
        rclpy.shutdown()


def pid_principal() -> int:
    import subprocess
    r = subprocess.run(['systemctl', 'show', 'atriz-robot', '-p', 'MainPID'],
                       capture_output=True, text=True, timeout=10)
    return int(r.stdout.strip().split('=')[1])


def main() -> int:
    t = esperar_mensaje(PLAZO_S)
    veredicto = decidir(t is not None, os.path.isfile(MARCA))

    if veredicto == SANO:
        print(f'[vigia-dds] ✓ DDS cruza: /{TOPIC} a los {t:.1f} s')
        return 0

    if veredicto == RENDIRSE:
        print(f'[vigia-dds] 🔴🔴 SIGUE MUDO tras un reinicio automático: '
              f'sin /{TOPIC} en {PLAZO_S:.0f} s y la marca {MARCA} ya '
              f'existe. NO se reinicia otra vez (fallo abierto). '
              f'Diagnóstico: bash ~/atriz_migracion/scripts/'
              f'diagnosticar_mudo.sh · remedio: sudo systemctl restart '
              f'atriz-robot')
        return 0

    # REINICIAR: la marca ANTES del disparo — si algo falla a mitad, el
    # peor caso es no reintentar, nunca reintentar en bucle.
    try:
        with open(MARCA, 'w') as f:
            f.write(time.strftime('%Y-%m-%dT%H:%M:%S%z\n'))
    except OSError as e:
        print(f'[vigia-dds] 🔴 sin /{TOPIC} en {PLAZO_S:.0f} s pero NO puedo '
              f'escribir la marca ({e}): no reinicio — sin marca no hay '
              f'garantía de una-sola-vez')
        return 0
    try:
        pid = pid_principal()
        print(f'[vigia-dds] 🔴 MUDO: sin /{TOPIC} en {PLAZO_S:.0f} s. '
              f'SIGINT al PID principal {pid}; Restart=always lo levanta '
              f'(evidencia 109/113). No habrá segundo intento este arranque.')
        os.kill(pid, 2)          # SIGINT = el cierre limpio del propio unit
    except (OSError, ValueError, IndexError) as e:
        print(f'[vigia-dds] 🔴 no pude señalar el proceso principal: {e}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
