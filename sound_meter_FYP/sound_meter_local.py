#!/usr/bin/env python
import pyaudio
import spl_lib as spl
from scipy.signal import lfilter
import numpy
import time
import csv
import os

CHUNK = 4800
FORMAT = pyaudio.paInt16
CHANNEL = 1
RATE = 48000

NUMERATOR, DENOMINATOR = spl.A_weighting(RATE)

pa = pyaudio.PyAudio()

default_index = pa.get_default_input_device_info()['index']
default_name = pa.get_default_input_device_info()['name']
print(f"Using input device [{default_index}]: {default_name}")

# To use a different device, set DEVICE_INDEX to its index from the list above
DEVICE_INDEX = None  # None = system default

stream = pa.open(format=FORMAT,
                 channels=CHANNEL,
                 rate=RATE,
                 input=True,
                 input_device_index=DEVICE_INDEX,
                 frames_per_buffer=CHUNK)


BAR_WIDTH = 40
DB_MIN = 30
DB_MAX = 100
DB_FLOOR = 10         # below this is treated as silence / mic disconnect
CHANGE_THRESHOLD = 3  # dB — set to 0 to display every reading

LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')


def get_log_writer():
    os.makedirs(LOGS_DIR, exist_ok=True)
    filename = os.path.join(LOGS_DIR, time.strftime("%Y-%m-%d") + ".csv")
    is_new = not os.path.exists(filename)
    f = open(filename, 'a', newline='')
    writer = csv.writer(f)
    if is_new:
        writer.writerow(['timestamp', 'decibel', 'status'])
    return f, writer


def status_label(db):
    if db < 40:
        return "LOW   "
    elif db <= 70:
        return "MEDIUM"
    else:
        return "HIGH  "


def render_bar(db):
    clamped = max(DB_MIN, min(DB_MAX, db))
    filled = int((clamped - DB_MIN) / (DB_MAX - DB_MIN) * BAR_WIDTH)
    bar = "█" * filled + "░" * (BAR_WIDTH - filled)
    label = status_label(db)
    timestamp = time.strftime("%H:%M:%S")
    return f"\r{timestamp} | {bar} | {db:6.1f} dB(A) | {label}"


def listen():
    log_file, log_writer = get_log_writer()
    print(f"Logging to: logs/{time.strftime('%Y-%m-%d')}.csv")
    print("Listening... (Ctrl+C to stop)\n")
    error_count = 0
    last_decibel = None
    try:
        while True:
            try:
                block = stream.read(CHUNK, exception_on_overflow=False)
            except IOError as e:
                error_count += 1
                print(f"\n({error_count}) Error recording: {e}")
            else:
                decoded_block = numpy.frombuffer(block, dtype='int16')
                y = lfilter(NUMERATOR, DENOMINATOR, decoded_block)
                decibel = 20 * numpy.log10(spl.rms_flat(y))

                if not numpy.isfinite(decibel) or decibel < DB_FLOOR:
                    print(f"\r{time.strftime('%H:%M:%S')} | {'░' * BAR_WIDTH} | -- SILENCE / NO SIGNAL --      ", end="", flush=True)
                    last_decibel = None
                    continue

                if last_decibel is None or abs(decibel - last_decibel) >= CHANGE_THRESHOLD:
                    last_decibel = decibel
                    log_writer.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), f"{decibel:.2f}", status_label(decibel).strip()])
                    log_file.flush()
                    print(render_bar(decibel), end="", flush=True)
    finally:
        log_file.close()


if __name__ == '__main__':
    try:
        listen()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()
