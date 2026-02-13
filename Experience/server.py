import socket
import struct
import time
import csv
import os
from datetime import datetime


# =========================
# 保存設定
# =========================
#チーム4のE-6とE-7はべつのグローブ
SAVE_DIR = "./Group2"
#SAVE_DIR = "./test"
os.makedirs(SAVE_DIR, exist_ok=True)

STRING_A = "F"
STRING_B = "7"
DURATION_SEC = 33  # 計測時間

DATE_STR = datetime.now().strftime("%Y%m%d")
CSV_FILENAME = f"{DATE_STR}_{STRING_A}_{STRING_B}.csv"
CSV_PATH = os.path.join(SAVE_DIR, CSV_FILENAME)

# =========================
# 同名ファイル存在チェック
# =========================
if os.path.exists(CSV_PATH):
    raise FileExistsError(
        f"CSVファイルが既に存在します: {CSV_PATH}\n"
        "上書き防止のため処理を中断しました。"
    )


def main(csv_path: str, duration_sec: float):
    # =========================
    # UDP 受信設定
    # =========================
    UDP_IP = "0.0.0.0"
    UDP_PORT = 12345
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))

    print(f"UDP listening on {UDP_IP}:{UDP_PORT}")
    print(f"Recording duration: {duration_sec} sec")

    # =========================
    # センサ設定
    # =========================
    sensors_rows_num = 2
    sensors_columns_num = 2
    sensors_num = sensors_rows_num * sensors_columns_num
    sensor_data_size = 4  # 4 or 2

    # =========================
    # CSVヘッダ（★ magn, gyro を追加）
    # =========================
    header = [
        "time",
        "compression0", "compression1", "compression2", "compression3",
        "magn_x", "magn_y", "magn_z",
        "gyro_x", "gyro_y", "gyro_z",
        "accel_x", "accel_y", "accel_z"
    ]

    # =========================
    # CSVを書き込みながらデータ収集
    # =========================
    with open(csv_path, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(header)

        start_time = time.time()
        packet_count = 0
        written_rows = 0

        while True:
            data, addr = sock.recvfrom(1024)
            offset = 0

            # ヘッダ部
            start_flag = data[offset:offset + 2]
            offset += 2
            device_id = data[offset]
            offset += 1
            sensor_count = data[offset]
            offset += 1

            # タイムスタンプ（読み捨て）
            epoch, = struct.unpack_from('<I', data, offset)
            offset += 4
            millis, = struct.unpack_from('<H', data, offset)
            offset += 2

            # センサデータ
            sensors = []
            for _ in range(sensors_num):
                if sensor_data_size == 4:
                    val, = struct.unpack_from('<I', data, offset)
                else:
                    val, = struct.unpack_from('<H', data, offset)
                sensors.append(val)
                offset += sensor_data_size

            # =========================
            # IMUデータ（★ magn, gyro, accel 全部保存）
            # =========================
            keys = [
                "magn_x", "magn_y", "magn_z",
                "gyro_x", "gyro_y", "gyro_z",
                "accel_x", "accel_y", "accel_z"
            ]

            # 9軸 * 4bytes = 36 bytes 必要
            if len(data) >= offset + 36:
                imu = {}
                for key in keys:
                    v, = struct.unpack_from('<f', data, offset)
                    imu[key] = v
                    offset += 4

                elapsed = time.time() - start_time

                row = [
                    f"{elapsed:.3f}",
                    sensors[0], sensors[1], sensors[2], sensors[3],
                    imu["magn_x"], imu["magn_y"], imu["magn_z"],
                    imu["gyro_x"], imu["gyro_y"], imu["gyro_z"],
                    imu["accel_x"], imu["accel_y"], imu["accel_z"]
                ]

                writer.writerow(row)
                written_rows += 1

                # ===== print 出力 =====
                print(
                    f"[{elapsed:6.3f}s] "
                    f"Sensors={sensors} | "
                    #f"Magn=({imu['magn_x']:.3f},{imu['magn_y']:.3f},{imu['magn_z']:.3f}) | "
                    #f"Gyro=({imu['gyro_x']:.3f},{imu['gyro_y']:.3f},{imu['gyro_z']:.3f}) | "
                    f"Accel=({imu['accel_x']:.3f},{imu['accel_y']:.3f},{imu['accel_z']:.3f})"
                )

                packet_count += 1
            else:
                # IMUが入ってない短いパケットの場合（必要ならログ出し）
                packet_count += 1

            # 終了条件
            if time.time() - start_time >= duration_sec:
                break

    sock.close()
    print(f"\nSaved CSV: {csv_path}")
    print(f"Total packets received: {packet_count}")
    print(f"Total rows written (with IMU): {written_rows}")


if __name__ == "__main__":
    main(CSV_PATH, DURATION_SEC)
