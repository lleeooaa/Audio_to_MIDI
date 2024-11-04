from converter import audio_to_notes_polyphonic, notes_to_midi, play_midi
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import threading
import os
import pygame
import sys
from io import StringIO

class AudioToMIDIConverter:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Audio to MIDI Converter")
        self.window.geometry("600x600")  # Increased height for console output
        self.output_midi = None
        pygame.mixer.init()
        self.setup_ui()

    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # File selection
        ttk.Label(main_frame, text="Audio File:").grid(row=0, column=0, sticky=tk.W)
        self.file_path = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.file_path, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_file).grid(row=0, column=2)

        # Conversion options
        options_frame = ttk.LabelFrame(main_frame, text="Conversion Options", padding="5")
        options_frame.grid(row=1, column=0, columnspan=3, pady=10, sticky=(tk.W, tk.E))

        ttk.Label(options_frame, text="Type:").grid(row=0, column=0, sticky=tk.W)
        self.conversion_type = tk.StringVar(value="non_vocal")
        ttk.Radiobutton(options_frame, text="Vocal", value="vocal", 
                       variable=self.conversion_type).grid(row=0, column=1)
        ttk.Radiobutton(options_frame, text="Non-Vocal", value="non_vocal", 
                       variable=self.conversion_type).grid(row=0, column=2)

        ttk.Label(options_frame, text="Max Notes (default: None):").grid(row=1, column=0, sticky=tk.W)
        self.max_notes = tk.StringVar()
        ttk.Entry(options_frame, textvariable=self.max_notes, width=10).grid(row=1, column=1)
        ttk.Label(options_frame, text="Delta (default vocal:0.03, non_vocal:0.04):").grid(row=2, column=0, sticky=tk.W)
        self.delta = tk.StringVar(value=0.04)
        ttk.Entry(options_frame, textvariable=self.delta, width=10).grid(row=2, column=1)

        # Console output
        console_frame = ttk.LabelFrame(main_frame, text="Console Output", padding="5")
        console_frame.grid(row=2, column=0, columnspan=3, pady=10, sticky=(tk.W, tk.E))
        self.console = scrolledtext.ScrolledText(console_frame, height=10, width=60)
        self.console.grid(row=0, column=0, padx=5, pady=5)

        # Status and progress
        self.status_var = tk.StringVar()
        ttk.Label(main_frame, textvariable=self.status_var).grid(row=3, column=0, 
                                                                columnspan=3, pady=5)
        self.progress = ttk.Progressbar(main_frame, length=300, mode='determinate')
        self.progress.grid(row=4, column=0, columnspan=3, pady=5)

        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=3, pady=10)
        
        ttk.Button(button_frame, text="Convert", command=self.start_conversion
                  ).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Play MIDI", command=self.play_midi
                  ).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="Exit", command=self.window.quit
                  ).grid(row=0, column=2, padx=5)

    def write_to_console(self, text):
        self.console.insert(tk.END, str(text) + '\n')
        self.console.see(tk.END)
        self.window.update()

    def browse_file(self):
        filename = filedialog.askopenfilename(
            filetypes=[("Audio Files", "*.mp3 *.wav *.ogg")])
        if filename:
            self.file_path.set(filename)

    def start_conversion(self):
        if not self.file_path.get():
            self.status_var.set("Please select an audio file first!")
            return
        
        self.status_var.set("Converting...")
        self.console.delete(1.0, tk.END)  # Clear console
        threading.Thread(target=self.convert_audio, daemon=True).start()

    def convert_audio(self):
        try:
            self.output_midi = os.path.splitext(self.file_path.get())[0] + "_output.mid"
            
            # Redirect stdout to capture print statements
            old_stdout = sys.stdout
            sys.stdout = string_buffer = StringIO()
            
            if isinstance(self.max_notes, int):
                notes, bpm = audio_to_notes_polyphonic(
                    self.file_path.get(),
                    type=self.conversion_type.get(),
                    number_of_notes=int(self.max_notes.get()),
                    delta=float(self.delta.get())
                )
            else:
                notes, bpm = audio_to_notes_polyphonic(
                    self.file_path.get(),
                    type=self.conversion_type.get(),
                    delta=float(self.delta.get())
                )
                
            # Restore stdout and get the captured output
            sys.stdout = old_stdout
            captured_output = string_buffer.getvalue()
            
            # Write captured output to console
            self.window.after(0, self.write_to_console, captured_output)
            
            notes_to_midi(notes, self.output_midi, bpm)
            self.status_var.set(f"Conversion complete!")
        except Exception as e:
            self.status_var.set(f"Error during conversion: {str(e)}")
            self.write_to_console(f"Error: {str(e)}")

    def play_midi(self):
        if not self.output_midi or not os.path.exists(self.output_midi):
            self.status_var.set("Please convert an audio file first!")
            return
        
        try:
            pygame.mixer.music.load(self.output_midi)
            pygame.mixer.music.play()
            self.status_var.set("Playing MIDI...")
            self.write_to_console(f"Playing {self.output_midi}...")
        except pygame.error as e:
            self.status_var.set(f"Error playing MIDI: {str(e)}")
            self.write_to_console(f"Error playing MIDI: {str(e)}")

    def run(self):
        self.window.mainloop()
        pygame.mixer.quit()

    def __del__(self):
        pygame.mixer.quit()

if __name__ == "__main__":
    app = AudioToMIDIConverter()
    app.run()