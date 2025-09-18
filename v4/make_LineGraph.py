import pandas as pd
import matplotlib.pyplot as plt

# 日本語フォントの設定 (文字化け対策)
# ご利用の環境に合わせてフォント名を変更してください
plt.rcParams['font.sans-serif'] = ['Hiragino Maru Gothic Pro', 'Yu Gothic', 'MS Gothic']


# --- ここを編集してください ---
# ファイル名を指定
file_name = 'output_data_exp1.csv'
# グラフにしたい列の名前を指定
value_column = 'compression3' # 例: '売上', '温度'など
# ---------------------------

try:
    # CSVファイルを読み込む
    df = pd.read_csv(file_name)

    # グラフのサイズを大きく設定
    plt.figure(figsize=(15, 8))

    # 折れ線グラフを描画し、各データ点にマーカー('o')を打つ
    plt.plot(df.index, df[value_column], marker='o', linestyle='-')

    # グラフの装飾
    plt.title(f'{value_column} の推移', fontsize=16)
    plt.xlabel('行番号', fontsize=12)
    plt.ylabel(value_column, fontsize=12)
    plt.grid(True) # グリッド線を表示

    # グラフを画像として保存
    plt.savefig('output_graph_large_with_dots.png')

    print("大きなサイズのグラフを 'output_graph_large_with_dots.png' として保存しました。")

except FileNotFoundError:
    print(f"エラー: ファイル '{file_name}' が見つかりません。")
except KeyError:
    print(f"エラー: 指定された列 '{value_column}' がCSVファイルに存在しません。列名が正しいか確認してください。")
except Exception as e:
    print(f"エラーが発生しました: {e}")