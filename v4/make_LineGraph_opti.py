import pandas as pd
import matplotlib.pyplot as plt

# --- ▼▼▼ ここを編集してください ▼▼▼ ---

# 1. CSVファイルの正確なパスまたはファイル名を指定してください
#    このスクリプトと同じフォルダにCSVファイルがあれば、ファイル名だけでOKです。
file_name = './opti/Take 2025-07-15 04.03.38 PM exp1.csv'

# 2. グラフにしたい「列の名前」を一つ指定してください
#    例: 'Unlabeled 5072_Y', 'Unlabeled 5073_X', など
column_to_plot = 'Unlabeled 5072_533029D47892613211F0'

# --- ▲▲▲ 編集はここまで ▲▲▲ ---

"""
['Unnamed: 0_level_0', 'Name_ID', 
'Unlabeled 5072_533029D47892613211F0', 
'Unlabeled 5072_533029D47892613211F0.1',
'Unlabeled 5072_533029D47892613211F0.2',
 'Unlabeled 5073_533429D47892613211F0', 
 'Unlabeled 5073_533429D47892613211F0.1', 
 'Unlabeled 5073_533429D47892613211F0.2', 
 'Unlabeled 5074_533729D47892613211F0', 
 'Unlabeled 5074_533729D47892613211F0.1']

"""



try:
    print(f"--- 処理を開始します ---")
    print(f"ファイル: {file_name}")
    print(f"プロットする列: {column_to_plot}")

    # ===== Step 1: CSVファイルの読み込みと整形 =====
    # ヘッダーが3行目と4行目にあるため、[2, 3]と指定して読み込みます
    df = pd.read_csv(file_name, header=[2, 3])

    # 複雑な列名を 'マーカー名_座標' の形式に整形します
    new_columns = []
    for col in df.columns:
        if 'Unnamed' in col[1]:
            new_columns.append(col[0])
        else:
            new_columns.append(f"{col[0]}_{col[1]}")
    df.columns = new_columns
    
    # ヘッダー情報だった最初の2行のデータを削除します
    df = df.drop([0, 1]).reset_index(drop=True)
    
    # すべての列を数値に変換します（変換できない値は欠損値NaNになります）
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    print("CSVファイルの読み込みと整形が完了しました。")

    # ===== Step 2: グラフの描画 =====
    # 日本語フォントとマイナス記号の文字化け対策
    plt.rcParams['font.sans-serif'] = ['Hiragino Maru Gothic Pro', 'Yu Gothic', 'MS Gothic']
    plt.rcParams['axes.unicode_minus'] = False

    # グラフのサイズを大きく設定
    plt.figure(figsize=(15, 8))

    # 折れ線グラフを描画し、各データ点にマーカー('o')を打ちます
    plt.plot(df.index, df[column_to_plot], marker='o', linestyle='-')

    # グラフの装飾
    plt.title(f'「{column_to_plot}」の推移', fontsize=16)
    plt.xlabel('行番号 (フレーム)', fontsize=12)
    plt.ylabel(f'座標 ({column_to_plot})', fontsize=12)
    plt.grid(True) # グリッド線を表示

    # グラフを画像として保存
    output_filename = 'output_graph.png'
    plt.savefig(output_filename)

    print(f"\n--- 処理が完了しました ---")
    print(f"グラフを '{output_filename}' という名前で保存しました。")


except FileNotFoundError:
    print(f"\nエラー: ファイル '{file_name}' が見つかりませんでした。パスが正しいか確認してください。")
except KeyError:
    print(f"\nエラー: 指定された列 '{column_to_plot}' がCSVファイルに存在しません。")
    print("利用可能な列名の例:", df.columns.tolist()[:10]) # 列名の候補を10個表示
except Exception as e:
    print(f"\n予期せぬエラーが発生しました: {e}")