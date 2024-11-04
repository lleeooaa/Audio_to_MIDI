import librosa
import numpy as np
from midiutil import MIDIFile
import pygame.midi
from scipy.signal import find_peaks
from tqdm import tqdm

def scale_velocity(magnitude, max_magnitude):
    # Logarithmic scaling (more perceptual, natural scaling)
    if magnitude > 0:
        velocity = int((np.log1p(magnitude) / np.log1p(max_magnitude)) * 127)
    else:
        velocity = 0
    # Ensure the velocity is in the range [0, 127]
    return max(0, min(127, velocity))

def vocal_transform(file_path, number_of_notes=None, delta=0.03):
    y, sr = librosa.load(file_path, sr=44100)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    bpm, _ = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
    print(f"Detected bpm: {bpm}")
    # Compute the constant-Q transform  
    C = np.abs(librosa.cqt(y, sr=sr, fmin=librosa.note_to_hz('A0'), n_bins=88, bins_per_octave=12))
    # Detect onsets
    wait=60 / 16 / bpm * sr / 512
    onsets = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr, delta=delta, wait=wait)
    onset_times = librosa.frames_to_time(onsets, sr=sr)
    notes = []
    for i in tqdm(range(len(onset_times))):
        start_time = onset_times[i]
        end_time = onset_times[i+1] if i+1 < len(onset_times) else librosa.get_duration(y=y, sr=sr)
        
        # Get the frame indices for this note duration
        start_frame = librosa.time_to_frames(start_time, sr=sr)
        end_frame = librosa.time_to_frames(end_time, sr=sr)
        
        # Extract the CQT data for this time range
        note_cqt = C[:, start_frame:end_frame]
        magnitude = np.sum(note_cqt, axis=1)
        # Find peaks in the total magnitude
        peaks, _ = find_peaks(magnitude)
        
        # Remove notes by magnitude
        if number_of_notes and len(peaks)>number_of_notes:
            tmp=np.argsort(magnitude[peaks])[::-1][:number_of_notes]
            peaks=peaks[tmp]
        
        for peak in peaks:
            # Convert to MIDI note number
            midi_note = peak + librosa.note_to_midi('A0')
            
            # Calculate velocity (loudness)
            velocity = scale_velocity(magnitude[peak], np.max(magnitude))
            # Add to notes list
            if velocity > 42:
                weight=peak/176/2+0.75 # Increase the volume of high notes while decrease the low notes (0.75-1.25)
                notes.append((start_time, midi_note, end_time - start_time, min(int(velocity*weight),127)))
    
    notes.sort(key=lambda x: x[0])  # Sort by start time
    print(f"Total number of notes: {len(notes)}")
    return notes, bpm
    
def non_vocal_transform(file_path, number_of_notes=None, delta=0.04):
    y, sr = librosa.load(file_path, sr=44100)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    bpm, _ = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
    print(f"Detected bpm: {bpm}")
    # Pre emphasis for finding sharp notes
    y_pre = librosa.effects.preemphasis(y)
    # Compute the constant-Q transform  
    C = np.abs(librosa.cqt(y, sr=sr, fmin=librosa.note_to_hz('A0'), n_bins=88*2, bins_per_octave=12*2))
    C_pre = np.abs(librosa.cqt(y_pre, sr=sr, fmin=librosa.note_to_hz('A0'), n_bins=88*2, bins_per_octave=12*2))
    # Detect onsets
    onsets = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr, delta=delta, wait=0.00001)
    onset_times = librosa.frames_to_time(onsets, sr=sr)
    notes = []
    for i in tqdm(range(len(onset_times))):
        start_time = onset_times[i]
        end_time = onset_times[i+1] if i+1 < len(onset_times) else librosa.get_duration(y=y, sr=sr)
        
        # Get the frame indices for this note duration
        start_frame = librosa.time_to_frames(start_time, sr=sr)
        end_frame = librosa.time_to_frames(end_time, sr=sr)
        
        # Extract the CQT data for this time range
        note_cqt = C[:, start_frame:end_frame]
        note_cqt_pre = C_pre[:, start_frame:end_frame]
        # Normalize to same magnitude
        note_cqt_norm = note_cqt/np.max(note_cqt)
        note_cqt_pre_norm = note_cqt_pre/np.max(note_cqt_pre)
        note_cqt_mixed = note_cqt_norm*2/3+note_cqt_pre_norm*1/3
        # Calculate the total magnitude for this segment
        magnitude = np.sum(note_cqt_mixed, axis=1)
        # Find peaks in the total magnitude
        peaks, _ = find_peaks(magnitude)
        
        # Remove notes by magnitude
        if number_of_notes and len(peaks)>number_of_notes:
            tmp=np.argsort(magnitude[peaks])[::-1][:number_of_notes]
            peaks=peaks[tmp]
        
        for peak in peaks:
            # Convert to MIDI note number
            midi_note = peak//2 + librosa.note_to_midi('A0')
            
            # Calculate velocity (loudness)
            velocity = scale_velocity(magnitude[peak], np.max(magnitude))
            # Add to notes list
            if velocity > 63:
                notes.append((start_time, midi_note, end_time - start_time, velocity))
    
    notes.sort(key=lambda x: x[0])  # Sort by start time
    print(f"Total number of notes: {len(notes)}")
    return notes, bpm

def audio_to_notes_polyphonic(file_path, type="vocal", number_of_notes=None, delta=0.03):
    if type=="vocal":
        return vocal_transform(file_path,number_of_notes,delta)
    elif type=="non_vocal":
        return non_vocal_transform(file_path,number_of_notes,delta)
    else:
        print("Invalid type")
        return None

def notes_to_midi(notes, output_file, bpm):
    midi = MIDIFile(1) # Create one track
    track = 0
    time = 0 # Start at the beginning
    midi.addTempo(track, time, bpm)

    for note_time, note, duration, velocity in notes:
        # Convert time and duration from seconds to beats
        time_in_beats = (note_time * bpm) / 60
        duration_in_beats = (duration * bpm) / 60
        
        midi.addNote(track, 0, note, time_in_beats, duration_in_beats, velocity)

    with open(output_file, "wb") as f:
        midi.writeFile(f)

def play_midi(file_path):
    pygame.mixer.init()
    try:
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        print(f"Playing {file_path}...")
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
    except pygame.error as e:
        print(f"Failed to play MIDI: {e}")
    finally:
        pygame.mixer.quit()