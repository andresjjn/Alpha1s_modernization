# Alpha 1S — Architecture (Mayo 2026)

## Pipeline

```
Pi 5 4GB                          ROG Ally X (Windows/Ubuntu)
─────────────────────────         ─────────────────────────────────
wake word (Google STT)
  → record WAV (pyaudio)
  → POST /transcribe ──────────→  faster-whisper large-v3-turbo (CPU int8)
                                    → transcript text
  ← text ←─────────────────────
  → POST /query ───────────────→  Qwen2.5-14B-Instruct (LM Studio, GPU)
                                    → JSON action
  ← JSON ←─────────────────────
  → dispatch action
      ├─ response+gestures → Piper TTS + servo gestures (parallel)
      ├─ execute_pose      → sdk.servo_write_all()
      ├─ execute_sequence  → load .txt → sdk.servo_write_all()
      ├─ execute_dance     → htsparser + pygame (PENDIENTE migrar)
      └─ control_led       → sdk.led_handler()
  → Bluetooth RFCOMM ──────────→  Alpha 1S robot (16 servos)
```

## Endpoints (ROG Ally X, port 3000)

| Method | Path | Input | Output |
|--------|------|-------|--------|
| POST | `/query` | `{"text": "..."}` | `{"response": "<JSON string>"}` |
| POST | `/transcribe` | WAV file (multipart) | `{"text": "..."}` — **PENDIENTE IMPLEMENTAR** |

## JSON Contract

### Conversational (with optional gestures)
```json
{
  "response": "Hola, soy Alpha 1S.",
  "gesture_sequence": ["brazos_abiertos_bienvenida", "presentarse"]
}
```

### Physical action — static pose
```json
{"action": "execute_pose", "parameters": {"pose_name": "hands_up"}}
```
Available poses: `init`, `hands_up`

### Physical action — movement sequence
```json
{"action": "execute_sequence", "parameters": {"sequence_name": "mover_adelante"}}
```
Available sequences (files in `pi/sequences/`):
`mover_adelante`, `mover_atras`, `mover_a_la_derecha`, `mover_a_la_izquierda`,
`girar_a_la_derecha`, `girar_a_la_izquierda`, `punetazo_derecho`, `punetazo_izquierdo`,
`flexiones_de_pecho`, `levantarse_desde_el_frente`, `levantarse_desde_la_espalda`,
`posicion_inicial`, `saludo_inicial`, `reverencia`

### Physical action — dance / choreography
```json
{"action": "execute_dance", "parameters": {"dance_name": "frozen"}}
```
Uses legacy `.hts` files + pygame. PENDIENTE eliminar o aislar.

### LED control
```json
{"action": "control_led", "parameters": {"state": true}}
```

## Gesture Catalog

Gestures only move arm servos (IDs 0–5). Legs remain locked in `init` pose.
Files live in `pi/gestures/*.txt`. Same format as sequences.

| Name | Duration |
|------|----------|
| `enfatizar_breve` | 2.4 s |
| `afirmar` | 2.4 s |
| `presentarse` | 3.0 s |
| `senalar_adelante` | 2.9 s |
| `pensar` | 3.0 s |
| `explicar_derecha` | 3.1 s |
| `explicar_izquierda` | 3.1 s |
| `brazos_abiertos_bienvenida` | 4.0 s |
| `explicar_ambos` | 5.3 s |
| `hablar_relajado` | 5.4 s |
| `despedirse` | 4.0 s |
| `saludar` | 3.5 s |
| `error` | 3.5 s |

## Sequence File Format

Each line in a `.txt` file:
```
[a0, a1, ..., a15] + [speed_units, time_ms]
```
- 16 servo angles (0–180°)
- `time_ms` = how long the robot holds the frame before the next one
- `speed_units` = ignored by the client (only `time_ms` is used)

## Hardware

| Device | Role | Details |
|--------|------|---------|
| Raspberry Pi 5 (4 GB) | Voice client | mic device_index=2 (pulse), RATE=16000, pyaudio |
| ROG Ally X | LLM + STT server | Qwen2.5-14B via LM Studio, faster-whisper large-v3-turbo CPU int8, port 3000 |
| Ubtech Alpha 1S | Robot body | Bluetooth RFCOMM channel 6, device name "ALPHA 1S", 16 servos IDs 0–15 |

## Servo Mapping

| ID | Joint |
|----|-------|
| 0 | Shoulder R Roll |
| 1 | Shoulder L Roll |
| 2 | Arm R Pitch |
| 3 | Arm L Pitch |
| 4 | Elbow R |
| 5 | Elbow L |
| 6 | Hip R Pitch |
| 7 | Hip L Pitch |
| 8 | Hip R Roll |
| 9 | Hip L Roll |
| 10 | Knee R |
| 11 | Knee L |
| 12 | Ankle R Pitch |
| 13 | Ankle L Pitch |
| 14 | Ankle R Roll |
| 15 | Ankle L Roll |

## Known Issues / Pending Work

1. **`/transcribe` endpoint missing** — Pi still runs Whisper locally. Add to `rog/rog_server.py`.
2. **`play_choreography()` still uses `htsparser` + `pygame`** — legacy dance system not yet migrated.
3. **`raspberry_client_gestos.py` imports** — `audioop`, `whisper`, `htsparser`, `pygame` remain. Must be removed after STT migration.
4. **`MAC_IP` / `MAC_SERVER_URL`** — hardcoded MacBook IP. Must be updated to ROG Ally X LAN IP.
5. **`reverencia` file location** — `SEQUENCE_FILES` maps it to `sequences/reverencia.txt` but the file lives in `gestures/`. Either move the file or update the path.
6. **LED opcode** — `led_handler()` uses `0x08`. Verify against Alpha1_Series_Bluetooth_communication_protocol PDF before deploying.
