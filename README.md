# Alpha 1S — AI Modernization

Ubtech Alpha 1S humanoid robot transformed from a Bluetooth toy into a
distributed AI assistant.

## Status (Mayo 2026)

- Bluetooth SDK: **complete** (`sdk/`)
- LLM server (ROG Ally X): **running** (`rog/rog_server.py`)
- Pi voice client + gestures: **running** (`pi/raspberry_client_gestos.py`)
- STT migration (Whisper → ROG `/transcribe`): **pending**
- Dance system (`htsparser` / `pygame`): **pending elimination**

## Architecture

```
Raspberry Pi 5  ←──HTTP──→  ROG Ally X  ←──LM Studio──→  Qwen2.5-14B
      │                                                        │
  Piper TTS                                          faster-whisper
  pyaudio / mic                                      (PENDIENTE /transcribe)
      │
  Bluetooth RFCOMM
      │
  Alpha 1S (16 servos)
```

Full architecture details: [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md)

## Repository Layout

```
Alpha1s_modernization/
├── sdk/                   # Bluetooth SDK — clean Alpha 1S Python driver
│   ├── robot.py           #   Alpha1s class (all BT commands)
│   ├── bluetooth_handler.py #  RFCOMM socket, frame protocol
│   ├── constants.py       #   Calibrated servo angle sequences
│   ├── exceptions.py      #   Custom exception hierarchy
│   ├── __init__.py
│   └── requirements.txt
│
├── pi/                    # Raspberry Pi client code
│   ├── raspberry_client_gestos.py  # Main voice+gesture loop
│   ├── sequences/         #   Movement .txt files (13 sequences)
│   ├── gestures/          #   Arm gesture .txt files (14 gestures)
│   └── requirements.txt
│
├── rog/                   # ROG Ally X server code
│   ├── rog_server.py      #   Flask: /query endpoint (LLM)
│   └── requirements.txt
│
├── docs/
│   └── ARQUITECTURA.md    # Full architecture, endpoints, JSON contract
│
└── scripts/               # Utility scripts (sync, deploy)
```

## Quick Start

### ROG Ally X
```bash
cd rog
pip install -r requirements.txt
# Start LM Studio with Qwen2.5-14B-Instruct on port 1234
python rog_server.py
```

### Raspberry Pi
```bash
cd pi
pip install -r requirements.txt
# Update MAC_SERVER_URL in raspberry_client_gestos.py to ROG IP
python raspberry_client_gestos.py
```

## Bluetooth Protocol

- Device name: `ALPHA 1S`
- RFCOMM channel: 6
- Frame: `\xFB\xBF` + length + payload + checksum + `\xED`
- Key opcode: `\x23` = move all 16 servos simultaneously

## Hardware

| Device | Specs |
|--------|-------|
| Raspberry Pi 5 | 4 GB, mic on device_index=2 (pulse), 16 kHz |
| ROG Ally X | Qwen2.5-14B via LM Studio, Flask port 3000 |
| Alpha 1S | 16 servos, RFCOMM BT, internal speaker |
