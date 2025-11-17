import pygame
import numpy as np
import threading
import time
import os

# --- 設定 ---------------------------------
MP3_FILE = "Push_strong.mp3"         # 再生するMP3ファイル名
BEEP_INTERVAL_SEC = 0.6         # ビープ音の間隔（秒）
BEEP_FREQ = 880                 # ビープ音の周波数（Hz） (例: 440=ラ, 880=高いラ)
BEEP_DURATION_MS = 150          # ビープ音の長さ（ミリ秒）
SAMPLE_RATE = 44100             # オーディオのサンプルレート
# ------------------------------------------

def generate_beep(frequency, duration_ms, sample_rate):
    """
    指定された周波数と長さのビープ音（numpy配列）を生成し、
    pygameのSoundオブジェクトにして返す
    """
    # サンプル数を計算
    num_samples = int(sample_rate * duration_ms / 1000.0)
    
    # サイン波を生成 ( -1.0 から 1.0 の範囲)
    t = np.linspace(0., duration_ms / 1000.0, num_samples, endpoint=False)
    wave = np.sin(2 * np.pi * frequency * t)
    
    # 16ビットの整数形式 ( -32768 から 32767 ) に変換
    wave = (wave * (2**15 - 1)).astype(np.int16)
    
    # ステレオ（2チャンネル）にするため、配列を2列にする
    wave_stereo = np.column_stack([wave, wave])
    
    # numpy配列からpygameのSoundオブジェクトを作成
    return pygame.sndarray.make_sound(wave_stereo)

def beep_task(beep_sound, interval, stop_event):
    """
    ビープ音を一定間隔で鳴らし続けるスレッド用の関数
    """
    print("ビープ音スレッド開始。")
    while not stop_event.is_set():
        # ビープ音を再生
        beep_sound.play()
        
        # 次のビープ音まで待機
        # time.sleep()の代わりにstop_event.wait()を使うことで、
        # 待機中にもスレッドの停止信号を検知できる
        stop_event.wait(timeout=interval)
    print("ビープ音スレッド停止。")

def main():
    # --- 1. MP3ファイルの存在チェック ---
    if not os.path.exists(MP3_FILE):
        print(f"エラー: '{MP3_FILE}' が見つかりません。")
        print("このスクリプトと同じディレクトリに、再生したいMP3ファイルを置いてください。")
        return

    # --- 2. pygameミキサーの初期化 ---
    # pre_initでバッファサイズ等を設定 (音ズレ防止)
    pygame.mixer.pre_init(SAMPLE_RATE, -16, 2, 512)
    pygame.init()
    pygame.mixer.init()

    try:
        # --- 3. サウンドの準備 ---
        print("サウンドを準備中...")
        # ビープ音を生成
        beep_sound = generate_beep(BEEP_FREQ, BEEP_DURATION_MS, SAMPLE_RATE)
        
        # MP3ファイルをロード (musicチャンネルを使用)
        pygame.mixer.music.load(MP3_FILE)

        # --- 4. スレッディングの準備 ---
        # ビープ音スレッドを停止させるための「フラグ」
        stop_event = threading.Event()
        
        # ビープ音を鳴らすための別スレッドを作成
        beep_thread = threading.Thread(
            target=beep_task, 
            args=(beep_sound, BEEP_INTERVAL_SEC, stop_event)
        )

        # --- 5. 再生開始 ---
        print(f"再生を開始します... (MP3の再生が終わるか、Ctrl+Cで停止します)")
        
        # ビープ音スレッドを開始
        beep_thread.start()
        
        # MP3の再生を開始 (メインスレッド)
        pygame.mixer.music.play()

        # MP3の再生が続く間、メインスレッドを待機させる
        while pygame.mixer.music.get_busy() and beep_thread.is_alive():
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n再生を中断します。")
    
    finally:
        # --- 6. 終了処理 ---
        print("再生を停止しています...")
        
        # ビープ音スレッドに停止信号を送る
        stop_event.set()
        
        # MP3の再生を停止
        pygame.mixer.music.stop()
        
        # ビープ音スレッドが完全に終了するのを待つ
        beep_thread.join()
        
        # pygameを終了
        pygame.mixer.quit()
        pygame.quit()
        print("完了。")

if __name__ == "__main__":
    main()