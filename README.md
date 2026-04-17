# soundmeterFYP

A distributed real-time sound level monitoring system built as a Final Year Project. Captures microphone audio, computes A-weighted decibel readings, and streams them over RabbitMQ. Includes a standalone local mode with a live terminal bar graph — no RabbitMQ required.

## Architecture

The pipeline has three layers:

1. **Audio capture** — `sound_meter_FYP/sound_meter_final.py` streams 16-bit mono audio at 48 kHz using PyAudio (4800-sample chunks).
2. **Signal processing** — `sound_meter_FYP/spl_lib.py` applies an IEC 1672 A-weighting digital filter (SciPy) and computes `20 × log10(RMS)` for dB(A).
3. **Messaging** — `pika` publishes decibel values to a RabbitMQ `decibel` queue; `receive_sound.py` consumes them.

`sound_meter_FYP/sound_meter_local.py` is a self-contained local mode — same audio pipeline but outputs directly to the terminal with no RabbitMQ dependency.

## Local Setup (no RabbitMQ)

Uses a Python virtual environment. Run from the repo root:

```bash
# Start — creates venv on first run, installs deps, launches meter
bash start.sh

# Stop — kills a backgrounded instance from another terminal
bash stop.sh
```

The meter prints a live updating bar to the terminal:
```
14:32:01 | ████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░ |   52.3 dB(A) | MEDIUM
```

On startup it prints the active input device. To switch devices, set `DEVICE_INDEX` in `sound_meter_FYP/sound_meter_local.py` to the index shown.

### Signal quality settings

| Constant | Default | Effect |
|---|---|---|
| `CHANGE_THRESHOLD` | `3` dB | Bar only updates when level shifts by ≥3 dB. Set to `0` to show every reading. |
| `DB_FLOOR` | `10` dB | Below this the bar shows `SILENCE / NO SIGNAL` — catches dead mic or `-inf` readings. |

## Distributed Setup (RabbitMQ)

Designed for Raspberry Pi / ARM Linux. Start RabbitMQ at `172.17.14.179:5672`, then:

```bash
# Producer — capture mic and publish dB readings
python sound_meter_FYP/sound_meter_final.py

# Consumer — receive and print dB readings
python receive_sound.py
```

Conda environment spec (Python 3.4, ARM/Linux): `sound_meter_FYP/requirements_conda.txt`

## Key Configuration

| Setting | File | Default |
|---|---|---|
| RabbitMQ host | `sound_meter_final.py`, `receive_sound.py` | `172.17.14.179` |
| Queue name | both | `decibel` |
| Sample rate | both | 48 000 Hz |
| Chunk size | both | 4 800 samples |
| Change threshold | `sound_meter_final.py` | 3 dB |

## Dependencies

- **PyAudio ≥ 0.2.14** — PortAudio bindings (pre-built wheels for Windows/Linux/macOS)
- **NumPy / SciPy** — A-weighting filter and RMS calculation
- **pika** — RabbitMQ/AMQP client (distributed mode only)

## Roadmap

### Transcription

Add opt-in speech-to-text output running alongside the dB meter.

**Proposed backend:** [OpenAI Whisper](https://github.com/openai/whisper) (local, free, no API key)

```bash
pip install openai-whisper
```

**Implementation steps:**

1. **Speech buffer** — accumulate audio chunks into a rolling 3–5 s buffer in parallel with the dB loop.
2. **Utterance detection** — flush the buffer when dB drops below ~40 dB after a voiced period (end-of-speech trigger).
3. **Background transcription thread** — pass the flushed buffer to Whisper in a separate thread so the bar loop is never blocked. Model size tradeoff: `tiny` (fast, less accurate) → `base` → `small` (slower, more accurate).
4. **Terminal output** — print the recognised phrase on a second line beneath the live bar, refreshed per utterance.
5. **`--transcribe` flag** — keep it opt-in so plain dB monitoring has zero overhead.

**Data flow:**
```
mic chunks ──► dB bar (every 100 ms)
           └──► speech buffer ──► silence trigger ──► Whisper thread ──► transcript line
```
