from __future__ import annotations
"""
test_v4.py – Integrated Pressure & IMU Visualiser (v4)
=====================================================

Realtime UDP viewer for G-CU armband combining:
  • Heat-map of an 11×11 pressure array (stretch 2)
  • 3-D STL model orientation via Madgwick filter (stretch 1)
  • Circular bubble-level for roll/pitch (stretch 1)

Changes since v3
----------------
* Expanded sensor grid from 10×9 to 11×11.
* Dynamic Madgwick sample period update based on actual polling interval.
* Toggleable magnetometer support in orientation filter.
* Median-based offset correction with configurable reference MV.
* CSV logging of both raw and offset-corrected frames.
* Live color-scale adjustment via Min/Max spinboxes.
* Refactored layout using Qt splitters for flexible resizing.

Key Features
------------
* Interactive heat-map with adjustable colorbar.
* Real-time 3D model rendering using PyQtGraph.opengl.
* Bubble-level widget driven by roll/pitch angles.
* Offset-correction learning phase with progress status.
* Start/Stop streaming and recording controls.

Usage
-----
$ python test_v4.py
→ Stream G-CU UDP packets to port 31415 (see README for protocol details).
"""

import csv
import math
import os
import signal
import socket
import struct
import sys
import time
from datetime import datetime

import numpy as np
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from ahrs.filters import Madgwick
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QBrush, QColor, QMatrix4x4, QPainter
from PyQt5.QtWidgets import (QApplication, QCheckBox, QDoubleSpinBox, QHBoxLayout, QLabel,
                             QMainWindow, QMessageBox, QPushButton, QVBoxLayout, QWidget)
from stl import mesh

# ---------------------------- Protocol constants ---------------------------- #
START_MAKER: int = 0x5A
END_MAKER: int = 0xA5
UDP_PORT: int = 31415

# --------------------------- Visualisation settings ------------------------- #
ROWS: int = 11
COLS: int = 11
POLL_INTERVAL_MS: int = 10
REFRESH_INTERVAL_MS: int = 40

# --------------------------- Offset‑correction ------------------------------ #
OFFSET_SAMPLES: int = 100  # number of frames to average for the offset
OFFSET_REFERENCE_MV: float = 330.0  # baseline sensor output

# --------------------------- IMU sensor settings --------------------------- #
ACCEL_SCALE: float = 16384.0
IMU_CALIB_SAMPLES: int = 100
IMUBYTES: int = 9 * 4
USING_MAGNET = False  # set True to enable magnetometer in orientation filter

# --------------------------------------------------------------------------- #
#                               Bubble‑level widget                           #
# --------------------------------------------------------------------------- #


