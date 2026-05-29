# Alpha 1S — AI-Powered Humanoid Robot

> **Thesis project** — *"Modernization of the UBTECH Alpha 1S Humanoid Robot: Integration of a Distributed Artificial Intelligence System for Voice Control and Complex Action Execution."*
> UNAD, Colombia. Director: Fernando Rojas Rojas.

A UBTECH Alpha 1S educational robot transformed into a voice-driven, gesture-aware humanoid assistant running on distributed AI. The robot understands natural language, responds with synchronized arm gestures, and executes scripted movement sequences — all powered by a local LLM running on a handheld gaming PC.

---

## Table of Contents

- [System Architecture](#system-architecture)
- [Hardware](#hardware)
- [Repository Structure](#repository-structure)
- [Software Stack](#software-stack)
- [Getting Started](#getting-started)
  - [Server (ROG Ally X)](#server-rog-ally-x)
  - [Client (Raspberry Pi)](#client-raspberry-pi)
- [API Reference](#api-reference)
- [JSON Contract](#json-contract)
- [Servo Mapping](#servo-mapping)
- [Gesture Catalog](#gesture-catalog)
- [Sequence Catalog](#sequence-catalog)
- [USB HID Protocol](#usb-hid-protocol)
- [Known Issues](#known-issues)
- [Roadmap (Post-Thesis)](#roadmap-post-thesis)
- [Status](#status)

---

## System Architecture

```
[User] speaks close to the ROG (handheld console)
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  ASUS ROG Ally X  —  BRAIN + VOICE                  │
│  AMD Ryzen Z2 Extreme · 24 GB LPDDR5X · Windows 11  │
│                                                      │
│  Built-in mic → Wake word (offline)                  │
│             → VAD (Silero / WebRTC)                  │
│             → faster-whisper large-v3-turbo (CPU)    │
│             → Qwen2.5-7B (LM Studio, GPU)            │
│             → Piper / Kokoro TTS                     │
│             → Flask :3000                            │
│                  /query  /query_stream  /transcribe  │
└──────────────────────┬──────────────────────────────┘
                       │  TTS audio fragments (WiFi LAN)
                       │  robot commands
                       ▼
┌──────────────────────────────────────────┐
│  Raspberry Pi 5  4 GB  —  EXECUTOR       │
│                                          │
│  Receives TTS audio chunks               │
│  → buffer (200–500 ms anti-jitter)       │
│  → HAT USB Audio (C-Media, 3.5 mm jack) │
│  Receives movement commands              │
│  → alpha1s_usb.py → USB HID             │
└──────────────────────┬───────────────────┘
                       │  USB HID (0483:5750) — short cable
                       ▼
              ┌──────────────────┐
              │   Alpha 1S       │
              │   16 DOF         │
              │   16 servos      │
              │   External PSU   │
              └──────────────────┘
```

**Compute split:**
All voice processing (capture / wake / VAD / STT / LLM / TTS) and future perception + planning live on the **ROG**.
The **Pi** only plays back audio fragments and relays movement commands over USB HID.
The only network segment in the voice loop is the one-way TTS output ROG → Pi.

> **Latency budget:** STT + LLM dominate. Network transfer is negligible (16 kHz/16-bit mono ≈ 256 kbit/s; a 4-second sentence ≈ 128 KB over WiFi 5 with ~5.68 ms ping). Measure with `metrics.py` before optimizing.

---

## Hardware

| Component | Model | Details |
|---|---|---|
| Robot | UBTECH Alpha 1S, 16 DOF | USB HID `0483:5750`, HW `Alpha1_V2.0` |
| Edge controller | Raspberry Pi 5 Model B Rev 1.0, 4 GB | Executor — runs venv under `~/TDD/` |
| Edge OS | Raspberry Pi OS (Debian) | — |
| Microphone | ROG Ally X built-in | Close-field, validated in HW |
| Audio output | HAT USB Audio C-Media (on Pi) | 3.5 mm jack + speaker |
| AI server | ASUS ROG Ally X RC73XA-NH011W | AMD Ryzen Z2 Extreme, Windows 11 |
| GPU / VRAM | Radeon 890M iGPU, 12 GB dedicated of 17.8 GB | Configurable up to 16 GB (not recommended) |
| Camera *(future)* | Luxonis OAK-D Lite, 51 g | USB direct to ROG; head mount pending |
| Power supply | RIDEN RD6006 + 24 V / 5 A AC/DC | Regulated to ~7.4–7.5 V / 3 A — umbilical, no battery |
| Network | Wi-Fi 5, same LAN | Pi ↔ ROG avg ping ~5.68 ms |

### Pi USB Bus Assignment — Critical

| Bus | Device | Note |
|---|---|---|
| Bus 001 (internal) | HAT USB Audio | **Do not touch.** Moving to Bus 002 breaks audio. |
| Bus 002 / Bus 004 (blue) | Alpha 1S robot | Must use a short, quality cable. A bad cable causes `error -71` / disconnects every 2 s. |

---

## Repository Structure

```
Alpha1s_modernization/
├── client/                         # Raspberry Pi — audio playback + robot control
│   ├── raspberry_client_gestos.py  # Main client (Phase 4, active version)
│   ├── alpha1s_usb.py              # USB HID transport driver
│   ├── stream_parser.py            # SSE streaming parser (Phase 4)
│   ├── metrics.py                  # Latency logger t0–t7 → CSV
│   ├── es_MX-claude-high.onnx      # Piper TTS voice model (Spanish)
│   ├── sequences/                  # Full-body movement files (12 files)
│   │   ├── mover_adelante.txt
│   │   ├── mover_atras.txt
│   │   ├── mover_a_la_derecha.txt
│   │   ├── mover_a_la_izquierda.txt
│   │   ├── girar_a_la_derecha.txt
│   │   ├── girar_a_la_izquierda.txt
│   │   ├── punetazo_derecho.txt
│   │   ├── punetazo_izquierdo.txt
│   │   ├── flexiones_de_pecho.txt
│   │   ├── posicion_inicial.txt
│   │   ├── levantarse_desde_el_frente.txt
│   │   └── levantarse_desde_la_espalda.txt
│   └── gestures/                   # Arm-only gesture files (12 files, run parallel to TTS)
│       ├── saludar.txt
│       ├── despedirse.txt
│       ├── presentarse.txt
│       ├── brazos_abiertos_bienvenida.txt
│       ├── pensar.txt
│       ├── afirmar.txt
│       ├── enfatizar_breve.txt
│       ├── senalar_adelante.txt
│       ├── explicar_derecha.txt
│       ├── explicar_izquierda.txt
│       ├── explicar_ambos.txt
│       └── hablar_relajado.txt
│
├── server/                         # ROG Ally X — LLM + STT + TTS + Flask
│   ├── rog_server_fase4.py         # Flask :3000 — /query + /query_stream + /transcribe
│   ├── alpha1s_prompt.py           # System prompt + JSON schema (single source of truth)
│   └── benchmark.py                # Phase 6: TTFT / tok/s / valid JSON / gestures per model
│
├── simulation/                     # ROS2 + Gazebo work (ABANDONED — kept as reference)
│   └── alpha1s_bringup/
│       ├── urdf/alpha1s.urdf.xacro # URDF v3 — reusable for arm IK
│       ├── meshes/visual/          # 18 STLs (Blender 5.0)
│       ├── meshes/collision/       # 18 simplified STLs (convex hull)
│       ├── launch/
│       │   ├── display.launch.py
│       │   └── gazebo.launch.py
│       └── config/controllers.yaml
│
├── docs/                           # Reference documentation
│   ├── Alpha1_Series_Bluetooth_communication_protocol.pdf
│   └── arquitectura.md
│
└── README.md
```

---

## Software Stack

### Server (ROG Ally X)

| Layer | Technology | Status |
|---|---|---|
| LLM runtime | LM Studio 0.4.12 + Qwen2.5-7B-Instruct | ✅ Active (~20 tok/s) |
| LLM alternative | Qwen2.5-3B-Instruct | ✅ Ready (~40 tok/s) |
| LLM backend | llama.cpp + Vulkan (Radeon 890M) | ✅ |
| STT | faster-whisper large-v3-turbo, CPU int8 | ✅ |
| TTS | Piper (current) / Kokoro-82M (candidate) | ✅ / evaluate |
| API server | Flask :3000 | ✅ |
| JSON enforcement | `response_format: json_schema` | ✅ |
| Streaming | SSE via `/query_stream` + `stream_parser.py` | ✅ code / ⏳ HW test |
| Metrics | `metrics.py` → CSV (t0–t7) | ✅ |

### Client (Raspberry Pi)

| Layer | Technology | Status |
|---|---|---|
| Robot transport | `alpha1s_usb.py` — direct `/dev/hidrawX` | ✅ USB HID |
| Audio playback | pyaudio + HAT USB Audio | ✅ |
| Gesture execution | `.txt` frames in daemon thread | ✅ |
| Heartbeat | USB HID opcode `0x08` every 8 s | ✅ |
| Wake word *(legacy)* | `speech_recognition` + Google STT on Pi | 🔄 migrating to ROG |

---

## Getting Started

### Prerequisites

**Server (ROG Ally X / Windows 11)**
- Python 3.10+
- [LM Studio 0.4.12](https://lmstudio.ai/) with Qwen2.5-7B-Instruct loaded
- `pip install flask faster-whisper openai`
- Windows encoding fix already in `rog_server_fase4.py` (`sys.stdout.reconfigure(encoding='utf-8')`)

**Client (Raspberry Pi 5 / Raspberry Pi OS)**
- Python 3.10+ with a venv (recommended: `~/TDD/`)
- `pip install pyaudio numpy requests`
- Piper TTS binary in PATH, `es_MX-claude-high.onnx` in `client/`
- udev rule for USB HID access (no `sudo`):

```bash
# /etc/udev/rules.d/99-alpha1s.rules
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="0483", ATTRS{idProduct}=="5750", GROUP="plugdev", MODE="0660"

sudo udevadm control --reload-rules && sudo udevadm trigger
sudo usermod -aG plugdev $USER
```

### Server (ROG Ally X)

1. Start LM Studio and load `Qwen2.5-7B-Instruct`. Verify the server is running on `localhost:1234`.

2. Start the Flask server:

```bash
cd server/
python rog_server_fase4.py
# → Listening on 0.0.0.0:3000
```

3. Note the ROG's LAN IP (`ipconfig`) — the client needs it.

### Client (Raspberry Pi)

1. Update `ROG_SERVER_URL` in `raspberry_client_gestos.py`:

```python
ROG_SERVER_URL = "http://<ROG_LAN_IP>:3000"
```

2. Connect the robot via USB to a **blue port** (Bus 002 or Bus 004) on the Pi.

3. Power the robot through the external umbilical (RIDEN RD6006, ~7.4–7.5 V / 3 A). **The robot has no internal battery.**

4. Run the client:

```bash
cd client/
source ~/TDD/venv/bin/activate
python raspberry_client_gestos.py
```

5. Say **"alfa"** to trigger the wake word, then speak your command.

---

## API Reference

All endpoints are served by `rog_server_fase4.py` on port `3000`.

| Method | Path | Input | Output |
|---|---|---|---|
| `POST` | `/query` | `{"text": "..."}` | `{"response": "<JSON string>"}` |
| `POST` | `/query_stream` | `{"text": "..."}` | Server-Sent Events (JSON chunks) |
| `POST` | `/transcribe` | WAV file (multipart) | `{"text": "..."}` |

**LLM parameters (active):**

| Parameter | Value |
|---|---|
| Model | `Qwen2.5-7B-Instruct` |
| Temperature | `0.4` |
| Max tokens | `256` |
| Top-p | `0.9` |
| Frequency penalty | `0.15` |
| Response format | `json_schema` |

---

## JSON Contract

`gesture_sequence` is **always present and always first**. Keys and action types are in English; `response` text is in Spanish.

### Type 1 — Conversational (with gestures)

```json
{
  "gesture_sequence": ["saludar", "presentarse"],
  "response": "Hola, soy Alpha 1S. ¿En qué puedo ayudarte?"
}
```

### Type 2 — Static pose

```json
{
  "gesture_sequence": [],
  "action": "execute_pose",
  "parameters": {"pose_name": "hands_up"},
  "response": "Levantando los brazos."
}
```

Available poses: `init`, `hands_up`

### Type 3 — Movement sequence

```json
{
  "gesture_sequence": [],
  "action": "execute_sequence",
  "parameters": {"sequence_name": "mover_adelante"},
  "response": "Caminando hacia adelante."
}
```

### Type 4 — LED control

```json
{
  "gesture_sequence": [],
  "action": "control_led",
  "parameters": {"state": true},
  "response": "Encendiendo luces."
}
```

### Gesture fallback (client-side)

If `gesture_sequence` is absent or empty and `response` has ≥ 4 words, the client selects a fallback gesture based on speech duration:

| Estimated duration | Fallback gesture(s) |
|---|---|
| ≤ 3.5 s | `enfatizar_breve` |
| 3.5 – 7 s | `explicar_derecha`, `afirmar` |
| > 7 s | `explicar_derecha`, `hablar_relajado`, `explicar_izquierda` |

### Qwen language leak mitigation

Qwen2.5-7B can switch to Chinese mid-response. `rog_server_fase4.py` handles this with: (1) reinforced language instruction in system prompt, (2) post-generation CJK detection (`U+4E00–U+9FFF`), (3) automatic retry, (4) truncation at first CJK character if the issue persists. If it remains frequent, switch to the 3B model.

---

## Servo Mapping

Servo IDs `0–15` (robot firmware uses `1–16` — `alpha1s_usb.py` handles the offset).

| ID | Joint | Notes |
|---|---|---|
| 0 | Right Shoulder fwd/back | 0 = forward, 180 = back |
| 1 | Right Shoulder up/down | 0 = down, 180 = up |
| 2 | Right Elbow | 0 = in, 180 = out |
| 3 | Left Shoulder fwd/back | **inverted** — 180 = forward, 0 = back |
| 4 | Left Shoulder up/down | **inverted** — 180 = down, 0 = up |
| 5 | Left Elbow | **inverted** — 180 = in, 0 = out |
| 6 | Right Hip Pitch | — |
| 7 | Left Hip Pitch | — |
| 8 | Right Hip Roll | — |
| 9 | Left Hip Roll | — |
| 10 | Right Knee | — |
| 11 | Left Knee | — |
| 12 | Right Ankle Pitch | — |
| 13 | Left Ankle Pitch | — |
| 14 | Right Ankle Roll | — |
| 15 | Left Ankle Roll | — |

> ⚠️ **Arm axes are asymmetric between sides.** Never assume mirrored values will produce mirrored poses.
> ⚠️ **Leg values (IDs 6–15) are sacred for gestures.** Gestures only move arm servos (IDs 0–5). Any motion involving legs is `execute_sequence`, not a gesture.

### INIT pose (canonical — all gestures return here)

```python
[90, 0, 90, 90, 177, 90,   90, 60, 76, 110, 90, 90, 120, 104, 70, 90]
# A0  A1  A2  A3  A4   A5  A6  A7  A8  A9  A10 A11  A12  A13 A14 A15
```

> ⚠️ The pose `[90, 90, 90, 90, 90, 90, ...]` is **obsolete**. Do not use it.

### Anti-collision laws (empirically verified on hardware)

| Law | Rule |
|---|---|
| 1 — Safe Entry | To bring elbow to chest: first raise shoulder with elbow extended, then close elbow. |
| 2 — Exit / Rescue | Never go from closed elbow directly to INIT. First extend elbow to 90° in one frame, then lower shoulder. |
| 3 — Staggering | To cross arms: one shoulder must be higher than the other before closing elbows, or fists collide. |

---

## Gesture Catalog

Gestures move only arm servos (IDs 0–5). They run in a daemon thread parallel to TTS playback. Files live in `client/gestures/`.

| Name | Duration |
|---|---|
| `enfatizar_breve` | 2.4 s |
| `afirmar` | 2.4 s |
| `senalar_adelante` | 2.9 s |
| `presentarse` | 3.0 s |
| `pensar` | 3.0 s |
| `explicar_derecha` | 3.1 s |
| `explicar_izquierda` | 3.1 s |
| `saludar` | 3.5 s |
| `despedirse` | 4.0 s |
| `brazos_abiertos_bienvenida` | 4.0 s |
| `explicar_ambos` | 5.3 s |
| `hablar_relajado` | 5.4 s |

---

## Sequence Catalog

Full-body movement sequences. Files live in `client/sequences/`. The list must stay synchronized across three places: the `sequences/` directory, `SEQUENCE_FILES` in the client, and the examples in the server system prompt.

| Sequence name | Description |
|---|---|
| `mover_adelante` | Walk forward |
| `mover_atras` | Walk backward |
| `mover_a_la_derecha` | Side-step right |
| `mover_a_la_izquierda` | Side-step left |
| `girar_a_la_derecha` | Turn right (yaw) |
| `girar_a_la_izquierda` | Turn left (yaw) |
| `punetazo_derecho` | Right punch |
| `punetazo_izquierdo` | Left punch |
| `flexiones_de_pecho` | Push-ups |
| `posicion_inicial` | Return to standing INIT |
| `levantarse_desde_el_frente` | Stand up from face-down |
| `levantarse_desde_la_espalda` | Stand up from back-down |

### Sequence file format

Each line in a `.txt` file:

```
[a0, a1, ..., a15]  speed_units  time_ms
```

- 16 servo angles (`0–180°`)
- `time_ms` — hold duration in milliseconds before the next frame
- `speed_units` — ignored by the client (only `time_ms` is used)
- A repeated frame = hold the pose

---

## USB HID Protocol

Protocol version `V20151215`. Framing: `FB BF [length] [cmd] [params...] [CHECK] ED`

Checksum: `CHECK = (length + cmd + sum(params)) & 0xFF`

Responses start directly with `FB BF` — no HID report ID prefix.

| Opcode | Name | Notes |
|---|---|---|
| `0x08` | Heartbeat | `FB BF 04 08 00 0C ED` — sent by Pi every 8 s |
| `0x0D` | LED control | param: `0x00` = off, `0x01` = on |
| `0x18` | Battery | `[volt_hi][volt_lo][charge][level 0–100]` — ⚠️ behavior changes with external PSU (no battery); re-verify |
| `0x20` | HW version | Response: ASCII string until `0xED` |
| `0x22` | Single servo | `[id][angle][speed][interval_lo][interval_hi]` |
| `0x23` | Multi servo | `[a0..a15][speed][interval]` ← primary motion command |
| `0x25` | Read all angles | Response: 16 angle bytes starting at position 4 |

---

## Known Issues

| # | Issue | Where | Priority |
|---|---|---|---|
| 1 | Wake word and VAD still run on the Pi (legacy flow) | `raspberry_client_gestos.py` | 🔴 Pending migration to ROG |
| 2 | TTS still synthesized on Pi (legacy flow) | `raspberry_client_gestos.py` | 🔴 Pending migration to ROG |
| 3 | `legacy_dance` system (`htsparser` + `pygame`) not yet removed | client | 🟡 Isolate or delete |
| 4 | `ROG_SERVER_URL` hardcoded — no env var / config file | client | 🟡 |
| 5 | Streaming SSE (`/query_stream`) code complete but not hardware-tested | server + client | 🟡 |
| 6 | Phase 6 benchmark (`benchmark.py`) not yet run | server | 🟡 Required for thesis |
| 7 | Battery telemetry (`0x18`) semantics undefined with external PSU | `alpha1s_usb.py` | 🟡 Re-measure |
| 8 | `reverencia` mapped in `SEQUENCE_FILES` as `sequences/` but file lives in `gestures/` | client | 🟠 |
| 9 | Qwen2.5-7B CJK language leak under long responses | server | 🟠 Mitigation in place |
| 10 | CoM shifted up/forward after battery removal → worse gait stability | hardware | ⚪ Addressed in Phase B |

---

## Roadmap (Post-Thesis)

The cognitive axis is **frozen** as the final thesis deliverable. The RL / simulation axis was **abandoned** (not paused) — see below. Post-thesis work follows a deliberative architecture: *metric perception → symbolic LLM planning → scripted primitive → visual verification*.

### Why RL was abandoned

1. The working surface is a 1.5 × 0.7 m table, not a floor — the robot barely walks on it and needs to perceive, reach, and avoid edges, not achieve dynamic locomotion.
2. Sim-to-real for dynamic gait on position-only servos without torque feedback is nearly intractable (cf. Hwangbo et al., 2019, *Science Robotics*).
3. Low learning yield per effort compared to the perception + manipulation path.

The URDF, STL meshes, and inertia data are preserved and will be reused for arm IK in Phase E.

### Phases A–F

| Phase | Description | Key outcome |
|---|---|---|
| **A** | Real servo mapping + context package | Semantic table of all 16 servos: part, axis, safe range, sign/inversion. Anti-collision laws consolidated. |
| **B** | Stabilize gait (minimum viable, not perfect) | 10 steps without falling post-umbilical. Static stability concept — support polygon. |
| **C** | Camera: calibration + pose estimation | OAK-D fixed to head. Intrinsics calibrated. ArUco / AprilTag on box and table corners. Box pose in base frame, error < ~2 cm. |
| **D** | Close the loop (fix lateral drift) | FSM on ROG: perceive heading → rotate if off-center, step if centered, repeat. Discrete visual servoing. Reach box at 40 cm ≥ 8/10. |
| **D.5** *(optional)* | Gait optimization with camera as fitness | Parameterize gait; fitness = straight distance / drift (measured by camera); optimize with CMA-ES. Skip if Phase D suffices. |
| **E** | Grasping: arm IK + blind zone | Known box pose → 3-DOF arm IK → forearm pinch grip for last ~20 cm (below OAK-D min range, open-loop). Precipice detection mandatory. |
| **F** | LLM planner + verification + replan | LLM sequences symbolic skills (`search → approach → grasp → carry → release`). Pre/post verification with camera; replan on failure. LLM never computes geometry — numbers come from perception. |

---

## Status

| Axis | Status |
|---|---|
| Cognitive (voice + LLM + gestures) | ✅ **Frozen — thesis final deliverable** |
| Simulation / RL | ❌ **Abandoned** (URDF/STL assets preserved) |
| Advanced robotics (Phases A–F) | 🔭 **Post-thesis — Phase A is next** |

**Only pending item before thesis submission:** run Phase 6 benchmark (`benchmark.py`) comparing Qwen2.5-7B vs 3B — TTFT, tok/s, JSON validity rate, gesture generation rate.

---

## Hardware Engineering Notes

- **Less weight ≠ more stable.** Removing the battery (which sat low and centered) raised the CoM and shifted it forward. The gait degrades without it. The suspension marionette is functional, not cosmetic.
- **Lateral drift is fixed by closing the loop with the camera**, not by refining the open-loop gait.
- **The UBTECH simulator is a pose/animation editor, not a physics simulator.** It does not validate balance or contact. Only the physical robot validates balance.
- **An AI cannot evaluate balance or collision from servo numbers alone.** It is useful for structural manipulation of sequences (mirror, interpolate, retime, splice with anti-collision rules, check limits, generate variations, interpret described failures). It must never assert that a new frame is stable — propose and validate on hardware.

---

## References

- Hwangbo, J. et al. (2019). Learning agile and dynamic motor skills for legged robots. *Science Robotics*, 4(26).
- Ahn, M. et al. (2022). Do as I Can, Not as I Say: Grounding Language in Robotic Affordances (SayCan). *arXiv:2204.01691*.
- Liang, J. et al. (2022). Code as Policies: Language Model Programs for Embodied Control. *arXiv:2209.07753*.
- Craig, J. J. (2005). *Introduction to Robotics: Mechanics and Control* (3rd ed.). Pearson.
- Siciliano, B. et al. (2009). *Robotics: Modelling, Planning and Control*. Springer.
- UBTECH Robotics. *Alpha 1S Bluetooth Communication Protocol* (internal, V20151215).