"""
server.py
=========

UDP packet parser and debugger for G-CU sensor stream format.

Purpose
-------
This script acts as a low-level inspection tool for UDP sensor data packets.
It extracts header info, sensor values, timestamps, and IMU data from
binary packets sent by the G-CU device.

Main Features
-------------
* Binds to UDP port 31415 to receive sensor packets
* Parses and prints:
  - Start flag, device ID, sensor count
  - Timestamp (epoch + millis)
  - 11×11 sensor grid values (float or int)
  - IMU fields (accel, gyro, magnet)
  - End flag
* Useful for testing firmware-generated data packet formats

Note
----
Sensor format is assumed fixed. Update `sensor_data_size` or format string
if the binary layout changes.
This script is for G-CU ver 1.x. or more.
"""

"""
エラーが出る場合は
# UDP_PORTの部分を実際のポート番号に置き換えてください
lsof -i :UDP_PORT
# PIDの部分を特定したプロセスIDに置き換えてください
kill -9 PID
これでうまくいく
"""



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

start = time.time()
output_list = []

header = [
    "time", "compression0", "compression1", "compression2", "compression3",
    "accel_x", "accel_y", "accel_z"
]


while True:
    data, addr = sock.recvfrom(1024)
    #print(f"Received {len(data)} bytes from {addr}")
    #print(f"data = {data.hex()}")

    offset = 0

    # ヘッダ部
    start_flag = data[offset:offset + 2]
    offset += 2
    device_id = data[offset]
    offset += 1
    sensor_count = data[offset]
    offset += 1

    # タイムスタンプ
    epoch, = struct.unpack_from('<I', data, offset)
    offset += 4
    millis, = struct.unpack_from('<H', data, offset)
    offset += 2

    #print(f"Device ID: {device_id}, Epoch: {epoch}, Millis: {millis}")

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
        
        set_list = [
            epoch,
            sensors[0], sensors[1], sensors[2], sensors[3],
            imu["accel_x"], imu["accel_y"], imu["accel_z"]
        ]
        #print("IMU:", imu)
        output_list.append(set_list)

    # End flag
    end_flag = data[offset:offset + 2]
    #print(f"End flag: {end_flag.hex()}")
    #print("-" * 40)

    now = time.time()
    if now - start > 10:
        break

# 'data.csv'という名前のファイルを書き込みモードで開く
with open('output_data_exp2.csv', mode='w', newline='', encoding='utf-8') as f:
    # この中に書き込み処理を書いていく
    writer = csv.writer(f)
    writer.writerow(header)
    writer.writerows(output_list)


