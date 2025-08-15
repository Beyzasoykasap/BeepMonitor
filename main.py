import sounddevice as sd
import numpy as np
import time
import matplotlib.pyplot as plt
from matplotlib.widgets import CheckButtons, TextBox, Button
from matplotlib.animation import FuncAnimation

# ---------- Sabitler ----------
MEASURE_DURATION = 0.5
BEEP_DURATION = 0.5
BEEP_FREQ = 1000
SAMPLERATE = 44100
WAIT_AFTER_BEEP = 2
AUTOTHRESHOLD_DURATION = 10
SECURITY_DB = 5
BEEP_VOLUME = 1.0
MAX_POINTS = 200

# ---------- Global Değişkenler ----------
auto_threshold_enabled = True
manual_threshold = None
THRESHOLD_DB = None
timestamps = []
db_values = []
start_time = time.time()

# ---------- Fonksiyonlar ----------

def measure_once(duration=MEASURE_DURATION, samplerate=SAMPLERATE):
    recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1)
    sd.wait()
    rms = np.sqrt(np.mean(recording**2))
    db = 20 * np.log10(rms + 1e-12)
    return db, rms

def play_beep(duration=BEEP_DURATION, freq=BEEP_FREQ, samplerate=SAMPLERATE):
    t = np.linspace(0, duration, int(samplerate * duration), endpoint=False)
    wave = BEEP_VOLUME * np.sin(2 * np.pi * freq * t)
    sd.play(wave, samplerate)
    sd.wait()

def auto_threshold(duration=AUTOTHRESHOLD_DURATION):
    print(f"Ortam gürültüsü ölçülüyor ({duration} saniye)...")
    values = []
    start = time.time()
    while time.time() - start < duration:
        db, _ = measure_once(duration=0.5)
        values.append(db)
        time.sleep(0.1)
    avg_db = np.mean(values)
    threshold = avg_db + SECURITY_DB
    print(f"Ortalama ortam gürültüsü: {avg_db:.2f} dBFS")
    print(f"Otomatik eşik değeri: {threshold:.2f} dBFS")
    return threshold

def increase_volume(event):
    global BEEP_VOLUME
    BEEP_VOLUME = min(BEEP_VOLUME + 0.05, 1.0)
    print(f"Ses arttı: {BEEP_VOLUME:.2f}")

def decrease_volume(event):
    global BEEP_VOLUME
    BEEP_VOLUME = max(BEEP_VOLUME - 0.05, 0.0)
    print(f"Ses azaldı: {BEEP_VOLUME:.2f}")

def toggle_auto_threshold(label):
    global auto_threshold_enabled, THRESHOLD_DB
    auto_threshold_enabled = not auto_threshold_enabled
    if auto_threshold_enabled:
        THRESHOLD_DB = auto_threshold()
        print("Otomatik eşik aktif.")
    else:
        if manual_threshold is not None:
            THRESHOLD_DB = manual_threshold
            print(f"Otomatik kapalı. Manuel eşik: {THRESHOLD_DB:.2f} dBFS")
        else:
            print("Otomatik kapalı. Lütfen manuel eşik girin.")
    update_threshold_line()

def set_manual_threshold(text):
    global manual_threshold, THRESHOLD_DB, auto_threshold_enabled
    try:
        val = float(text)
        manual_threshold = val
        auto_threshold_enabled = False
        THRESHOLD_DB = manual_threshold
        print(f"Manuel eşik değeri ayarlandı: {THRESHOLD_DB:.2f} dBFS (Otomatik kapatıldı)")
        update_threshold_line()
    except ValueError:
        print("Geçersiz sayı! Örnek: -30 veya -25.5")

# ---------- Grafik Ayarları ----------
fig, ax = plt.subplots()
plt.subplots_adjust(right=0.78)

line, = ax.plot([], [], label="Anlık dB")
threshold_line, = ax.plot([], [], 'r--', label="Eşik")
ax.set_xlabel("Süre (saniye)")
ax.set_ylabel("dBFS")
ax.legend()

# Kontrol bileşenleri
ax_increase = fig.add_axes([0.80, 0.82, 0.16, 0.06])
ax_decrease = fig.add_axes([0.80, 0.74, 0.16, 0.06])
btn_increase = Button(ax_increase, 'Ses +')
btn_decrease = Button(ax_decrease, 'Ses -')
btn_increase.on_clicked(increase_volume)
btn_decrease.on_clicked(decrease_volume)

rax = fig.add_axes([0.80, 0.60, 0.16, 0.10])
check = CheckButtons(rax, ['Otomatik eşik'], [True])
check.on_clicked(toggle_auto_threshold)

axbox = fig.add_axes([0.80, 0.52, 0.16, 0.06])
text_box = TextBox(axbox, 'Eşik (dBFS)')
text_box.on_submit(set_manual_threshold)

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

# ---------- Güncelleme Fonksiyonu ----------
last_threshold_update = time.time()
def update(frame):
    global last_threshold_update, THRESHOLD_DB

    db, rms = measure_once()
    print(f"Anlık ses: {db:.2f} dBFS")

    # Bip çalma
    if THRESHOLD_DB is not None and db > THRESHOLD_DB:
        print("Eşik aşıldı! Bip çalınıyor...")
        play_beep()
        time.sleep(WAIT_AFTER_BEEP)

    # Otomatik eşik güncellemesi (10 dk aralıkla)
    if auto_threshold_enabled and (time.time() - last_threshold_update > 600):
        THRESHOLD_DB = auto_threshold()
        last_threshold_update = time.time()
        update_threshold_line()

    # Grafik verilerini güncelle
    current_time = time.time() - start_time
    timestamps.append(current_time)
    db_values.append(db)
    if len(timestamps) > MAX_POINTS:
        timestamps.pop(0)
        db_values.pop(0)

    line.set_data(timestamps, db_values)
    if THRESHOLD_DB is not None:
        threshold_line.set_xdata([timestamps[0], timestamps[-1]])
    ax.relim()
    ax.autoscale_view()

# ---------- Başlangıç ----------
print("Ses ölçüm programı başlıyor..")
THRESHOLD_DB = auto_threshold()
update_threshold_line()

ani = FuncAnimation(fig, update, interval=100)
plt.show()
