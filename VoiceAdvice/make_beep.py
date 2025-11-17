import sys
from pydub import AudioSegment
from pydub.generators import Sine

# --- 設定 ---
BPM = 110              # ビート/分
DURATION_SEC = 10      # 生成する秒数
BEEP_FREQ = 440        # ビープ音の周波数 (Hz) (440Hzは「ラ」の音)
BEEP_DURATION_MS = 100 # ビープ音自体の長さ (ミリ秒)
OUTPUT_FILENAME = "beep_110bpm_10s.mp3"

# --- 計算 ---
# 1ビートあたりの時間 (ミリ秒)
try:
    beat_duration_ms = (60 / BPM) * 1000
except ZeroDivisionError:
    print("エラー: BPMに0は設定できません。")
    sys.exit()

# 総再生時間 (ミリ秒)
total_duration_ms = DURATION_SEC * 1000

print(f"設定: {BPM} BPM, 1ビートの間隔: {beat_duration_ms:.2f} ミリ秒")

# --- オーディオ生成 ---

# 1. ビープ音自体を作成 (少し音量を下げて耳障りでないようにします)
beep = Sine(BEEP_FREQ).to_audio_segment(
    duration=BEEP_DURATION_MS
).apply_gain(-10) 

# 2. 1ビート分の無音部分を作成
silence_duration = beat_duration_ms - BEEP_DURATION_MS
if silence_duration < 0:
    # ビープ音がビート間隔より長い場合は無音なし
    silence_duration = 0

silence = AudioSegment.silent(duration=silence_duration)

# 3. 1ビートのセグメント（ビープ + 無音）を作成
one_beat = beep + silence

# 4. 10秒になるまでビートを繰り返す
final_audio = AudioSegment.empty()
while len(final_audio) < total_duration_ms:
    final_audio += one_beat

# 5. ぴったり10秒にカットする
final_audio = final_audio[:total_duration_ms]

# --- MP3としてエクスポート ---
try:
    print(f"'{OUTPUT_FILENAME}' を書き出しています...")
    final_audio.export(OUTPUT_FILENAME, format="mp3")
    print(f"'{OUTPUT_FILENAME}' の作成が完了しました。")

except FileNotFoundError:
    print("\n" + "="*30)
    print("      エラー: MP3の書き出しに失敗しました     ")
    print("="*30)
    print("MP3を処理するには **FFmpeg** が必要です。")
    print("FFmpegがインストールされていないか、PCのパスが通っていないようです。")
    print("\n解決策:")
    print("  - (Windows/Anaconda環境の場合) ターミナルで以下を実行:")
    print("    conda install ffmpeg -c conda-forge")
    print("  - (Mac/Homebrew環境の場合) ターミナルで以下を実行:")
    print("    brew install ffmpeg")
    print("  - または、FFmpeg公式サイトからダウンロードしてパスを通してください。")