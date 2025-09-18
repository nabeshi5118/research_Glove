import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks, butter, filtfilt, detrend
from scipy.integrate import cumulative_trapezoid
from sklearn.decomposition import PCA

def analyze_compression_with_baseline_correction(csv_file_path: str, output_image_path: str):
    """
    ユーザーの定義に基づき、胸骨圧迫の距離を推定する関数。
    ★各圧迫サイクルの開始点を深さ0に補正する機能を追加。
    """
    try:
        df = pd.read_csv(csv_file_path)
    except FileNotFoundError:
        print(f"エラー: ファイル '{csv_file_path}' が見つかりません。")
        return

    # --- パラメータ設定 (変更なし) ---
    SAMPLING_RATE = 18.5
    PEAK_PROMINENCE = 50 
    VALLEY_PROMINENCE = 50
    CUTOFF_FREQ = 0.6
    FILTER_ORDER = 4

    # --- 1. ピークと谷の検出 (変更なし) ---
    peaks, _ = find_peaks(df['compression3'], prominence=PEAK_PROMINENCE)
    inverted_pressure = -df['compression3']
    valleys, _ = find_peaks(inverted_pressure, prominence=VALLEY_PROMINENCE)
    if len(valleys) < 2:
        print("エラー: 圧迫のスタート地点（谷）を2つ以上検出できませんでした。")
        return
    print(f"合計 {len(peaks)} 回の最大圧迫点と {len(valleys)} 回のスタート地点を検出しました。")
    print("-" * 30)

    # --- 2. 加速度データの前処理 (PCA) (変更なし) ---
    accel_data = df[['accel_x', 'accel_y', 'accel_z']].values
    pca = PCA(n_components=1)
    df['accel_pca'] = -pca.fit_transform(accel_data).flatten()

    # --- 3. 距離推定とベースライン補正 ---
    df['displacement'] = np.nan
    max_depths = []
    print("各圧迫サイクルの推定深度を計算中（開始点を0に補正）...")
    for i in range(len(valleys) - 1):
        start_idx = valleys[i]
        end_idx = valleys[i+1]
        
        segment_accel = df.loc[start_idx:end_idx, 'accel_pca'].values
        nyq = 0.5 * SAMPLING_RATE
        normal_cutoff = CUTOFF_FREQ / nyq
        b, a = butter(FILTER_ORDER, normal_cutoff, btype='high', analog=False)
        filtered_accel = filtfilt(b, a, segment_accel)
        velocity = cumulative_trapezoid(filtered_accel, dx=1/SAMPLING_RATE, initial=0)
        detrended_velocity = detrend(velocity)
        displacement = cumulative_trapezoid(detrended_velocity, dx=1/SAMPLING_RATE, initial=0)
        detrended_displacement = detrend(displacement)
        
        # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
        # ★ 修正点: 各サイクルの開始点が0になるようにベースラインを補正 ★
        # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
        baselined_displacement = detrended_displacement - detrended_displacement[0]
        
        df.loc[start_idx:end_idx, 'displacement'] = baselined_displacement[:len(df.loc[start_idx:end_idx])]
        current_max_depth = np.abs(np.min(baselined_displacement))
        max_depths.append(current_max_depth)
        print(f"  - サイクル {i+1} (サンプル {start_idx}-{end_idx}): 推定最大深度 = {current_max_depth*100:.2f} cm")
    
    print("-" * 30)
    # --- 4. 結果の可視化 (変更なし) ---
    fig, axes = plt.subplots(3, 1, figsize=(15, 12), sharex=True)
    fig.suptitle('Chest Compression Analysis (Baselined at Start)', fontsize=16)

    axes[0].plot(df.index, df['compression3'], label='Pressure (compression3)', color='g', zorder=1)
    axes[0].scatter(peaks, df.loc[peaks, 'compression3'], color='red', s=50, zorder=2, label='Peak Pressure')
    axes[0].scatter(valleys, df.loc[valleys, 'compression3'], color='blue', s=50, zorder=2, marker='v', label='Start/End Position')
    axes[0].set_title('Pressure Sensor: Peaks and Valleys')
    axes[0].set_ylabel('Pressure Value')
    axes[0].legend()
    axes[0].grid(True)
    
    axes[1].plot(df.index, df['accel_pca'], label='Principal Component of Acceleration', color='b')
    axes[1].set_title('Acceleration (after PCA)')
    axes[1].set_ylabel('Acceleration (Principal Component)')
    axes[1].legend()
    axes[1].grid(True)
    
    axes[2].plot(df.index, -df['displacement'].ffill(), label='Estimated Depth (Baselined)', color='purple')
    axes[2].set_title('Estimated Compression Depth (Each cycle starts at 0)')
    axes[2].set_xlabel('Sample Index')
    axes[2].set_ylabel('Depth (m)')
    axes[2].axhline(0, color='black', linewidth=0.8, linestyle='--')
    axes[2].legend()
    axes[2].grid(True)

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig(output_image_path)
    print(f"ベースライン補正版の解析結果グラフを '{output_image_path}' として保存しました。")
    if max_depths:
        avg_depth = np.mean(max_depths)
        print(f"平均最大深度: {avg_depth*100:.2f} cm")

if __name__ == '__main__':
    INPUT_CSV = 'esp_data/output_data_exp1.csv'
    OUTPUT_IMAGE = 'compression_analysis_baselined.png'
    
    analyze_compression_with_baseline_correction(INPUT_CSV, OUTPUT_IMAGE)