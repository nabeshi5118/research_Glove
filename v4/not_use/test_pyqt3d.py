import socket
import struct
import sys
import time

import cv2
import numpy as np
import pyqtgraph.opengl as gl
from ahrs.filters import Madgwick
from PyQt5 import QtWidgets
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QMatrix4x4, QPixmap
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow
from pyqtgraph.opengl import GLMeshItem, GLViewWidget
from stl import mesh  # numpy-stlを使用

# Constants
UDP_PORT = 31415
POLL_INTERVAL_MS = 10
UI_REFRESH_MS = 40
# BMI270 default accel scale for ±2g: 16384 LSB/g
ACCEL_SCALE = 16384.0
N = 100


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("PyQt with 3D Model")
        self.setGeometry(100, 100, 800, 600)

        # UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', UDP_PORT))
        self.sock.setblocking(False)

        # Initialize quaternion values
        self.quaternion = np.array([1.0, 0.0, 0.0, 0.0])
        self.ahrs = Madgwick(sampleperiod=UI_REFRESH_MS / 1000)

        self.gyro_bias = np.zeros(3)
        self.calib_count = 0
        self.calib_accum = np.zeros(3)

        self.last_ts = time.time()

        self.widget = gl.GLViewWidget(self)
        self.widget.setCameraPosition(distance=4000)  # カメラの距離を調整
        self.widget.setGeometry(0, 0, 800, 600)
        self.widget.show()

        self.model = self.createModel("teamugstl.stl")
        self.widget.addItem(self.model)

        # Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_orientation)
        self.timer.start(40)  # 25fps

        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self.poll_udp)
        self.poll_timer.start(POLL_INTERVAL_MS)

    def poll_udp(self):
        try:
            packet, _ = self.sock.recvfrom(65535)
        except BlockingIOError:
            return

        # madgwick = Madgwick(sampleperiod=4 / 100)  #初期化するサンプリング周期

        # Assuming packet: header then 9 int16 values little-endian
        sensor_count = packet[3]
        sensor_block_size = sensor_count * 4  # 仮に1センサー = float(4バイト)

        offset = 10 + sensor_block_size
        raw = struct.unpack_from('<9f', packet, offset)
        raw_np = np.array(raw, dtype=np.float32)

        # print("Unpacked data:", raw)  # ここで展開結果を確認

        # バイアスキャリブレーション
        if self.calib_count < N:
            self.gyro_bias += np.radians(raw_np[3:6])
            self.calib_count += 1
            if self.calib_count == N:
                self.gyro_bias /= N
            return

        # magnet indices 0,1,2
        # gyro indices 3,4,5
        # accel indices 6,7,8
        # mx, my, mz = raw_np[0:3]
        gx, gy, gz = np.radians(raw_np[3:6]) - self.gyro_bias
        ax, ay, az = raw_np[6:9] / ACCEL_SCALE

        print(f"Unpacked data: {gx}, {gy}, {gz}")

        # mx, my, mz = np.array([raw[0], raw[1], raw[2]])
        # gx, gy, gz = np.radians([raw[3], raw[4], raw[5]])
        # ax, ay, az = [raw[i] / ACCEL_SCALE for i in (6, 7, 8)]

        # # Convert to g
        # self.accel_x = raw_ax / ACCEL_SCALE
        # self.accel_y = raw_ay / ACCEL_SCALE
        # self.accel_z = raw_az / ACCEL_SCALE

        now = time.time()
        dt = now - self.last_ts
        self.ahrs.sampleperiod = dt
        self.last_ts = now

        # self.quaternion = self.ahrs.updateMARG(gyr=[gx, gy, gz],
        #                                        acc=[ax, ay, az],
        #                                        mag=[mx, my, mz],
        #                                        q=self.quaternion)

        self.quaternion = self.ahrs.updateIMU(gyr=[gx, gy, gz], acc=[ax, ay, az], q=self.quaternion)

        self.quaternion /= np.linalg.norm(self.quaternion)
        # self.quaternion = Madgwick.updateIMU(gyr=[gx, gy, gz], acc=[ax, ay, az], mag=[mx, my, mz])

    def createModel(self, model_path):
        # STLファイルの読み込みと3Dモデルの作成
        your_mesh = mesh.Mesh.from_file(model_path)  # STLファイルパス
        vertices = np.array(your_mesh.vectors, dtype=np.float32)
        faces = np.arange(vertices.shape[0] * 3, dtype=np.uint32).reshape(vertices.shape[0], 3)
        model = gl.GLMeshItem(vertexes=vertices.reshape(-1, 3),
                              faces=faces,
                              smooth=False,
                              color=(1, 1, 1, 1),
                              shader="shaded")

        return model

    def update_orientation(self):
        """
            IMU からクォータニオン取得する。
            IMU からの読み出しロジックに置き換える。
        """
        # q_w, q_x, q_y, q_z = self.get_imu_quaternion()
        q_w, q_x, q_y, q_z = self.quaternion

        # クォータニオン -> 4x4 行列
        qmat = QMatrix4x4(1 - 2 * q_y * q_y - 2 * q_z * q_z, 2 * q_x * q_y - 2 * q_w * q_z,
                          2 * q_x * q_z + 2 * q_w * q_y, 0, 2 * q_x * q_y + 2 * q_w * q_z,
                          1 - 2 * q_x * q_x - 2 * q_z * q_z, 2 * q_y * q_z - 2 * q_w * q_x, 0,
                          2 * q_x * q_z - 2 * q_w * q_y, 2 * q_y * q_z + 2 * q_w * q_x,
                          1 - 2 * q_x * q_x - 2 * q_y * q_y, 0, 0, 0, 0, 1)

        self.model.setTransform(qmat)

    def get_imu_quaternion(self):
        # ダミー：正面向き
        return (1.0, 0.0, 0.0, 0.0)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
