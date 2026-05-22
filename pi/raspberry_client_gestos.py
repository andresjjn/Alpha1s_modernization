#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
raspberry_client.py
Cliente de voz para Alpha 1S. Contrato JSON: claves en INGLES.

Archivo en ASCII puro. Los acentos del castellano se expresan con
escapes Unicode (é = e con tilde, ñ = enie, etc.) para
que Piper los pronuncie bien sin meter chars no-ASCII en el codigo.

EXTENSION MAYO 2026: gesture_sequence
-------------------------------------
El LLM puede acompanar respuestas tipo "response" con una lista de
gestos corporales que se ejecutan EN PARALELO con la voz de Piper.

Contrato extendido:
  {
    "response": "Hola, soy Alpha 1S",
    "gesture_sequence": ["brazos_abiertos_bienvenida", "presentarse"]
  }

Los gestos solo mueven los servos de los brazos (IDs 0-5). Las
piernas (IDs 6-15) permanecen rigidamente en la pose 'init' real
para no comprometer el equilibrio mientras el robot habla.

PENDIENTE DE MIGRAR:
  - import whisper       -> STT ahora corre en ROG via /transcribe
  - import audioop       -> eliminado en nueva arquitectura
  - import htsparser     -> eliminado (sistema de coreografia antiguo)
  - import pygame        -> eliminado (musica de coreografia antigua)
  - MAC_IP               -> actualizar a IP del ROG Ally X
  - transcribe_audio_local() -> reemplazar por llamada HTTP a ROG /transcribe
