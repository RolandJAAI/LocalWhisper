import os
import subprocess
import tempfile
import pygame
import pyperclip
import time
import shutil
from whisper_turbo import transcribe
from threading import Thread

class AudioTranscriber:
    def __init__(self):
        # Initialize PyGame
        pygame.init()
        self.width, self.height = 200, 200
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("WhisperTurbo MLX")
        
        # Load microphone icon
        icon_path = os.path.join(os.path.dirname(__file__), 'mic_icon_sw.png')
        self.mic_icon = pygame.image.load(icon_path)
        # Scale icon to fill window height minus space for text
        icon_size = 160  # Bigger size, leaving 40px for text at top
        self.mic_icon = pygame.transform.scale(self.mic_icon, (icon_size, icon_size))
        
        # Set taskbar icon
        pygame.display.set_icon(self.mic_icon)
        
        # States and colors
        self.recording = False
        self.processing = False
        self.colors = {
            'idle': (34, 177, 76),     # Green
            'recording': (255, 0, 0),   # Red
            'processing': (255, 165, 0), # Orange
        }
        
        # Setup fonts
        self.button_font = pygame.font.Font(None, 24)
        self.footer_font = pygame.font.Font(None, 16)
        
        # Recording setup
        self.temp_dir = None
        self.current_chunk = None
        self.chunk_duration = 60  # Seconds per chunk
        self.chunks = []
        self.ffmpeg_process = None
        self.start_time = None

    def draw_button(self):
        """Draw the window with icon and text"""
        # Determine state and text
        if self.processing:
            color = self.colors['processing']
            text = "Processing..."
        elif self.recording:
            color = self.colors['recording']
            elapsed = int(time.time() - self.start_time)
            text = f"Recording... ({elapsed}s)"
        else:
            color = self.colors['idle']
            text = "Ready."
                
        # Fill background with status color
        self.screen.fill(color)
        
        # Draw microphone icon at bottom
        icon_rect = self.mic_icon.get_rect()
        icon_rect.bottom = self.height  # Align to bottom
        icon_rect.centerx = self.width // 2  # Center horizontally
        self.screen.blit(self.mic_icon, icon_rect)
        
        # Draw status text at top
        text_surface = self.button_font.render(text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=(self.width // 2, 20))  # Moved text up
        self.screen.blit(text_surface, text_rect)
        
        # Draw footer as overlay on the icon
        footer_text = "Made by @RolandJAAI"
        footer_surface = self.footer_font.render(footer_text, True, (255, 255, 255))
        footer_rect = footer_surface.get_rect(center=(self.width // 2, self.height - 15))
        self.screen.blit(footer_surface, footer_rect)
        
        pygame.display.flip()

    def start_recording(self):
        """Start recording audio using ffmpeg"""
        if self.recording:
            return
            
        # Create new temp directory for this recording session
        self.temp_dir = tempfile.mkdtemp()
        self.chunks = []  # Reset chunks list
        self.recording = True
        self.start_time = time.time()
        
        # Start single ffmpeg process for continuous recording
        output_pattern = os.path.join(self.temp_dir, 'chunk_%d.wav')
        cmd = [
            'ffmpeg',
            '-f', 'avfoundation',
            '-i', ':0',
            '-y',
            '-ar', '16000',
            '-ac', '1',
            '-f', 'segment',
            '-segment_time', str(self.chunk_duration),
            output_pattern
        ]
        
        try:
            self.ffmpeg_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print("Recording started...")
        except Exception as e:
            print(f"Error starting recording: {e}")
            self.recording = False

    def stop_recording(self):
        """Stop recording and transcribe in a separate thread"""
        if not self.recording:
            return
            
        self.recording = False
        self.processing = True
        
        try:
            # Stop ffmpeg gracefully
            if self.ffmpeg_process:
                self.ffmpeg_process.terminate()
                try:
                    self.ffmpeg_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.ffmpeg_process.kill()
                    
            print("Recording stopped...")
            
            # Get list of recorded chunks
            if self.temp_dir and os.path.exists(self.temp_dir):
                self.chunks = sorted([
                    os.path.join(self.temp_dir, f) 
                    for f in os.listdir(self.temp_dir) 
                    if f.endswith('.wav')
                ])
            
            # Start transcription in a separate thread
            Thread(target=self.process_audio, daemon=True).start()
        except Exception as e:
            print(f"Error stopping recording: {e}")
            self.processing = False

    def process_audio(self):
        """Process all recorded chunks"""
        try:
            full_text = []
            
            # Process each chunk
            for chunk_file in self.chunks:
                if os.path.exists(chunk_file) and os.path.getsize(chunk_file) > 0:
                    text = transcribe(chunk_file, any_lang=True)
                    full_text.append(text)
                    
            # Combine all transcriptions
            final_text = ' '.join(full_text)
            pyperclip.copy(final_text)
            print(f"Transcribed: {final_text}")
            
        except Exception as e:
            print(f"Transcription error: {e}")
        finally:
            # Cleanup
            try:
                if self.temp_dir and os.path.exists(self.temp_dir):
                    shutil.rmtree(self.temp_dir)
            except Exception as e:
                print(f"Error cleaning up temp files: {e}")
            self.processing = False

    def run(self):
        """Main application loop"""
        running = True
        while running:
            try:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        if event.button == 1 and not self.processing:  # Left click
                            if not self.recording:
                                self.start_recording()
                            else:
                                self.stop_recording()
                
                self.screen.fill((255, 255, 255))
                self.draw_button()
                pygame.time.Clock().tick(30)
                
            except Exception as e:
                print(f"Error in main loop: {e}")
                running = False

        # Cleanup
        if self.recording:
            self.stop_recording()
        pygame.quit()

def main():
    transcriber = AudioTranscriber()
    transcriber.run()

if __name__ == "__main__":
    main() 