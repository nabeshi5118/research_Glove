import socket
import struct
import time
import csv

# 受信側の設定
UDP_IP = "0.0.0.0"
#ここをESP32で指定したポート番号にする
UDP_PORT = 12345
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

# センサ数（例：11 x 11 = 121）
sensors_rows_num = 2
sensors_columns_num = 2
sensors_num = sensors_rows_num * sensors_columns_num
data_format = 'f'  # 'H'なら2バイト、'f'ならfloat (4バイト)
sensor_data_size = 4  # or 2

header = [
    "time", "compression0", "compression1", "compression2", "compression3",
    "accel_x", "accel_y", "accel_z"
]


# ========================= 変更点① =========================
# whileループの外でCSVファイルを開き、最初にヘッダーを書き込みます。
# これにより、ループ内で一行ずつデータを追記できます。
# -----------------------------------------------------------
with open('output_data_exp2_modified.csv', mode='w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(header)

    start_time = time.time()

    # ========================= 変更点② =========================
    # 受信したデータパケットの数を数えるためのカウンターを初期化します。
    # このカウンターを使って、time列の値を 0.0, 0.1, 0.2... と生成します。
    # -----------------------------------------------------------
    packet_count = 0

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

        # タイムスタンプ（デバイスから送られてきた値は使用しませんが、オフセットを進めるために読み込みます）
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

        print("Sensor values:", sensors)

        # IMUデータ（加速度・ジャイロ・地磁気）
        print(f"Remaining IMU sensor data({len(data)}): {data[offset:].hex()}")
        imu = {}
        keys = [
                "magn_x", "magn_y", "magn_z", "gyro_x", "gyro_y", "gyro_z", "accel_x", "accel_y",
                "accel_z"
            ]

        if len(data) >= offset + 36:
            for key in keys:
                v, = struct.unpack_from('<f', data, offset)
                if "accel" in str(key):
                    imu[key] = v
                offset += 4
            
            # ========================= 変更点③ =========================
            # CSVに書き込むデータリストを作成します。
            # time列には `packet_count * 0.1` を設定し、0.1秒ごとの時間を表現します。
            # -----------------------------------------------------------
            set_list = [
                f"{packet_count * 0.1:.1f}",  # 小数点以下1桁でフォーマット
                sensors[0], sensors[1], sensors[2], sensors[3],
                imu["accel_x"], imu["accel_y"], imu["accel_z"]
            ]

            # ========================= 変更点④ =========================
            # リストに溜め込まず、受信するたびに1行ずつCSVファイルに書き込みます。
            # -----------------------------------------------------------
            writer.writerow(set_list)

            # カウンターを1増やします
            packet_count += 1

        # End flag
        end_flag = data[offset:offset + 2]

        # 元のコードと同じく、約10秒経過したらループを抜けます
        if time.time() - start_time > 10:
            break

# ========================= 変更点⑤ =========================
# withブロックが終了するとファイルは自動で閉じられます。
# 最後にまとめてリストを書き出す処理は不要になりました。
# -----------------------------------------------------------