class BubbleLevelWidget(QtWidgets.QWidget):
    """Circular bubble‑level indicator driven by roll/pitch."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.roll = 0.0  # rad, rotation around X (pitch toward left/right)
        self.pitch = 0.0  # rad, rotation around Y (nose up/down)

    def set_tilt(self, roll: float, pitch: float) -> None:
        self.roll = roll
        self.pitch = pitch
        self.update()

    # ------------------------------------------------------------------ #
    #                           Painting                                 #
    # ------------------------------------------------------------------ #

    def paintEvent(self, _event):  # noqa: N802 (Qt API)
        side = min(self.width(), self.height())
        radius = side * 0.45
        bubble_radius = radius * 0.2

        max_offset = radius - bubble_radius
        dx = np.sin(self.roll) * max_offset
        dy = -np.sin(self.pitch) * max_offset

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # housing
        x0 = int((self.width() - side) / 2)
        y0 = int((self.height() - side) / 2)
        diameter = int(side)
        painter.setBrush(QColor("#2ECC71"))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawEllipse(x0, y0, diameter, diameter)

        # bubble
        painter.setBrush(QColor("#1A237E"))
        cx = int(self.width() / 2 + dx)
        cy = int(self.height() / 2 + dy)
        br = int(bubble_radius)
        painter.drawEllipse(cx - br, cy - br, br * 2, br * 2)


# --------------------------------------------------------------------------- #
#                               Packet decoding                               #
# --------------------------------------------------------------------------- #


def decode_packet(packet: bytes):
    """Decode a G‑CU packet and return (ts, grid, magnet, gyro, accel)."""
    if len(packet) < 10 or packet[0] != START_MAKER or packet[1] != START_MAKER:
        return None
    # timestamp (little‑endian: 4‑byte seconds + 2‑byte millis)
    secs = struct.unpack_from('<I', packet, 4)[0]
    ms = struct.unpack_from('<H', packet, 8)[0]
    ts_str = datetime.fromtimestamp(secs + ms / 1000.0).strftime('%H:%M:%S.%f')

    # pressure block (sensor_cnt × 4‑byte ints)
    sensor_cnt = packet[3]
    pos = 10
    values: list[int] = []
    for _ in range(sensor_cnt):
        if pos + 4 > len(packet):
            break
        values.append(struct.unpack_from('<I', packet, pos)[0])
        pos += 4
    if not values:
        return None

    flat = np.zeros(sensor_cnt, dtype=np.float32)
    per = len(flat) // len(values)
    for idx, v in enumerate(values):
        flat[idx * per:(idx + 1) * per] = v
    grid = flat.reshape(ROWS, COLS)

    # IMU block (9 × float32)
    magnet = None
    gyro = None
    accel = None
    if pos + IMUBYTES <= len(packet):
        raw = struct.unpack_from('<9f', packet, pos)
        if USING_MAGNET:
            magnet = raw[0:3]
        gyro = np.radians(raw[3:6])
        accel = np.array(raw[6:9], dtype=np.float32) / ACCEL_SCALE
    return ts_str, grid, magnet, gyro, accel


# --------------------------------------------------------------------------- #
#                                    GUI                                      #
# --------------------------------------------------------------------------- #


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Integrated Pressure & IMU Viewer')
        self.resize(1200, 650)

        # ---------------------- Runtime data ------------------------------ #
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', UDP_PORT))
        self.sock.setblocking(False)

        # ---------------------- Data storage ------------------------------ #
        self._pressure = np.zeros((ROWS, COLS), dtype=np.float32)
        self._levels = (0.0, 3000.0)
        self._offset_enabled = False
        self._offset_ready = False
        self._offset_accum: list[np.ndarray] = []
        self._offset_baseline: np.ndarray | None = None
        self._recording = False
        self._log_handle: csv.FileWriter | None = None
        self._log_writer: csv.writer | None = None

        # ---------------------- IMU filter ------------------------------ #
        self.ahrs = Madgwick(beta=0.3, sampleperiod=REFRESH_INTERVAL_MS / 1000)
        self.quaternion = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
        self._imu_calib_cnt = 0
        self._gyro_bias = np.zeros(3)
        self.last_ts = time.time()

        # accel (g‑units) for bubble‑level
        self.accel_x = 0.0
        self.accel_y = 0.0
        self.accel_z = 1.0

        # ---------------------- Build UI ------------------------------ #
        self._build_view()
        self._build_controls()
        self._compose_layout()

        # ---------------------- Timers ------------------------------ #
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.poll_udp)
        self.poll_timer.start(POLL_INTERVAL_MS)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.update_views)
        self.refresh_timer.start(REFRESH_INTERVAL_MS)

        # graceful Ctrl‑C
        signal.signal(signal.SIGINT, lambda *_: QApplication.quit())

    # ------------------------------------------------------------------ #
    #                           UI building                              #
    # ------------------------------------------------------------------ #

    def _build_view(self):
        # ---------------------- Heat‑map ------------------------------ #
        self.heatmap_widget = pg.GraphicsLayoutWidget()
        self.heatmap_widget.setBackground('w')
        plot = self.heatmap_widget.addPlot()
        plot.setLabel('left', 'Row')
        plot.setLabel('bottom', 'Col')
        self.image_item = pg.ImageItem()
        plot.addItem(self.image_item)
        cmap = pg.ColorMap(pos=np.array([0.0, 0.5, 1.0]),
                           color=[(0, 0, 255), (0, 255, 0), (255, 0, 0)])
        self.image_item.setLookupTable(cmap.getLookupTable())
        self.colorbar = pg.ColorBarItem(colorMap=cmap, values=self._levels, interactive=False)
        self.heatmap_widget.addItem(self.colorbar)
        self.colorbar.setImageItem(self.image_item)

        # ---------------------- 3‑D model ------------------------------ #
        self.model_widget = gl.GLViewWidget()
        self.model_widget.setCameraPosition(distance=4000)
        try:
            mesh_data = mesh.Mesh.from_file('teamugstl.stl')
            verts = np.array(mesh_data.vectors, dtype=np.float32).reshape(-1, 3)
            faces = np.arange(len(verts), dtype=np.uint32).reshape(-1, 3)
            self.mesh_item = gl.GLMeshItem(vertexes=verts,
                                           faces=faces,
                                           drawEdges=True,
                                           smooth=False,
                                           shader='shaded',
                                           color=(0.8, 0.8, 0.8, 1.0))
            self.model_widget.addItem(self.mesh_item)
        except FileNotFoundError:
            label = pg.LabelItem(text='teamugstl.stl not found')
            self.model_widget.addItem(label)

        # ---------------------- Bubble level ------------------------------ #
        self.bubble_widget = BubbleLevelWidget()

    def _build_controls(self):
        self.start_btn = QPushButton('Start Recv')
        self.start_btn.clicked.connect(self.start_receiving)
        self.stop_btn = QPushButton('Stop Recv')
        self.stop_btn.clicked.connect(self.stop_receiving)
        self.stop_btn.setEnabled(False)

        self.record_cb = QCheckBox('Record Pressure')
        self.record_cb.stateChanged.connect(self.toggle_recording)
        self.offset_cb = QCheckBox('Offset Corr')
        self.offset_cb.stateChanged.connect(self.toggle_offset)

        self.min_spin = QDoubleSpinBox()
        self.min_spin.setPrefix('Min: ')
        self.min_spin.setDecimals(1)
        self.min_spin.setRange(0.0, 1e6)
        self.min_spin.setValue(self._levels[0])
        self.min_spin.editingFinished.connect(self.update_levels)
        self.max_spin = QDoubleSpinBox()
        self.max_spin.setPrefix('Max: ')
        self.max_spin.setDecimals(1)
        self.max_spin.setRange(0.0, 1e6)
        self.max_spin.setValue(self._levels[1])
        self.max_spin.editingFinished.connect(self.update_levels)

        self.ctrl_layout = QHBoxLayout()
        for w in (self.start_btn, self.stop_btn, self.record_cb, self.offset_cb, self.min_spin,
                  self.max_spin):
            self.ctrl_layout.addWidget(w)

        self.status_label = QLabel('Idle')

    def _compose_layout(self):
        # Heatmap + ボタン類コンテナ
        left_container = QWidget()
        left_vbox = QVBoxLayout(left_container)
        left_vbox.setContentsMargins(0, 0, 0, 0)
        left_vbox.setSpacing(2)
        left_vbox.addWidget(self.heatmap_widget)
        left_vbox.addLayout(self.ctrl_layout)

        # 3D + Bubbleコンテナ
        right_split = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        right_split.addWidget(self.model_widget)
        right_split.addWidget(self.bubble_widget)
        self.model_widget.setMinimumWidth(200)
        self.bubble_widget.setMinimumWidth(200)
        right_split.setStretchFactor(0, 1)  # model : bubble = 1:1
        right_split.setStretchFactor(1, 1)

        main_split = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        main_split.addWidget(left_container)  # left
        main_split.addWidget(right_split)
        main_split.setStretchFactor(0, 2)  # heatmap : right = 2:1
        main_split.setStretchFactor(1, 1)

        central = QWidget()
        vbox = QVBoxLayout(central)
        vbox.setContentsMargins(4, 4, 4, 4)
        vbox.setSpacing(4)
        vbox.addWidget(main_split)
        vbox.addWidget(self.status_label)
        self.setCentralWidget(central)

    # ------------------------------------------------------------------ #
    #                           Networking                               #
    # ------------------------------------------------------------------ #

    def start_receiving(self):
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText('Receiving…')
        self._receiving = True

    def stop_receiving(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText('Stopped')
        self._receiving = False
        if self._log_handle:
            self._log_handle.close()
            self._log_handle = None

    # ------------------------------------------------------------------ #
    #                           Callbacks                                #
    # ------------------------------------------------------------------ #

    def toggle_recording(self, state: int):
        self._recording = bool(state)
        if self._recording:
            os.makedirs('log', exist_ok=True)
            fname = datetime.now().strftime('%Y%m%d_%H%M%S') + '.csv'
            self._log_handle = open(os.path.join('log', fname), 'w', newline='')
            self._log_writer = csv.writer(self._log_handle)
            self._log_writer.writerow(['time'] + [f'p{i}' for i in range(ROWS * COLS)])
        elif self._log_handle:
            self._log_handle.close()
            self._log_handle = None

    def toggle_offset(self, state: int):
        self._offset_enabled = bool(state)
        self._offset_ready = False
        self._offset_accum.clear()
        self.status_label.setText('Offset Enabled' if self._offset_enabled else 'Offset Disabled')

    def update_levels(self):
        vmin = self.min_spin.value()
        vmax = self.max_spin.value()
        if vmax <= vmin:
            QMessageBox.warning(self, 'Invalid Range', 'Max must be greater than Min')
            return
        self._levels = (vmin, vmax)
        self.image_item.setLevels(self._levels)
        self.colorbar.setLevels(self._levels)

    # ------------------------------------------------------------------ #
    #                           UDP polling                              #
    # ------------------------------------------------------------------ #

    def poll_udp(self):
        if not getattr(self, '_receiving', True):
            return
        try:
            packet, _ = self.sock.recvfrom(65535)
        except BlockingIOError:
            return
        decoded = decode_packet(packet)
        if not decoded:
            return
        ts, grid, magnet, gyro, accel = decoded

        raw = grid.copy()
        if self._offset_enabled:
            if not self._offset_ready:
                self._offset_accum.append(raw)
                if len(self._offset_accum) >= OFFSET_SAMPLES:
                    self._offset_baseline = np.median(np.stack(self._offset_accum), axis=0)
                    self._offset_ready = True
                    self.status_label.setText('Offset Applied')
                else:
                    self.status_label.setText(
                        f'Offset Learning {len(self._offset_accum)}/{OFFSET_SAMPLES}')
            if self._offset_ready:
                grid = raw - self._offset_baseline + OFFSET_REFERENCE_MV
        self._pressure = grid

        if self._recording and self._log_writer:
            self._log_writer.writerow([ts] + raw.flatten().tolist())

        # ---------------- IMU update ---------------- #
        if gyro is not None and accel is not None:
            if self._imu_calib_cnt < IMU_CALIB_SAMPLES:
                self._gyro_bias += gyro
                self._imu_calib_cnt += 1
                if self._imu_calib_cnt == IMU_CALIB_SAMPLES:
                    self._gyro_bias /= IMU_CALIB_SAMPLES
                return
            now = time.time()
            dt = now - self.last_ts
            self.ahrs.sampleperiod = dt
            self.last_ts = now
            corrected_gyro = gyro - self._gyro_bias
            # Choose update method based on magnetometer usage
            if USING_MAGNET and magnet is not None:
                # MARG update: use magnet data
                self.quaternion = self.ahrs.updateMARG(gyr=corrected_gyro.tolist(),
                                                       acc=accel.tolist(),
                                                       mag=list(magnet),
                                                       q=self.quaternion.tolist())
            else:
                # IMU-only update
                self.quaternion = self.ahrs.updateIMU(gyr=corrected_gyro.tolist(),
                                                      acc=accel.tolist(),
                                                      q=self.quaternion.tolist())
            # normalize
            self.quaternion = np.array(self.quaternion, dtype=np.float32)
            self.quaternion /= np.linalg.norm(self.quaternion)

    def update_views(self):
        self.image_item.setImage(self._pressure, levels=self._levels)
        qw, qx, qy, qz = self.quaternion
        m = QMatrix4x4(1 - 2 * qy * qy - 2 * qz * qz, 2 * qx * qy - 2 * qw * qz,
                       2 * qx * qz + 2 * qw * qy, 0, 2 * qx * qy + 2 * qw * qz,
                       1 - 2 * qx * qx - 2 * qz * qz, 2 * qy * qz - 2 * qw * qx, 0,
                       2 * qx * qz - 2 * qw * qy, 2 * qy * qz + 2 * qw * qx,
                       1 - 2 * qx * qx - 2 * qy * qy, 0, 0, 0, 0, 1)
        self.mesh_item.setTransform(m)

        roll = math.atan2(2 * (qw * qx + qy * qz), 1 - 2 * (qx * qx + qy * qy))
        pitch = math.asin(max(-1.0, min(1.0, 2 * (qw * qy - qz * qx))))
        self.bubble_widget.set_tilt(roll, pitch)

    # ------------------------------------------------------------------ #
    #                              Exit                                  #
    # ------------------------------------------------------------------ #

    def closeEvent(self, event) -> None:
        if self._log_handle:
            self._log_handle.close()
        self.sock.close()
        return super().closeEvent(event)


# --------------------------------------------------------------------------- #
#                               Top‑level                                     #
# --------------------------------------------------------------------------- #


def _install_sigint_handler(app: QApplication) -> None:
    signal.signal(signal.SIGINT, lambda _sig, _frm: app.quit())


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
