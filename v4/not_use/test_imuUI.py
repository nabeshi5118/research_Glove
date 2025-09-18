import socket
import struct
import sys

import numpy as np
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QBrush, QColor, QPainter
from PyQt5.QtWidgets import (QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget)

# Constants
UDP_PORT = 31415
POLL_INTERVAL_MS = 10
UI_REFRESH_MS = 40
# BMI270 default accel scale for ±2g: 16384 LSB/g
ACCEL_SCALE = 16384.0


class BubbleLevelWidget(QWidget):
    """
    Simple bubble level: draws a circle and a smaller bubble that moves
    according to roll (x-axis tilt) and pitch (y-axis tilt).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.roll = 0.0
        self.pitch = 0.0

    def set_tilt(self, roll: float, pitch: float):
        self.roll = roll
        self.pitch = pitch
        self.update()

    def paintEvent(self, event):
        side = min(self.width(), self.height())
        radius = side * 0.45
        bubble_radius = radius * 0.2

        max_offset = radius - bubble_radius
        dx = np.sin(self.roll) * max_offset
        dy = -np.sin(self.pitch) * max_offset

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        x0 = int((self.width() - side) / 2)
        y0 = int((self.height() - side) / 2)
        diameter = int(side)
        painter.setBrush(QBrush(QColor(200, 200, 200)))
        painter.drawEllipse(x0, y0, diameter, diameter)

        painter.setBrush(QBrush(QColor(100, 220, 100)))
        cx = int(self.width() / 2 + dx)
        cy = int(self.height() / 2 + dy)
        br = int(bubble_radius)
        painter.drawEllipse(cx - br, cy - br, br * 2, br * 2)


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle('IMU Bubble Level')

        # UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', UDP_PORT))
        self.sock.setblocking(False)

        # Initialize accelerometer values (m/s²)
        self.accel_x = 0.0
        self.accel_y = 0.0
        self.accel_z = 9.81

        # UI
        self.bubble = BubbleLevelWidget()
        self.status_label = QLabel('Accel (g): 0.00, 0.00, 1.00')
        layout = QVBoxLayout()
        layout.addWidget(self.bubble)
        layout.addWidget(self.status_label)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Timers
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self.poll_udp)
        self.poll_timer.start(POLL_INTERVAL_MS)

        self.ui_timer = QTimer()
        self.ui_timer.timeout.connect(self.refresh_ui)
        self.ui_timer.start(UI_REFRESH_MS)

    def poll_udp(self):
        try:
            packet, _ = self.sock.recvfrom(65535)
        except BlockingIOError:
            return
        # Assuming packet: header then 9 int16 values little-endian
        sensor_count = packet[3]
        sensor_block_size = sensor_count * 4  # 仮に1センサー = float(4バイト)

        offset = 10 + sensor_block_size
        raw = struct.unpack_from('<9f', packet, offset)

        print("Unpacked data:", raw)  # ここで展開結果を確認

        # accel indices 6,7,8
        raw_ax, raw_ay, raw_az = raw[6], raw[7], raw[8]
        # Convert to g
        self.accel_x = raw_ax / ACCEL_SCALE
        self.accel_y = raw_ay / ACCEL_SCALE
        self.accel_z = raw_az / ACCEL_SCALE

    def refresh_ui(self):
        # Compute roll and pitch (radians)
        roll = np.arctan2(self.accel_y, self.accel_z)
        pitch = np.arctan2(-self.accel_x, np.sqrt(self.accel_y**2 + self.accel_z**2))
        self.bubble.set_tilt(roll, pitch)
        # Update status label in g
        self.status_label.setText(
            f"Accel (g): {self.accel_x:.5f}, {self.accel_y:.5f}, {self.accel_z:.5f}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = MainWindow()
    w.resize(400, 450)
    w.show()
    sys.exit(app.exec_())
