import tkinter as tk
import sqlite3
import threading
import time
import os
import subprocess
import pygame
import speech_recognition as sr
import socket
import pyaudio
import json
from vosk import Model, KaldiRecognizer
from backend import IskaBackend  # All RAG, jailbreak, and AI logic lives here now

# ============================================================
# MICROPHONE CONFIGURATION
# Set MIC_NAME to any part of your microphone's device name.
# Run the app once to see all detected devices in the terminal,
# then paste any unique substring of your mic's name here.
#
# Examples:
#   MIC_NAME = "8- USB"          → Microphone (8- USB Audio Device)
#   MIC_NAME = "USB Audio Device" → Microphone (USB Audio Device)
#   MIC_NAME = "Realtek"         → Microphone (Realtek Audio)
#   MIC_NAME = None              → Auto-detect (falls back to strategies)
# ============================================================
MIC_NAME = "8- USB"

class ISKA_Core_Test:
    def __init__(self, root):
        self.root = root
        self.root.title("ISKA - Core Logic Test")
        self.root.attributes('-fullscreen', True)
        
        # --- State Variables ---
        self.language = "en"
        self.is_idle = True
        self.is_online = True
        self.idle_timer = None
        self.db_path = 'iska_database.db'
        self.current_session_id = None
        self.announcement_index = 0

        # --- BACKEND ---
        # IskaBackend loads the sentence embedder in a background thread,
        # so the UI and mic calibration are never blocked at startup.
        self.backend = IskaBackend()

        # --- AUDIO HARDWARE SCANNER ---
        self.audio_engine = pyaudio.PyAudio()
        self.mic_index = self.get_realtek_index()
        
        # --- WAKE WORD CONFIGURATION (VOSK) ---
        print("\nLoading Vosk Wake Word Model...")
        try:
            self.vosk_model = Model("model")
        except Exception as e:
            print(f"\nCRITICAL ERROR: 'model' folder not found. Cannot start wake word engine. ({e})")
            self.vosk_model = None
            
        self.is_waiting_for_wake_word = True

        # Init Audio Mixer
        pygame.mixer.init()

        # --- PERSISTENT MICROPHONE ---
        # Open the mic once at startup and keep it alive for the entire session.
        # This avoids the 3-8 second hardware handshake that was causing the
        # "Calibrating for room noise..." screen to hang on every tap.
        self._recognizer = sr.Recognizer()
        self._mic_source = sr.Microphone(device_index=self.mic_index)
        self._mic_source.__enter__()
        threading.Thread(target=self._warmup_mic, daemon=True).start()

        self.setup_raw_ui()
        self.start_idle_loop()
        
        # --- BACKGROUND THREADS ---
        threading.Thread(target=self.network_monitor_loop, daemon=True).start()
        
        if self.vosk_model:
            threading.Thread(target=self.wake_word_monitor_loop, daemon=True).start()

    def get_realtek_index(self):
        print("\n--- Audio Hardware Scan ---")

        input_devices = []
        for i in range(self.audio_engine.get_device_count()):
            dev = self.audio_engine.get_device_info_by_index(i)
            if dev['maxInputChannels'] > 0:
                input_devices.append((i, dev))
                print(f"  Input Device {i}: {dev['name']} "
                      f"(channels: {int(dev['maxInputChannels'])}, "
                      f"rate: {int(dev['defaultSampleRate'])}Hz)")

        if not input_devices:
            print("CRITICAL: No input devices found at all. Check your microphone connection.")
            return None

        # STRATEGY 0: Use MIC_NAME config if set — highest priority.
        # Change MIC_NAME at the top of this file to switch microphones.
        if MIC_NAME:
            for i, dev in input_devices:
                if MIC_NAME.lower() in dev['name'].lower():
                    print(f"LOCKED [Config]: Device {i} - {dev['name']}")
                    print(f"  --> Matched MIC_NAME = '{MIC_NAME}'")
                    return i
            print(f"WARNING: MIC_NAME = '{MIC_NAME}' did not match any device.")
            print("  --> Falling through to auto-detection strategies.")

        # STRATEGY 1: Prefer a dedicated USB microphone
        for i, dev in input_devices:
            if "usb" in dev['name'].lower() and "mic" in dev['name'].lower():
                print(f"LOCKED [USB Mic]: Device {i} - {dev['name']}")
                return i

        # STRATEGY 2: Realtek onboard mic
        for i, dev in input_devices:
            if "realtek" in dev['name'].lower() and "mic" in dev['name'].lower():
                print(f"LOCKED [Realtek Mic]: Device {i} - {dev['name']}")
                return i

        # STRATEGY 3: Any device with "microphone" in the name
        for i, dev in input_devices:
            if "microphone" in dev['name'].lower() or "mic" in dev['name'].lower():
                print(f"LOCKED [Generic Mic]: Device {i} - {dev['name']}")
                return i

        # STRATEGY 4: Last resort — first available input device
        fallback_index = input_devices[0][0]
        print(f"WARNING: No named microphone found. Falling back to first available "
              f"input device: Device {fallback_index} - {input_devices[0][1]['name']}")
        print("  --> If this is the wrong device, check your Windows Sound Settings")
        print("      and make sure your microphone is set as the default recording device.")
        return fallback_index

    def setup_raw_ui(self):
        top_frame = tk.Frame(self.root, bg="lightgray", height=50)
        top_frame.pack(fill=tk.X)
        
        self.status_label = tk.Label(top_frame, text="STATUS: IDLE (Awaiting Wake Word)", font=("Arial", 14), bg="lightgray")
        self.status_label.pack(side=tk.LEFT, padx=20)

        self.network_label = tk.Label(top_frame, text="🌐 Online", font=("Arial", 11), bg="lightgray", fg="green")
        self.network_label.pack(side=tk.LEFT, padx=10)
        
        tk.Button(top_frame, text="Toggle EN/TL", font=("Arial", 12, "bold"), command=self.toggle_language).pack(side=tk.RIGHT, padx=20, pady=10)

        self.display_text = tk.Text(self.root, font=("Arial", 24), wrap=tk.WORD, height=10)
        self.display_text.pack(expand=True, fill=tk.BOTH, padx=50, pady=20)

        bottom_frame = tk.Frame(self.root, bg="darkgray")
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)

        search_frame = tk.Frame(bottom_frame, bg="darkgray")
        search_frame.pack(fill=tk.X, pady=10)
        
        self.text_entry = tk.Entry(search_frame, font=("Arial", 16))
        self.text_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=10)
        
        tk.Button(search_frame, text="Submit", font=("Arial", 12, "bold"), command=self.handle_text_search).pack(side=tk.RIGHT, padx=20)

        self.mic_btn = tk.Button(bottom_frame, text="TAP TO SPEAK", font=("Arial", 16, "bold"), command=self.start_listening_thread, bg="#28a745", fg="white", padx=20, pady=10)
        self.mic_btn.pack(pady=20)
        
        tk.Button(bottom_frame, text="Exit Kiosk", font=("Arial", 12, "bold"), command=self.root.destroy, bg="#dc3545", fg="white").pack(side=tk.RIGHT, padx=20, pady=10)

    # ==========================================
    # MIC MANAGEMENT
    # ==========================================
    def _warmup_mic(self):
        """
        Runs once in a background thread at startup.
        Calibrates for ambient noise so the first tap is instant.
        """
        print("[MIC] Warming up microphone...")
        self._recognizer.adjust_for_ambient_noise(self._mic_source, duration=0.5)
        print(f"[MIC] Ready. Energy threshold: {self._recognizer.energy_threshold:.1f}")

    def recalibrate_mic(self):
        """
        Re-runs ambient noise calibration in the background.
        Call this if the environment changes significantly (e.g. after a
        long idle period or if the mic is picking up too much background noise).
        """
        threading.Thread(
            target=lambda: self._recognizer.adjust_for_ambient_noise(
                self._mic_source, duration=0.5
            ),
            daemon=True
        ).start()
        print("[MIC] Recalibrating ambient noise threshold...")

    # ==========================================
    # ENGINE: VOSK WAKE WORD & GOOGLE STT
    # ==========================================
    def wake_word_monitor_loop(self):
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        CHUNK = 4000 
        
        while True:
            if not self.is_waiting_for_wake_word:
                time.sleep(0.5)
                continue
                
            mic_stream = None
            trigger_detected = False
            
            try:
                mic_stream = self.audio_engine.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK, input_device_index=self.mic_index)
                rec = KaldiRecognizer(self.vosk_model, RATE, '["hello", "is", "car", "that", "[unk]"]')
                
                while self.is_waiting_for_wake_word:
                    pcm_data = mic_stream.read(CHUNK, exception_on_overflow=False)
                    if not self.is_waiting_for_wake_word:
                        # STT requested the mic — exit cleanly so the stream closes
                        break
                    if rec.AcceptWaveform(pcm_data):
                        result = json.loads(rec.Result())
                        text = result.get("text", "")
                        
                        if text in ["hello is car", "hello is that"]:
                            self.is_waiting_for_wake_word = False
                            trigger_detected = True
                            break 
                            
            except Exception as e:
                print(f"[Wake Word Error] {e}")
                time.sleep(2)
            finally:
                if mic_stream is not None:
                    try:
                        mic_stream.stop_stream()
                        mic_stream.close()
                    except: pass 

            if trigger_detected:
                self.root.after(0, lambda: self.update_display("Hello! I'm listening. How can I help?"))
                self.start_listening_thread()

    def start_listening_thread(self):
        self.wake_up() 
        self.mic_btn.config(state=tk.DISABLED, text="Listening...", bg="#ffc107", fg="black")
        threading.Thread(target=self.process_audio_input, daemon=True).start()

    def process_audio_input(self):
        try:
            time.sleep(0.5)

            if not self.is_online:
                msg = "I'm currently offline and cannot process voice input. Please type your question instead."
                self.root.after(0, lambda: self.update_display(msg))
                threading.Thread(target=self.speak_response, args=(msg,), daemon=True).start()
                return

            # Pause Vosk wake word loop so it releases Device 1.
            # Without this, Vosk and sr.Microphone deadlock over the same device.
            # The finally block below sets it back to True so Vosk resumes after STT.
            self.is_waiting_for_wake_word = False
            time.sleep(0.3)  # Brief pause to let Vosk's read() cycle finish

            # Mic is already open and calibrated from startup — go straight to listening.
            self.root.after(0, lambda: self.update_display("Speak your inquiry now..."))
            audio = self._recognizer.listen(self._mic_source, timeout=10, phrase_time_limit=12)

            self.root.after(0, lambda: self.update_display("Processing your question..."))

            spoken_text = None
            for attempt in range(2):
                try:
                    spoken_text = self._recognizer.recognize_google(audio).lower()
                    break
                except sr.RequestError as e:
                    if attempt == 0:
                        print(f"[STT] Google STT failed (attempt 1), retrying... ({e})")
                        time.sleep(1.5)
                    else:
                        raise

            if spoken_text:
                print(f"[STT] Heard: '{spoken_text}'")
                self.root.after(0, lambda t=spoken_text: self.update_display(f"You said:\n\"{t}\"\n\nISKA is thinking..."))
                time.sleep(0.8)
                self.route_input(spoken_text)

        except sr.WaitTimeoutError:
            msg = "I didn't hear anything. Please tap the button and speak clearly."
            print("[STT] Timeout — no speech detected within the window.")
            self.root.after(0, lambda: self.update_display(msg))
            threading.Thread(target=self.speak_response, args=(msg,), daemon=True).start()

        except sr.UnknownValueError:
            msg = "I heard you, but I couldn't understand the words. Please speak a little slower and try again."
            print("[STT] UnknownValueError — audio captured but speech not recognised.")
            self.root.after(0, lambda: self.update_display(msg))
            threading.Thread(target=self.speak_response, args=(msg,), daemon=True).start()

        except sr.RequestError as e:
            msg = "I couldn't connect to the speech service. Please check the internet and try again."
            print(f"[STT] RequestError after retry — Google STT unavailable: {e}")
            self.root.after(0, lambda: self.update_display(msg))
            threading.Thread(target=self.speak_response, args=(msg,), daemon=True).start()

        except Exception as e:
            print(f"[STT] Unexpected error: {e}")

        finally:
            self.root.after(0, lambda: self.mic_btn.config(state=tk.NORMAL, text="TAP TO SPEAK", bg="#28a745", fg="white"))
            self.is_waiting_for_wake_word = True

    # ==========================================
    # ENGINE: INPUT ROUTER
    # ==========================================
    def route_input(self, text_input):
        """
        Single entry point for all student input (voice + text).
        Intercepts sleep cues first, then hands everything else
        to the backend which handles jailbreak detection, RAG,
        the adaptive response layer, and Ollama.
        """
        self.wake_up()

        # Sleep cue interceptor — handled locally, no backend needed
        sleep_cues = [
            "thank you", "thanks", "goodbye", "bye", "go to sleep",
            "that's all", "salamat", "paalam"
        ]
        if any(cue in text_input.lower() for cue in sleep_cues):
            threading.Thread(target=self.execute_sleep_sequence, args=(text_input,), daemon=True).start()
            return

        # Everything else goes to the backend
        threading.Thread(target=self.query_backend, args=(text_input,), daemon=True).start()

    def query_backend(self, text_input):
        """
        Calls backend.process_query() and handles the response:
        streams it to the display, speaks it, and logs it.

        The backend handles (in order):
          - Warmup guard (embedder not ready yet)
          - Semantic jailbreak detection
          - Semantic RAG retrieval
          - Adaptive response layer (bypass / augmented / fallback)
          - Ollama streaming
        """
        def stream_to_display(text):
            self.root.after(0, lambda t=text: self.update_display(t))

        full_response = self.backend.process_query(
            user_input=text_input,
            lang=self.language,
            ui_callback=stream_to_display
        )

        # Speak the final assembled response
        threading.Thread(target=self.speak_response, args=(full_response,), daemon=True).start()

        # Log the interaction to the database
        self.log_interaction(text_input, full_response)

    # ==========================================
    # MANUAL SLEEP SEQUENCE
    # ==========================================
    def execute_sleep_sequence(self, text_input):
        closing_msg = (
            "You are very welcome! Have a great day ahead."
            if self.language == 'en'
            else "Walang anuman! Magandang araw sa iyo."
        )
        self.root.after(0, lambda: self.update_display(f"ISKA AI:\n\n{closing_msg}"))
        self.log_interaction(text_input, closing_msg)
        self.speak_response(closing_msg)
        self.root.after(0, self.go_to_sleep)

    # ==========================================
    # CONVERSATION LOGGER
    # ==========================================
    def log_interaction(self, student_query, ai_response):
        """Saves the query/response pair to the database."""
        try:
            clean_response = ai_response.replace("ISKA AI:\n\n", "").replace("ISKA:\n\n", "")
            local_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                "INSERT INTO query_logs (student_query, ai_response, session_id, timestamp) VALUES (?, ?, ?, ?)",
                (student_query, clean_response, self.current_session_id, local_time)
            )
            conn.commit()
            conn.close()
            print(f"[LOGGER] Saved transcript at local time: {local_time}")
        except Exception as e:
            print(f"[LOGGER] Database logging failed: {e}")

    # ==========================================
    # AUDIO OUTPUT & UTILS
    # ==========================================
    def speak_response(self, text):
        self.root.after(0, lambda: self.status_label.config(text="STATUS: SPEAKING...", fg="blue"))
        voice = "fil-PH-AngeloNeural" if self.language == "tl" else "en-US-ChristopherNeural"
        
        safe_text = (text
            .replace("ISKA AI:", "")
            .replace("ISKA:", "")
            .replace("ISKA", "Isska")
            .replace("PUP", "P. U. P.")
            .replace("Biñan", "Binyan")
            .replace('"', '\\"')
            .replace('\n', ' ')
        )
        filename = f"temp_res_{int(time.time())}.mp3"
        
        command = ['python', '-m', 'edge_tts', '--voice', voice, '--text', safe_text, '--write-media', filename]
        try:
            subprocess.run(command, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print(f"[TTS Error] edge-tts failed: {e.stderr.decode()}")
        
        try:
            if os.path.exists(filename):
                pygame.mixer.music.load(filename)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy(): 
                    time.sleep(0.1)
            else:
                print("[TTS Error] Audio file was not created by edge-tts.")
                
        except Exception as e:
            print(f"[Pygame Audio Error] {e}")
            
        finally:
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
            if os.path.exists(filename): 
                os.remove(filename)
                
        self.root.after(0, lambda: self.status_label.config(text="STATUS: IDLE (Awaiting Wake Word)", fg="black"))

    def network_monitor_loop(self):
        while True:
            try:
                socket.create_connection(("8.8.8.8", 53), timeout=2)
                newly_online = not self.is_online
                self.is_online = True
                if newly_online:
                    self.root.after(0, lambda: self.network_label.config(text="🌐 Online", fg="green"))
            except:
                newly_offline = self.is_online
                self.is_online = False
                if newly_offline:
                    self.root.after(0, lambda: self.network_label.config(text="⚠ Offline", fg="red"))
            time.sleep(5)

    def start_idle_loop(self):
        if self.is_idle:
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                announcements = conn.execute("SELECT * FROM announcements WHERE is_active = 1").fetchall()
                conn.close()

                if announcements:
                    self.announcement_index = self.announcement_index % len(announcements)
                    ann = announcements[self.announcement_index]
                    self.announcement_index += 1

                    txt = ann['content_en'] if self.language == 'en' else ann['content_tl']
                    title = ann['title_en'] if self.language == 'en' else ann['title_tl']
                    self.update_display(f"[ANNOUNCEMENT]\n{title}\n\n{txt}")
            except Exception as e:
                print(f"[Idle Loop Error] {e}")

        self.root.after(5000, self.start_idle_loop)

    def wake_up(self):
        if self.is_idle:
            self.current_session_id = f"session_{int(time.time())}"
            
        self.is_idle = False
        if self.idle_timer: self.root.after_cancel(self.idle_timer)
        self.idle_timer = self.root.after(30000, self.go_to_sleep)

    def go_to_sleep(self):
        self.is_idle = True
        self.current_session_id = None
        self.announcement_index = 0
        self.status_label.config(text="STATUS: IDLE (Awaiting Wake Word)", fg="black")
        # Recalibrate mic after each session so ambient noise changes
        # (e.g. hallway crowds, AC switching on) don't affect the next student.
        self.recalibrate_mic()
        self.start_idle_loop()

    def update_display(self, text):
        self.display_text.config(state=tk.NORMAL)
        self.display_text.delete(1.0, tk.END)
        self.display_text.insert(tk.END, text)
        self.display_text.config(state=tk.DISABLED)
        self.display_text.yview(tk.END)

    def handle_text_search(self):
        query = self.text_entry.get().strip()
        if query:
            self.text_entry.delete(0, tk.END)
            self.route_input(query)

    def toggle_language(self):
        self.language = "tl" if self.language == "en" else "en"
        self.update_display(f"Language switched to {'Filipino' if self.language == 'tl' else 'English'}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ISKA_Core_Test(root)
    root.mainloop()