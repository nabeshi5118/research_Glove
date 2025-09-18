import csv
class CalculateAndRecodeCSV():
    def __init__(self):
        #出力用の配列データ
        self.csv_data = []
        #配列データ内にある辞書データ
        self.recode_data = {
            "time":int(0),
            "accel_data":float(0),
            "pressure_data":float(0),
            "distance_cal":float(0)
        }

    def recode_from_esp32(self,time,accel,pressure):
        key_name = list(self.recode_data)
        self.recode_data[key_name[0]] = time
        self.recode_data[key_name[1]] = accel
        self.recode_data[key_name[2]] = pressure

    def recode_from_calculated(self):
        #いったん作っただけ
        maked = 0

    #加速度基準で計算する
    def calculate_distance_from_accel(self):
        print("")
        
    #圧力センサー基準で計算する
    def calculate_distance_from_pressure(self):
        print("")


    #csvデータとして保存する
    def make_csv(self,path = './output_data.csv'):

        # 辞書のキーを取得してヘッダー（列名）として使用
        header = self.recode_data[0].keys()

        with open(path, 'w', newline='', encoding='utf-8') as csvfile:
            # DictWriterオブジェクトを作成
            # fieldnamesにヘッダーのリストを指定
            writer = csv.DictWriter(csvfile, fieldnames=header)
            
            # 1行目にヘッダーを書き込む
            writer.writeheader()
            
            # 複数行のデータを一括で書き込む
            writer.writerows(self.recode_data)