"""

import os
import wave
import whisper
import requests
import pyaudio
import speech_recognition as sr
import audioop
import subprocess
import json
from time import sleep
import ast
import threading

from alpha1s import Alpha1S
import htsparser
import pygame

# ---------- CONFIG ----------
WAKE_WORD = "alfa"
WHISPER_MODEL_SIZE = "base"
WHISPER_LANGUAGE = "es"
TEMP_AUDIO_FILENAME = "temp_recording.wav"
MAC_IP = "192.168.1.12"
MAC_SERVER_URL = "http://" + MAC_IP + ":3000/query"

RATE = 16000
CHUNK = 1024
CHANNELS = 1
FORMAT = pyaudio.paInt16
SILENCE_THRESHOLD = 300
SILENCE_DURATION = 2
MAX_RECORDING_SECONDS = 30

VOICE_MODEL_PATH = "es_MX-claude-high.onnx"

# ---------- SALUDO INICIAL ----------
# Texto que dice Piper al arrancar. Usa escapes Unicode para mantener
# el archivo ASCII puro pero que la pronunciacion sea correcta.
# Equivale a: "Saludos Andres, en que te puedo ayudar hoy?"
STARTUP_GREETING_TEXT = (
    "Saludos Andrés, ¿en qué te puedo ayudar hoy?"
)

# ---------- CATALOGOS ----------
# Claves en INGLES (el LLM las emite); valores son angulos de los 16 servos.
# Mapeo de servos:
#   0: Hombro D Roll      1: Hombro I Roll      2: Brazo D Pitch    3: Brazo I Pitch
#   4: Codo D             5: Codo I             6: Cadera D Pitch   7: Cadera I Pitch
#   8: Cadera D Roll      9: Cadera I Roll     10: Rodilla D       11: Rodilla I
#  12: Tobillo D Pitch   13: Tobillo I Pitch   14: Tobillo D Roll  15: Tobillo I Roll
STATIC_POSES = {
    # Pose neutra: brazos caidos, piernas rectas. Postura estable de pie.
    "init":     [90, 0, 90, 90, 177, 90, 90, 60, 76, 110, 90, 90, 120, 104, 70, 90],

    # Manos arriba: brazo izquierdo elevado por encima de la cabeza.
    "hands_up": [90, 180, 90, 90, 0, 90, 90, 60, 76, 110, 90, 90, 120, 104, 70, 90],
}

SEQUENCE_FILES = {
    "mover_adelante":                "mover_adelante.txt",
    "mover_atras":                   "mover_atras.txt",
    "girar_a_la_derecha":            "girar_a_la_derecha.txt",
    "girar_a_la_izquierda":          "girar_a_la_izquierda.txt",
    "punetazo_derecho":              "punetazo_derecho.txt",
    "punetazo_izquierdo":            "punetazo_izquierdo.txt",
    "flexiones_de_pecho":            "flexiones_de_pecho.txt",
    "levantarse_desde_el_frente":    "levantarse_desde_el_frente.txt",
    "levantarse_desde_la_espalda":   "levantarse_desde_la_espalda.txt",
    "mover_a_la_derecha":            "mover_a_la_derecha.txt",
    "mover_a_la_izquierda":          "mover_a_la_izquierda.txt",
    "posicion_inicial":              "posicion_inicial.txt",
    "saludo_inicial":                "saludo_inicial.txt",
    "reverencia":                    "reverencia.txt",
}

AVAILABLE_CHOREOGRAPHIES = {
    "frozen", "beat_it", "gangnam_style", "happy_birthday",
    "just_the_way_you_are", "moves_like_jagger", "remix",
    "sorry_sorry", "that_power", "trojan_horse", "waka_waka",
    "presentacion",
    "sirius", "default", "default_foot1", "bueno",
    "fall_backward_rise1", "fall_forward_rise1",
    "push_up",
    "hit_left", "hit_right",
    "left_hits_forward", "right_hits_forward",
    "left_punch", "right_punch",
    "left_slide_tackle1", "right_slide_tackle1",
    "shoot_left1", "shoot_right1",
    "move_back", "move_forward", "move_leftward", "move_rightward",
    "turn_left", "turn_right", "turn_left1", "turn_right1",
    "leftward1", "rightward1", "backward2", "forward2",
}

# ---------- CATALOGO DE GESTOS ----------
# Gestos corporales para acompanar respuestas habladas. Solo mueven
# los brazos (servos 0-5). Las piernas (6-15) se mantienen en pose
# 'init' en cada frame para no comprometer el equilibrio.
#
# Cada valor es la duracion total aproximada del gesto en segundos.
# El LLM la usa para sumar gestos hasta cubrir la duracion del audio.
GESTURE_CATALOG = {
    "enfatizar_breve":             2.4,
    "afirmar":                     2.4,
    "presentarse":                 3.0,
    "senalar_adelante":            2.9,
    "pensar":                      3.0,
    "explicar_derecha":            3.1,
    "explicar_izquierda":          3.1,
    "brazos_abiertos_bienvenida":  4.0,
    "explicar_ambos":              5.3,
    "hablar_relajado":             5.4,
    "despedirse":                  4.0,
    "saludar":                     3.5,
    "error":                       3.5,
}

GESTURES_DIR = "gestures"

# ---------- TTS ----------
def initialize_piper_voice():
    print("[PI] Verificando modelo de voz Piper...")
    if not os.path.exists(VOICE_MODEL_PATH):
        raise FileNotFoundError("Modelo de voz no encontrado: " + VOICE_MODEL_PATH)
    print("  - Modelo encontrado.")
    return VOICE_MODEL_PATH


def generate_tts_wav(text, voice_model_path, output_wav_path="response.wav"):
    """Genera el WAV con Piper. No lo reproduce. Retorna la ruta o None."""
    try:
        subprocess.run(
            ["piper", "--model", voice_model_path, "--output_file", output_wav_path],
            input=text, text=True, check=True
        )
        return output_wav_path
    except subprocess.CalledProcessError as e:
        print("[PI] Error ejecutando Piper: " + str(e))
        return None


def play_wav_file(wav_path):
    """Reproduce un WAV. Bloqueante. Limpia el archivo al final."""
    p = pyaudio.PyAudio()
    try:
        with wave.open(wav_path, "rb") as wf:
            stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                            channels=wf.getnchannels(),
                            rate=wf.getframerate(),
                            output=True)
            data = wf.readframes(CHUNK)
            while data:
                stream.write(data)
                data = wf.readframes(CHUNK)
            stream.stop_stream()
            stream.close()
    except Exception as e:
        print("[PI] Error en reproduccion: " + str(e))
    finally:
        p.terminate()
        if os.path.exists(wav_path):
            os.remove(wav_path)


def speak(text, voice_model_path):
    """Sintetiza y reproduce el texto. Sin gestos."""
    print("[PI] Hablando: " + text)
    wav_path = generate_tts_wav(text, voice_model_path)
    if wav_path:
        play_wav_file(wav_path)


def speak_with_gestures(text, voice_model_path, gesture_sequence, robot):
    """
    Reproduce el TTS y los gestos corporales EN PARALELO.

    Flujo:
      1. Genera el WAV de Piper (bloqueante, 50-500 ms).
      2. Lanza un thread que ejecuta los gestos en secuencia.
      3. Reproduce el WAV en el thread principal.
      4. Espera al thread de gestos (con margen de gracia).
      5. Al terminar, vuelve a la pose 'init' para postura segura.

    Si gesture_sequence es None/vacio o robot es None, solo habla.
    """
    # Sin gestos: ruta directa
    if not gesture_sequence or robot is None:
        speak(text, voice_model_path)
        return

    print("[PI] Hablando con gestos: " + text)
    print("[GESTURE] Secuencia solicitada: " + str(gesture_sequence))

    # 1) Generar WAV antes de lanzar el thread para sincronizar bien
    wav_path = generate_tts_wav(text, voice_model_path)
    if not wav_path:
        print("[PI] Fallo TTS. Cancelando gestos.")
        return

    # 2) Lanzar thread de gestos
    stop_event = threading.Event()

    def run_gestures():
        for gesture_name in gesture_sequence:
            if stop_event.is_set():
                print("[GESTURE] Stop recibido, abortando secuencia.")
                break
            if gesture_name not in GESTURE_CATALOG:
                print("[GESTURE] '" + gesture_name + "' no esta en el catalogo. Saltando.")
                continue
            try:
                play_gesture(gesture_name, robot)
            except Exception as e:
                print("[GESTURE] Error ejecutando '" + gesture_name + "': " + str(e))
                # Continua con el siguiente gesto sin abortar el audio

    gesture_thread = threading.Thread(target=run_gestures, daemon=True)
    gesture_thread.start()

    # 3) Reproducir audio (bloqueante) en el thread principal
    play_wav_file(wav_path)

    # 4) Esperar al thread de gestos con margen de gracia
    grace_period = 1.5  # segundos
    gesture_thread.join(timeout=grace_period)
    if gesture_thread.is_alive():
        print("[SYNC] Audio termino, senalando stop al thread de gestos.")
        stop_event.set()
        gesture_thread.join(timeout=3.0)
        if gesture_thread.is_alive():
            print("[SYNC] Advertencia: thread de gestos no termino limpiamente.")

    # 5) Volver a init para postura segura
    try:
        robot.servo_write_all(STATIC_POSES["init"], travelling=50)
        sleep(0.5)
    except Exception as e:
        print("[GESTURE] Error volviendo a init: " + str(e))


# ---------- SALUDO INICIAL ----------
def startup_greeting(robot, voice_model_path):
    print("[GREETING] Iniciando saludo de bienvenida...")
    pose_thread = None

    if robot is not None:
        def do_pose():
            try:
                play_sequence("saludo_inicial", robot)
            except Exception as e:
                print("[GREETING] Error moviendo a pose 'greeting': " + str(e))

        pose_thread = threading.Thread(target=do_pose)
        pose_thread.start()

    sleep(0.2)
    speak(STARTUP_GREETING_TEXT, voice_model_path)

    if pose_thread is not None:
        pose_thread.join()
        sleep(1)
        try:
            robot.servo_write_all(STATIC_POSES["init"], travelling=80)
            sleep(1)
        except Exception as e:
            print("[GREETING] Error volviendo a 'init': " + str(e))

    print("[GREETING] Saludo finalizado.")

# ---------- AUDIO ----------
def listen_for_wake_word(recognizer, microphone):
    print("\n[PI] Di '" + WAKE_WORD + "' para comenzar...")
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        while True:
            try:
                audio = recognizer.listen(source)
                text = recognizer.recognize_google(audio, language="es-ES").lower()
                if WAKE_WORD in text:
                    print("[PI] Palabra de activacion detectada.")
                    return True
            except (sr.UnknownValueError, sr.RequestError):
                continue


def record_audio(stream):
    print("[PI] Grabando... Habla ahora.")
    frames = []
    silent_chunks = 0
    silent_chunks_needed = int(SILENCE_DURATION * RATE / CHUNK)
    max_chunks = int(MAX_RECORDING_SECONDS * RATE / CHUNK)
    has_spoken = False

    while len(frames) < max_chunks:
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)
        rms = audioop.rms(data, 2)
        if rms >= SILENCE_THRESHOLD:
            has_spoken = True
            silent_chunks = 0
        elif has_spoken:
            silent_chunks += 1
        if has_spoken and silent_chunks > silent_chunks_needed:
            print("[PI] Silencio detectado. Grabacion finalizada.")
            return b"".join(frames)

    print("[PI] Tope maximo de grabacion alcanzado.")
    return b"".join(frames)


def save_as_wav(frames, audio_interface, filename):
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(audio_interface.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(frames)
    return filename

# ---------- STT y LLM ----------
def transcribe_audio_local(audio_filepath, model):
    print("[PI] Transcribiendo con Whisper...")
    try:
        result = model.transcribe(audio_filepath, fp16=False, language=WHISPER_LANGUAGE)
        return result["text"]
    except Exception as e:
        print("[PI] Error transcripcion: " + str(e))
        return None


def query_llm_server(text):
    print("[PI] Enviando texto al servidor LLM...")
    try:
        payload = {"text": text, "language": "es"}
        response = requests.post(MAC_SERVER_URL, json=payload, timeout=90)
        response.raise_for_status()
        llm_response_text = response.json().get("response")
        print("[PI] Respuesta LLM: '" + str(llm_response_text) + "'")
        return llm_response_text
    except requests.exceptions.RequestException as e:
        print("[PI] Error conexion servidor: " + str(e))
        return '{"response": "No pude conectar con el servidor de Inteligencia Artificial."}'

# ---------- EJECUCION DE MOVIMIENTOS ----------
def _load_frames_from_file(file_path):
    """
    Lector generico para archivos de secuencia/gesto.
    Formato por linea:  [angulos x 16] + [velocidad, tiempo_ms]
    Solo se usa el segundo valor del segundo par (tiempo_ms).
    """
    frames = []
    with open(file_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(" + ")
            angles = ast.literal_eval(parts[0])
            time_data = ast.literal_eval(parts[1])
            time_ms = time_data[1]
            frames.append({"angles": angles, "time_ms": time_ms})
    return frames


def load_sequence_from_file(sequence_name):
    filename = SEQUENCE_FILES.get(sequence_name)
    if not filename:
        return None, "Secuencia '" + sequence_name + "' no esta en el catalogo."
    file_path = os.path.join("sequences", filename)
    if not os.path.exists(file_path):
        return None, "Archivo de secuencia no encontrado: '" + file_path + "'."
    try:
        return _load_frames_from_file(file_path), None
    except Exception as e:
        return None, "Error parseando '" + file_path + "': " + str(e)


def play_sequence(sequence_name, robot):
    print("[ROBOT] Cargando secuencia '" + sequence_name + "'...")
    frames, error = load_sequence_from_file(sequence_name)
    if error:
        return None, error

    print("[ROBOT] Ejecutando '" + sequence_name + "' (" + str(len(frames)) + " frames)...")
    for frame in frames:
        angles = frame["angles"]
        time_ms = frame["time_ms"]
        travelling_units = max(1, int(time_ms / 20))
        robot.servo_write_all(angles, travelling=travelling_units)
        sleep(time_ms / 1000.0)

    robot.servo_write_all(STATIC_POSES["init"], travelling=50)
    sleep(1)
    print("[ROBOT] Secuencia '" + sequence_name + "' finalizada.")
    return "hecho"


def play_gesture(gesture_name, robot):
    """
    Ejecuta un gesto corporal (archivo en gestures/).
    Mismo formato que las secuencias. NO vuelve a 'init' al final
    porque el siguiente gesto (o el caller speak_with_gestures)
    se encarga de eso.
    """
    file_path = os.path.join(GESTURES_DIR, gesture_name + ".txt")
    if not os.path.exists(file_path):
        print("[GESTURE] Archivo no encontrado: '" + file_path + "'. Saltando.")
        return

    try:
        frames = _load_frames_from_file(file_path)
    except Exception as e:
        print("[GESTURE] Error parseando '" + file_path + "': " + str(e))
        return

    print("[GESTURE] Ejecutando '" + gesture_name + "' (" + str(len(frames)) + " frames)...")
    for frame in frames:
        angles = frame["angles"]
        time_ms = frame["time_ms"]
        travelling_units = max(1, int(time_ms / 20))
        robot.servo_write_all(angles, travelling=travelling_units)
        sleep(time_ms / 1000.0)


def play_choreography(name, robot):
    if name not in AVAILABLE_CHOREOGRAPHIES:
        return None, "Coreografia '" + name + "' no esta en el catalogo."

    action_file = "actions/" + name + ".hts"
    music_file = "music/" + name + ".mp3"

    if not os.path.exists(action_file):
        return None, "No se encontro el archivo de coreografia '" + action_file + "'."

    print("[ROBOT] Cargando coreografia desde '" + action_file + "'...")
    sequence = htsparser.parse_file(action_file)

    has_music = os.path.exists(music_file)
    music_thread = None

    def play_music():
        print("[MUSIC] Reproduciendo '" + music_file + "'...")
        pygame.mixer.music.load(music_file)
        pygame.mixer.music.play()

    if has_music:
        music_thread = threading.Thread(target=play_music)
        music_thread.start()
        sleep(0.5)
    else:
        print("[MUSIC] Sin musica asociada -- coreografia silenciosa.")

    print("[ROBOT] Iniciando coreografia.")
    for frame in sequence:
        angles = frame["servos"]
        travel_time_ms = frame["time"]
        travelling_units = max(1, int(travel_time_ms / 20))
        robot.servo_write_all(angles, travelling=travelling_units)
        sleep(travel_time_ms / 1000.0)

    if music_thread:
        music_thread.join()
    print("[ROBOT] Coreografia finalizada.")
    return "He terminado la coreografia " + name.replace("_", " ") + ".", None

# ---------- DESPACHADOR ----------
def handle_robot_action(action_json, robot):
    """
    Despacha la respuesta del LLM.

    Retorna (response_text, gesture_sequence, error):
      - response_text: texto a hablar (puede ser None)
      - gesture_sequence: lista de gestos a ejecutar en paralelo
                          al TTS (solo aplica si action_type es None)
                          puede ser None
      - error: mensaje de error si aplica (None en caso normal)
    """
    try:
        action_data = json.loads(action_json)
        action_type = action_data.get("action")
        parameters = action_data.get("parameters") or {}

        # Caso 1: conversacional (sin "action") -> response + gestos opcionales
        if not action_type:
            response_text = action_data.get("response", action_json)
            gesture_sequence = action_data.get("gesture_sequence")
            # Validar que sea lista de strings
            if gesture_sequence is not None:
                if not isinstance(gesture_sequence, list):
                    print("[ROBOT] gesture_sequence no es lista, ignorando.")
                    gesture_sequence = None
                else:
                    # Filtrar nombres no validos en el cliente para no
                    # depender solo del LLM
                    valid = [g for g in gesture_sequence
                             if isinstance(g, str) and g in GESTURE_CATALOG]
                    if len(valid) != len(gesture_sequence):
                        invalid = set(gesture_sequence) - set(valid)
                        print("[ROBOT] Gestos invalidos descartados: " + str(invalid))
                    gesture_sequence = valid if valid else None
            return response_text, gesture_sequence, None

        # Caso 2: acciones fisicas (sin gestos paralelos)
        print("[ROBOT] Accion recibida: " + str(action_type))

        if action_type == "execute_pose":
            pose_name = parameters.get("pose_name")
            if pose_name in STATIC_POSES:
                robot.servo_write_all(STATIC_POSES[pose_name])
                return "Entendido, ejecutando la pose " + str(pose_name).replace("_", " ") + ".", None, None
            return None, None, "No se encontro la pose: '" + str(pose_name) + "'."

        if action_type == "execute_sequence":
            sequence_name = parameters.get("sequence_name")
            if sequence_name in SEQUENCE_FILES:
                result = play_sequence(sequence_name, robot)
                # play_sequence devuelve "hecho" (string) o (None, error)
                if isinstance(result, tuple):
                    return None, None, result[1]
                return None, None, None
            return None, None, "Secuencia '" + str(sequence_name) + "' desconocida."

        if action_type == "execute_dance":
            dance_name = parameters.get("dance_name")
            if dance_name:
                response, error = play_choreography(dance_name, robot)
                return response, None, error
            return None, None, "Nombre de baile no especificado."

        if action_type == "control_led":
            state = parameters.get("state", False)
            if isinstance(state, bool):
                print("[ROBOT] LEDs " + ("ON" if state else "OFF"))
                robot.leds(state)
                return ("OK, " + ("encendiendo" if state else "apagando") + " las luces.", None, None)
            return None, None, "Estado invalido para LEDs."

        return None, None, "Accion '" + str(action_type) + "' no reconocida."

    except json.JSONDecodeError:
        return action_json, None, None
    except Exception as e:
        return None, None, "Error ejecutando accion del robot: " + str(e)

# ---------- MAIN ----------
def main():
    print("Inicializando asistente de voz para Alpha 1S...")

    pygame.mixer.init()
    voice_model = initialize_piper_voice()
    whisper_model = whisper.load_model(WHISPER_MODEL_SIZE)
    recognizer = sr.Recognizer()
    microphone = sr.Microphone(sample_rate=RATE)
    audio_interface = pyaudio.PyAudio()
    stream = audio_interface.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                                  input=True, frames_per_buffer=CHUNK)
    stream.stop_stream()

    robot = None
    try:
        print("[ROBOT] Conectando con el robot Alpha 1S...")
        robot = Alpha1S()
        robot.leds(False)
        print("[ROBOT] Conexion establecida.")
    except Exception as e:
        print("[ROBOT] No se pudo conectar. Error: " + str(e))

    print("\n" + "=" * 50)
    print("Asistente Alpha 1S iniciado")
    print("=" * 50)

    # Saludo inicial: pose de saludo + mensaje hablado en paralelo.
    startup_greeting(robot, voice_model)
    sleep(1.5)

    try:
        while True:
            if listen_for_wake_word(recognizer, microphone):
                if robot: robot.leds(True)
                stream.start_stream()
                audio_frames = record_audio(stream)
                stream.stop_stream()

                if not audio_frames:
                    continue

                audio_file = save_as_wav(audio_frames, audio_interface, TEMP_AUDIO_FILENAME)
                transcribed_text = transcribe_audio_local(audio_file, whisper_model)
                os.remove(audio_file)

                if transcribed_text and transcribed_text.strip():
                    print("[PI] Texto transcrito: '" + transcribed_text.strip() + "'")
                    llm_output = query_llm_server(transcribed_text)

                    if llm_output:
                        response_to_speak = None
                        gesture_sequence = None

                        if robot:
                            response_to_speak, gesture_sequence, error = handle_robot_action(
                                llm_output, robot
                            )
                            if error:
                                print("[ROBOT] ERROR: " + error)
                                response_to_speak = "Tuve un problema al intentar esa accion."
                                gesture_sequence = None
                        else:
                            try:
                                data = json.loads(llm_output)
                                response_to_speak = data.get("response", "No entendi la accion.")
                            except json.JSONDecodeError:
                                response_to_speak = llm_output

                        if response_to_speak:
                            # Si hay gestos Y robot conectado, ejecucion paralela.
                            # En otro caso, TTS normal sin gestos.
                            if gesture_sequence and robot:
                                speak_with_gestures(
                                    response_to_speak, voice_model,
                                    gesture_sequence, robot
                                )
                            else:
                                speak(response_to_speak, voice_model)
                if robot: robot.leds(False)

    except KeyboardInterrupt:
        print("\n[PI] Apagando el asistente...")
    finally:
        if stream.is_active():
            stream.stop_stream()
        stream.close()
        audio_interface.terminate()
        pygame.mixer.quit()
        # IMPORTANTE: NO apagar servos al salir; el robot caeria.


if __name__ == "__main__":
    main()
