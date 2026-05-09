import tkinter as tk
import threading
import subprocess
import pygame
import os
import time

class IskaFrontend:
    def __init__(self, root, backend):
        self.root = root
        self.backend = backend
        self.language = "en" # Default language
        
        # Initialize Audio Mixer for Edge-TTS playback
        pygame.mixer.init()

        # --- UI Design ---
        # Top Status Bar
        self.status_label = tk.Label(root, text="ISKA is Ready.", font=("Helvetica", 14, "bold"), bg="#800000", fg="white")
        self.status_label.pack(pady=10)

        # Main Text Display Box (Where the streaming happens)
        self.text_display = tk.Text(root, font=("Helvetica", 16), wrap=tk.WORD, height=10, width=60, padx=20, pady=20)
        self.text_display.pack(pady=20)
        self.text_display.insert(tk.END, "Tap the button below and ask me a question about PUP Biñan!")
        self.text_display.config(state=tk.DISABLED) # Make it read-only

        # Interaction Button (Acts as your Wake Word/Microphone trigger)
        self.listen_btn = tk.Button(root, text="🎤 Tap to Speak", font=("Helvetica", 16, "bold"), 
                                    bg="white", fg="#800000", command=self.start_interaction)
        self.listen_btn.pack(pady=20)

    def update_display(self, text):
        """Safely updates the Tkinter text box from a background thread."""
        self.text_display.config(state=tk.NORMAL)
        self.text_display.delete(1.0, tk.END)
        self.text_display.insert(tk.END, text)
        self.text_display.config(state=tk.DISABLED)
        # Scroll to the bottom as new text streams in
        self.text_display.yview(tk.END) 

    def update_status(self, status_text):
        """Updates the status bar at the top of the screen."""
        self.status_label.config(text=status_text)

    def start_interaction(self):
        """Triggered when the student taps the button."""
        self.listen_btn.config(state=tk.DISABLED)
        
        # Step 1: Get user audio (Simulated here with a hardcoded prompt for testing)
        # In your final version, your Vosk speech_recognition code goes here.
        user_query = "Where is the registrar's office?" 
        
        self.update_display(f"You asked: '{user_query}'\n\nISKA is thinking...")
        self.update_status("Processing...")
        
        # Step 2: Send to backend in a separate thread so Tkinter doesn't freeze!
        threading.Thread(target=self.process_in_background, args=(user_query,), daemon=True).start()

    def process_in_background(self, user_query):
        """Runs the AI and RAG logic in the background."""
        
        # Notice the lambda function! This catches the streaming words from Gemma 
        # and instantly pushes them to the Tkinter screen safely.
        final_text = self.backend.process_query(
            user_input=user_query, 
            lang=self.language, 
            ui_callback=lambda msg: self.root.after(0, self.update_display, msg)
        )
        
        self.root.after(0, self.update_status, "Speaking...")
        
        # Step 3: Speak the final assembled text
        self.speak_text(final_text)

    def speak_text(self, text):
        """Converts text to speech using Edge-TTS and plays it via Pygame."""
        # Clean the text for the command line (remove quotes/newlines)
        clean_text = text.replace('"', '').replace('\n', ' ').replace('ISKA AI:', '')
        audio_file = "temp_response.mp3"

        try:
            # We use subprocess to call the edge-tts CLI tool directly. 
            # It's the most stable way to run async TTS inside a Tkinter app.
            voice = "en-US-JennyNeural" if self.language == "en" else "fil-PH-AngeloNeural"
            command = f'edge-tts --voice {voice} --text "{clean_text}" --write-media {audio_file}'
            subprocess.run(command, shell=True, check=True)

            # Play the audio file
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()

            # Wait until the audio completely finishes playing
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)

            # Clean up the file so your 128GB SSD doesn't fill up!
            pygame.mixer.music.unload()
            if os.path.exists(audio_file):
                os.remove(audio_file)
                
        except Exception as e:
            print(f"Audio Error: {e}")
            
        finally:
            # Reset the UI for the next student
            self.root.after(0, self.update_status, "ISKA is Ready.")
            self.root.after(0, lambda: self.listen_btn.config(state=tk.NORMAL))