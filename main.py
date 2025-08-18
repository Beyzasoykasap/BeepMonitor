import time
import numpy as np
import sounddevice as sd
import matplotlib.pyplot as plt
from matplotlib.widgets import CheckButtons, TextBox, Button
from matplotlib.animation import FuncAnimation
import config 

MEASURE_DURATION = 0.5
SAMPLERATE = 44100
BEEP_DURATION = 0.5
BEEP_FREQ = 1000
BEEP_VOLUME = 1.0
WAIT_AFTER_BEEP = 2
AUTOTHRESHOLD_DURATION = 5
SECURITY_DB = 5
MAX_POINTS = 200

auto_threshold_enabled = True
manual_threshold = None
THRESHOLD_DB = None
timestamps = []
db_values = []
start_time = time.time()
last_threshold_update = time.time()

def measure_once(duration=config.MEASURE_DURATION, samplerate=config.SAMPLERATE):
    recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1)
    sd.wait()
    rms = np.sqrt(np.mean(recording**2))
    db = 20 * np.log10(rms + 1e-12)
    return db, rms

def play_beep(duration=config.BEEP_DURATION, freq=config.BEEP_FREQ, samplerate=config.SAMPLERATE):
    t = np.linspace(0, duration, int(samplerate * duration), endpoint=False)
    wave = config.BEEP_VOLUME * np.sin(2 * np.pi * freq * t)
    sd.play(wave, samplerate)
    sd.wait()

def auto_threshold(duration=config.AUTOTHRESHOLD_DURATION):
    print(f"Ortam gurultusu olculuyor ({duration} saniye)...")
    values = []
    start = time.time()
    while time.time() - start < duration:
        db, _ = measure_once(duration=0.5)
        values.append(db)
        time.sleep(0.1)
    avg_db = np.mean(values)
    threshold = avg_db + config.SECURITY_DB
    print(f"Ortalama ortam gurultusu: {avg_db:.2f} dBFS")
    print(f"Otomatik esik degeri: {threshold:.2f} dBFS")
    return threshold

def increase_volume(event):
    config.BEEP_VOLUME = min(config.BEEP_VOLUME + 0.05, 1.0)
    print(f"Ses artti: {config.BEEP_VOLUME:.2f}")

def decrease_volume(event):
    config.BEEP_VOLUME = max(config.BEEP_VOLUME - 0.05, 0.0)
    print(f"Ses azaldi: {config.BEEP_VOLUME:.2f}")

def toggle_auto_threshold(label):
    global auto_threshold_enabled, THRESHOLD_DB, manual_threshold
    if check.get_status()[0]:
        auto_threshold_enabled = True
        print("Otomatik esik aktif. Manuel giris devre disi.")
        THRESHOLD_DB = auto_threshold()
        text_box.set_active(False)
    
    else:
        auto_threshold_enabled = False
        text_box.set_active(True)
        if manual_threshold is not None:
            THRESHOLD_DB = manual_threshold
            print(f"Otomatik kapali. Manuel esik: {THRESHOLD_DB:.2f} dBFS")
        else:
            THRESHOLD_DB = None
            print("Otomatik kapali. Lütfen manuel esik girin.")
    update_threshold_line()

def set_manual_threshold(text):
    global manual_threshold, THRESHOLD_DB, auto_threshold_enabled
    try:
        val = float(text)
        manual_threshold = val
        auto_threshold_enabled = False
        THRESHOLD_DB = manual_threshold
        if check.get_status()[0]:
            check.set_active(0)
        print(f"Manuel esik ayarlandi: {THRESHOLD_DB:.2f} dBFS (Otomatik kapatildi)")
        update_threshold_line()
    except ValueError:
        print("Geçersiz sayi! Ornek: -30 veya -25.5")

def update_threshold_line():
    if timestamps:
        x0, x1 = timestamps[0], timestamps[-1]
    else:
        x0, x1 = 0, 1
    y = THRESHOLD_DB if THRESHOLD_DB is not None else -90.0
    threshold_line.set_xdata([x0, x1])
    threshold_line.set_ydata([y, y])
    ax.relim()
    ax.autoscale_view()


fig, ax = plt.subplots()
plt.subplots_adjust(right=0.78)

line, = ax.plot([], [], label="Anlik dB")
threshold_line, = ax.plot([], [], 'r--', label="Esik")
ax.set_xlabel("Sure (saniye)")
ax.set_ylabel("dBFS")
ax.legend()

ax_increase = fig.add_axes([0.80, 0.82, 0.16, 0.06])
ax_decrease = fig.add_axes([0.80, 0.74, 0.16, 0.06])
btn_increase = Button(ax_increase, 'Ses +')
btn_decrease = Button(ax_decrease, 'Ses -')
btn_increase.on_clicked(increase_volume)
btn_decrease.on_clicked(decrease_volume)

rax = fig.add_axes([0.80, 0.60, 0.16, 0.10])
check = CheckButtons(rax, ['Otomatik esik'], [True])
check.on_clicked(toggle_auto_threshold)

axbox = fig.add_axes([0.80, 0.52, 0.16, 0.06])
text_box = TextBox(axbox, 'Esik (dBFS)')
text_box.on_submit(set_manual_threshold)

def update(frame):
    global last_threshold_update, THRESHOLD_DB

    db, rms = measure_once()
    print(f"Anlik ses: {db:.2f} dBFS")

    if THRESHOLD_DB is not None and db > THRESHOLD_DB:
        print("Eşik asildi! Bip çaliniyor...")
        play_beep()
        time.sleep(config.WAIT_AFTER_BEEP)

    if auto_threshold_enabled and (time.time() - last_threshold_update > 600):
        THRESHOLD_DB = auto_threshold()
        last_threshold_update = time.time()
        update_threshold_line()

    current_time = time.time() - start_time
    timestamps.append(current_time)
    db_values.append(db)
    if len(timestamps) > config.MAX_POINTS:
        timestamps.pop(0)
        db_values.pop(0)

    line.set_data(timestamps, db_values)
    if THRESHOLD_DB is not None and timestamps:
        threshold_line.set_xdata([timestamps[0], timestamps[-1]])
    ax.relim()
    ax.autoscale_view()

print("Ses olcum programi basliyor..")
THRESHOLD_DB = auto_threshold()
update_threshold_line()

ani = FuncAnimation(fig, update, interval=100)
plt.show()
