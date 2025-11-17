import pandas as pd
import matplotlib.pyplot as plt

# 日本語フォントを正しく表示するための設定
plt.rcParams['font.sans-serif'] = ['Hiragino Maru Gothic Pro', 'Yu Gothic', 'MS Gothic']
plt.rcParams['axes.unicode_minus'] = False  # マイナス記号の文字化けを防ぐ

# --- グラフの設定 ---
# 1. ファイル名
file_name = '/Users/watanaberyouta/research/2025/research_Glove/force/20251109/log_2025-11-09_16-32-28_over.csv'
output_filename = './force/scatter_plot_ranged.png'
# 2. X軸とY軸に使う列の名前
y_column = 'Primary Parameter'
x_column = 'Force'

# 3. ★★★【新機能】★★★
#    データの読み込み範囲を指定します

#    データの先頭から、ここで指定した行数ぶんスキップします (10なら10行目までを無視し11行目から開始)
#    Pythonの内部処理では0から数えるため、10行目から始めたい場合は「9」と設定します。
start_index = 79

#    データのここで指定した行で読み込みを終了します
#    Pythonの内部処理では指定した値の手前までを読み込むため、50行目まで含めたい場合は「50」と設定します。
end_index = 315
# --------------------

try:
    # CSVファイルを読み込みます。
    # ヘッダーが6行目にあるため、header=5と指定します。
    df = pd.read_csv(file_name, header=5, encoding='shift_jis')

    # (念のため) 列名の前後の余分なスペースを削除します
    df.columns = df.columns.str.strip()

    print(f"CSVファイルの読み込みに成功しました。元のデータ数: {len(df)}行")

    # ★★★【新機能】★★★
    # 指定した範囲のデータに絞り込みます
    if start_index < end_index and not df.empty:
        df = df.iloc[start_index:end_index].reset_index(drop=True)
        print(f"データの {start_index + 1}行目から{end_index}行目の範囲に絞り込みました。")
        print(f"グラフ化するデータ数: {len(df)}行")

    # 散布図を描画します
    plt.figure(figsize=(12, 8))
    plt.scatter(df[x_column], df[y_column], alpha=0.7)

    # グラフのタイトルと軸ラベルを設定します
    plt.title(f'「{x_column}」と「{y_column}」の散布図 ({start_index + 1}〜{end_index}行)', fontsize=16)
    plt.xlabel(x_column, fontsize=12)
    plt.ylabel(y_column, fontsize=12)
    plt.grid(True)

    # グラフを画像ファイルとして保存します
    plt.savefig(output_filename)

    print(f"グラフを '{output_filename}' という名前で保存しました。")

except FileNotFoundError:
    print(f"エラー: ファイル '{file_name}' が見つかりませんでした。")
except KeyError as e:
    print(f"エラー: 指定された列 {e} が見つかりません。列名が正しいか確認してください。")
except Exception as e:
    print(f"予期せぬエラーが発生しました: {e}")