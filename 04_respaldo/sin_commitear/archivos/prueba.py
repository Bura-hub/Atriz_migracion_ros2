#!/usr/bin/env python3
# -- coding: utf-8 --

import rospy
from geometry_msgs.msg import Twist
from atriz_rvr_msgs.msg import Color
import time

class SimpleLineFollower:
    def _init_(self):
        rospy.init_node("simple_line_follower")
        self.pub = rospy.Publisher("/cmd_vel", Twist, queue_size=1)
        rospy.Subscriber("/color_sensor_left", Color, self.left_callback)
        rospy.Subscriber("/color_sensor_right", Color, self.right_callback)
        self.twist = Twist()

        # Colores actuales
        self.left_color = None
        self.right_color = None

        # Estado del seguidor
        self.last_seen = "center"  # "left", "right", "center"
        self.line_detected = False

        self.rate = rospy.Rate(20)
        self.run()

    def left_callback(self, msg):
        self.left_color = (msg.r, msg.g, msg.b)

    def right_callback(self, msg):
        self.right_color = (msg.r, msg.g, msg.b)

    def luminance(self, r, g, b):
        # Calcular luminancia percibida
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    def detect_line(self, color):
        if color is None:
            return False
        Y = self.luminance(*color)
        return Y < 40  # umbral típico para línea negra

    def run(self):
        while not rospy.is_shutdown():
            if self.left_color is None or self.right_color is None:
                self.rate.sleep()
                continue

            left_line = self.detect_line(self.left_color)
            right_line = self.detect_line(self.right_color)

            # Ambos sensores ven negro → avanzar recto
            if left_line and right_line:
                self.twist.linear.x = 0.25
                self.twist.angular.z = 0.0
                self.last_seen = "center"
                self.line_detected = True

            # Solo el izquierdo ve negro → girar suave izquierda
            elif left_line:
                self.twist.linear.x = 0.18
                self.twist.angular.z = 0.3
                self.last_seen = "left"
                self.line_detected = True

            # Solo el derecho ve negro → girar suave derecha
            elif right_line:
                self.twist.linear.x = 0.18
                self.twist.angular.z = -0.3
                self.last_seen = "right"
                self.line_detected = True

            # Ninguno ve línea → búsqueda con avance suave
            else:
                self.line_detected = False
                self.twist.linear.x = 0.10  # avanza lentamente
                if self.last_seen == "left":
                    self.twist.angular.z = 0.35  # busca hacia la izquierda
                elif self.last_seen == "right":
                    self.twist.angular.z = -0.35  # busca hacia la derecha
                else:
                    # si nunca ha visto línea, gira ligeramente a la izquierda
                    self.twist.angular.z = 0.25

            self.pub.publish(self.twist)
            self.rate.sleep()

if _name_ == "_main_":
    try:
        SimpleLineFollower()
    except rospy.ROSInterruptException:
        pass