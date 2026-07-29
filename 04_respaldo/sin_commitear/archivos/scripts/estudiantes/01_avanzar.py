#!/usr/bin/env python3
import rospy
from geometry_msgs.msg import Twist
from atriz_rvr_msgs.msg import Color
from std_srvs.srv import SetBool
import signal, sys

class SeguidorBordeRojo:
    def __init__(self):
        rospy.init_node('seguidor_borde_rojo')
        self.pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
        rospy.Subscriber('/color', Color, self.color_callback)
        rospy.wait_for_service('/enable_color')
        activar = rospy.ServiceProxy('/enable_color', SetBool)
        activar(True)
        signal.signal(signal.SIGINT, self.detener)
        
        self.en_rojo = False
        self.sentido_giro = 1  # 1 = izquierda, -1 = derecha
        self.tiempo_sin_rojo = 0
        rospy.sleep(1)
        rospy.loginfo("🤖 Seguidor del borde rojo (versión rápida) listo!")

    def color_callback(self, msg):
        r, g, b = [int(c) for c in msg.rgb_color]
        # Ajusta estos valores según tu entorno
        if r > 120 and g < 90 and b < 90:
            self.en_rojo = True
            self.tiempo_sin_rojo = 0
        else:
            self.en_rojo = False
            self.tiempo_sin_rojo += 1

    def mover(self):
        rate = rospy.Rate(10)
        while not rospy.is_shutdown():
            cmd = Twist()

            if self.en_rojo:
                # 💨 Aumentamos un poco la velocidad lineal
                cmd.linear.x = 0.22   # antes 0.18
                cmd.angular.z = 0.0
            else:
                # 🔄 Gira suavemente más rápido para encontrar el borde
                cmd.linear.x = 0.0
                cmd.angular.z = 0.32 * self.sentido_giro  # antes 0.25

                # Si pasa mucho tiempo sin ver rojo, cambia dirección
                if self.tiempo_sin_rojo > 25:
                    self.sentido_giro *= -1
                    self.tiempo_sin_rojo = 0
                    rospy.loginfo("🔁 Cambiando dirección de búsqueda")

            self.pub.publish(cmd)
            rate.sleep()

    def detener(self, *args):
        cmd = Twist()
        for _ in range(5):
            self.pub.publish(cmd)
            rospy.sleep(0.1)
        sys.exit(0)

if __name__ == "__main__":
    seguidor = SeguidorBordeRojo()
    seguidor.mover()
