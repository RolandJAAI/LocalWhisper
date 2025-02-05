import os
import subprocess
import tempfile
import pygame
import pyperclip
from whisper_turbo import transcribe
from threading import Thread

class AudioTranscriber:
    def __init__(self):
        # Initialize PyGame
        pygame.init()
        self.width, self.height = 200, 200
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("WhisperTurbo MLX")
        
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
        self.footer_font = pygame.font.Font(None, 16)  # Smaller size for footer
        
        # Recording setup
        self.temp_file = None
        self.ffmpeg_process = None

    def draw_button(self):
        """Draw the recording button and text"""
        # Determine state and text
        if self.processing:
            color = self.colors['processing']
            text = "Processing..."
        elif self.recording:
            color = self.colors['recording']
            text = "Recording..."
        else:
            color = self.colors['idle']
            text = "Ready."
                
        # Draw circle button
        center = (self.width // 2, self.height // 2)
        pygame.draw.circle(self.screen, color, center, 70)
        
        # Draw button text
        text_surface = self.button_font.render(text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=center)
        self.screen.blit(text_surface, text_rect)
        
        # Draw footer
        footer_text = "Made by JAAI"
        footer_surface = self.footer_font.render(footer_text, True, (150, 150, 150))  # Lighter gray
        footer_rect = footer_surface.get_rect(center=(self.width // 2, self.height - 15))  # Moved up slightly
        self.screen.blit(footer_surface, footer_rect)
        
        # Update display
        pygame.display.flip()

    def start_recording(self):
        """Start recording audio using ffmpeg"""
        if self.recording:
            return
            
        self.temp_file = tempfile.mktemp(suffix='.wav')
        cmd = [
            'ffmpeg',
            '-f', 'avfoundation',
            '-i', ':0',
            '-y',
            '-ar', '16000',
            '-ac', '1',
            self.temp_file
        ]
        
        self.ffmpeg_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.recording = True
        print("Recording started...")

    def stop_recording(self):
        """Stop recording and transcribe in a separate thread"""
        if not self.recording:
            return
            
        self.recording = False
        self.processing = True
        
        # Stop ffmpeg
        self.ffmpeg_process.terminate()
        self.ffmpeg_process.wait()
        print("Recording stopped...")
        
        # Start transcription in a separate thread
        Thread(target=self.process_audio).start()

    def process_audio(self):
        """Process the recorded audio"""
        try:
            text = transcribe(self.temp_file, any_lang=True)
            pyperclip.copy(text)
            print(f"Transcribed: {text}")
        except Exception as e:
            print(f"Transcription error: {e}")
        finally:
            # Cleanup
            os.unlink(self.temp_file)
            self.processing = False

    def run(self):
        """Main application loop"""
        running = True
        while running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click
                        # Check if click is within button circle
                        center = (self.width // 2, self.height // 2)
                        click_pos = event.pos
                        distance = ((click_pos[0] - center[0]) ** 2 + 
                                  (click_pos[1] - center[1]) ** 2) ** 0.5
                        
                        if distance <= 70 and not self.processing:  # 70 is button radius
                            if not self.recording:
                                self.start_recording()
                            else:
                                self.stop_recording()
            
            # Clear screen
            self.screen.fill((255, 255, 255))  # White background
            
            # Draw button and text
            self.draw_button()
            
            # Cap the frame rate
            pygame.time.Clock().tick(30)

        # Cleanup
        pygame.quit()

def main():
    transcriber = AudioTranscriber()
    transcriber.run()

if __name__ == "__main__":
    main() 