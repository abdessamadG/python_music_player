import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QFileDialog, 
                            QListWidget, QSlider, QStyle, QFrame, QSizePolicy)
from PyQt6.QtCore import Qt, QTimer, QUrl, QSize
from PyQt6.QtGui import QIcon, QFont, QPixmap, QImage, QColor
import pygame
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
from mutagen import File
import requests
from io import BytesIO

# Catppuccin Mocha Color Palette
COLORS = {
    'base': '#1e1e2e',      # Background
    'surface0': '#313244',   # Surface colors
    'surface1': '#45475a',
    'text': '#cdd6f4',      # Text
    'subtext0': '#a6adc8',  # Secondary text
    'blue': '#89b4fa',      # Accent
    'lavender': '#b4befe',  # Hover
    'overlay0': '#6c7086',  # Borders
    'red': '#f38ba8',       # Alerts/Errors
}

class MusicPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Music Player")
        self.setGeometry(100, 100, 900, 700)
        
        # Set base style
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {COLORS['base']};
            }}
            QLabel {{
                color: {COLORS['text']};
                font-size: 14px;
            }}
            QPushButton {{
                background-color: {COLORS['surface0']};
                color: {COLORS['text']};
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['surface1']};
            }}
            QListWidget {{
                background-color: {COLORS['surface0']};
                color: {COLORS['text']};
                border: none;
                border-radius: 4px;
                font-size: 14px;
                padding: 5px;
            }}
            QListWidget::item:selected {{
                background-color: {COLORS['surface1']};
                color: {COLORS['lavender']};
            }}
            QSlider::groove:horizontal {{
                border: 1px solid {COLORS['overlay0']};
                height: 8px;
                background: {COLORS['surface0']};
                margin: 2px 0;
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                background: {COLORS['blue']};
                border: none;
                width: 18px;
                margin: -2px 0;
                border-radius: 9px;
            }}
            QFrame#metadataFrame {{
                background-color: {COLORS['surface0']};
                border-radius: 8px;
                padding: 10px;
            }}
        """)

        # Initialize pygame mixer
        pygame.mixer.init()
        pygame.mixer.music.set_volume(0.5)

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create top section with album art and metadata
        top_section = QHBoxLayout()
        
        # Album art frame
        self.album_art_frame = QFrame()
        self.album_art_frame.setFixedSize(300, 300)
        self.album_art_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface0']};
                border-radius: 8px;
            }}
        """)
        album_art_layout = QVBoxLayout(self.album_art_frame)
        
        self.album_art_label = QLabel()
        self.album_art_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.album_art_label.setFixedSize(280, 280)
        self.album_art_label.setStyleSheet("border-radius: 4px;")
        
        # Set default album art
        default_art = QPixmap(280, 280)
        default_art.fill(QColor(COLORS['surface1']))
        self.album_art_label.setPixmap(default_art)
        
        album_art_layout.addWidget(self.album_art_label)
        top_section.addWidget(self.album_art_frame)
        
        # Metadata frame
        metadata_frame = QFrame()
        metadata_frame.setObjectName("metadataFrame")
        metadata_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        metadata_layout = QVBoxLayout(metadata_frame)
        
        self.song_title_label = QLabel("No song playing")
        self.song_title_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {COLORS['text']};")
        self.artist_label = QLabel("Unknown Artist")
        self.artist_label.setStyleSheet(f"color: {COLORS['subtext0']};")
        self.album_label = QLabel("Unknown Album")
        self.album_label.setStyleSheet(f"color: {COLORS['subtext0']};")
        self.year_label = QLabel("")
        self.year_label.setStyleSheet(f"color: {COLORS['subtext0']};")
        
        metadata_layout.addWidget(self.song_title_label)
        metadata_layout.addWidget(self.artist_label)
        metadata_layout.addWidget(self.album_label)
        metadata_layout.addWidget(self.year_label)
        metadata_layout.addStretch()
        
        top_section.addWidget(metadata_frame)
        main_layout.addLayout(top_section)

        # Create playlist
        self.playlist = QListWidget()
        self.playlist.itemDoubleClicked.connect(self.play_selected)
        main_layout.addWidget(self.playlist)

        # Create time slider
        self.time_slider = QSlider(Qt.Orientation.Horizontal)
        self.time_slider.setMaximum(100)
        self.time_slider.sliderPressed.connect(self.slider_pressed)
        self.time_slider.sliderReleased.connect(self.slider_released)
        main_layout.addWidget(self.time_slider)

        # Create time labels
        time_layout = QHBoxLayout()
        self.current_time = QLabel("0:00")
        self.total_time = QLabel("0:00")
        time_layout.addWidget(self.current_time)
        time_layout.addStretch()
        time_layout.addWidget(self.total_time)
        main_layout.addLayout(time_layout)

        # Create volume control
        volume_layout = QHBoxLayout()
        volume_label = QLabel("Volume:")
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(70)
        self.volume_slider.valueChanged.connect(self.change_volume)
        volume_layout.addWidget(volume_label)
        volume_layout.addWidget(self.volume_slider)
        main_layout.addLayout(volume_layout)

        # Create control buttons
        controls_layout = QHBoxLayout()
        
        # Previous button
        self.prev_button = QPushButton()
        self.prev_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSkipBackward))
        self.prev_button.clicked.connect(self.play_previous)
        
        # Stop button
        self.stop_button = QPushButton()
        self.stop_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self.stop_button.clicked.connect(self.stop_music)
        
        # Play/Pause button
        self.play_button = QPushButton()
        self.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.play_button.clicked.connect(self.play_pause)
        
        # Next button
        self.next_button = QPushButton()
        self.next_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSkipForward))
        self.next_button.clicked.connect(self.play_next)
        
        # Add file button
        self.add_button = QPushButton("Add Music")
        self.add_button.clicked.connect(self.add_music)

        controls_layout.addWidget(self.prev_button)
        controls_layout.addWidget(self.stop_button)
        controls_layout.addWidget(self.play_button)
        controls_layout.addWidget(self.next_button)
        controls_layout.addWidget(self.add_button)
        
        main_layout.addLayout(controls_layout)

        # Initialize variables
        self.current_file = None
        self.is_playing = False
        self.is_paused = False
        self.playlist_files = []
        self.current_index = 0
        self.slider_is_pressed = False
        self.just_seeked = False
        self.seek_position = 0
        self.song_length = 0
        self.current_position = 0
        self.last_update_time = 0

        # Set up timer for updating the slider
        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update_slider)

    def add_music(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Add Music Files",
            "",
            "Audio Files (*.mp3 *.wav)"
        )
        for file in files:
            self.playlist.addItem(os.path.basename(file))
            self.playlist_files.append(file)

    def play_selected(self, item):
        index = self.playlist.row(item)
        if 0 <= index < len(self.playlist_files):
            self.current_index = index
            self.current_file = self.playlist_files[index]
            pygame.mixer.music.load(self.current_file)
            pygame.mixer.music.play()
            self.is_playing = True
            self.is_paused = False
            self.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
            self.timer.start()
            
            # Update song metadata and artwork
            self.update_metadata(self.current_file)
            
            # Update song length
            try:
                audio = MP3(self.current_file)
                self.song_length = audio.info.length
                self.time_slider.setMaximum(int(self.song_length))
                self.total_time.setText(self.format_time(self.song_length))
            except:
                self.song_length = 0
                self.time_slider.setMaximum(100)
                self.total_time.setText("0:00")

    def update_metadata(self, file_path):
        try:
            # Try to load ID3 tags directly
            try:
                audio = ID3(file_path)
                has_id3 = True
            except:
                audio = File(file_path)
                has_id3 = False
            
            # Extract metadata
            if has_id3:
                # Get title
                if 'TIT2' in audio:
                    title = str(audio['TIT2'])
                    self.song_title_label.setText(title)
                else:
                    self.song_title_label.setText(os.path.basename(file_path))
                
                # Get artist
                if 'TPE1' in audio:
                    artist = str(audio['TPE1'])
                    self.artist_label.setText(artist)
                else:
                    self.artist_label.setText("Unknown Artist")
                
                # Get album
                if 'TALB' in audio:
                    album = str(audio['TALB'])
                    self.album_label.setText(album)
                else:
                    self.album_label.setText("Unknown Album")
                
                # Get year
                if 'TDRC' in audio:
                    year = str(audio['TDRC'])
                    self.year_label.setText(f"Year: {year}")
                else:
                    self.year_label.setText("")
                
                # Get album art
                if 'APIC:' in audio:
                    apic = audio['APIC:'].data
                    image = QImage()
                    image.loadFromData(apic)
                    pixmap = QPixmap.fromImage(image)
                    scaled_pixmap = pixmap.scaled(280, 280, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self.album_art_label.setPixmap(scaled_pixmap)
                    print("Album art loaded from ID3 tags")
                else:
                    # Try alternative APIC tag
                    for key in audio.keys():
                        if key.startswith('APIC'):
                            apic = audio[key].data
                            image = QImage()
                            image.loadFromData(apic)
                            pixmap = QPixmap.fromImage(image)
                            scaled_pixmap = pixmap.scaled(280, 280, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                            self.album_art_label.setPixmap(scaled_pixmap)
                            print(f"Album art loaded from {key}")
                            break
                    else:
                        # No album art found
                        default_art = QPixmap(280, 280)
                        default_art.fill(QColor(COLORS['surface1']))
                        self.album_art_label.setPixmap(default_art)
                        print("No album art found in ID3 tags")
            else:
                # No ID3 tags, try to get basic metadata
                if hasattr(audio, 'tags') and audio.tags:
                    if 'TIT2' in audio.tags:
                        title = str(audio.tags['TIT2'])
                        self.song_title_label.setText(title)
                    else:
                        self.song_title_label.setText(os.path.basename(file_path))
                    
                    if 'TPE1' in audio.tags:
                        artist = str(audio.tags['TPE1'])
                        self.artist_label.setText(artist)
                    else:
                        self.artist_label.setText("Unknown Artist")
                    
                    if 'TALB' in audio.tags:
                        album = str(audio.tags['TALB'])
                        self.album_label.setText(album)
                    else:
                        self.album_label.setText("Unknown Album")
                    
                    if 'TDRC' in audio.tags:
                        year = str(audio.tags['TDRC'])
                        self.year_label.setText(f"Year: {year}")
                    else:
                        self.year_label.setText("")
                    
                    # Try to get album art from tags
                    if 'APIC:' in audio.tags:
                        apic = audio.tags['APIC:'].data
                        image = QImage()
                        image.loadFromData(apic)
                        pixmap = QPixmap.fromImage(image)
                        scaled_pixmap = pixmap.scaled(280, 280, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        self.album_art_label.setPixmap(scaled_pixmap)
                        print("Album art loaded from tags")
                    else:
                        # No album art found
                        default_art = QPixmap(280, 280)
                        default_art.fill(QColor(COLORS['surface1']))
                        self.album_art_label.setPixmap(default_art)
                        print("No album art found in tags")
                else:
                    # No tags found
                    self.song_title_label.setText(os.path.basename(file_path))
                    self.artist_label.setText("Unknown Artist")
                    self.album_label.setText("Unknown Album")
                    self.year_label.setText("")
                    default_art = QPixmap(280, 280)
                    default_art.fill(QColor(COLORS['surface1']))
                    self.album_art_label.setPixmap(default_art)
                    print("No tags found")
        except Exception as e:
            print(f"Error updating metadata: {e}")
            self.song_title_label.setText(os.path.basename(file_path))
            self.artist_label.setText("Unknown Artist")
            self.album_label.setText("Unknown Album")
            self.year_label.setText("")
            default_art = QPixmap(280, 280)
            default_art.fill(QColor(COLORS['surface1']))
            self.album_art_label.setPixmap(default_art)

    def play_pause(self):
        if not self.playlist_files:
            return

        if not self.is_playing:
            if not self.current_file:
                self.current_file = self.playlist_files[0]
                pygame.mixer.music.load(self.current_file)
                # Update song metadata and artwork
                self.update_metadata(self.current_file)
                # Update song length
                try:
                    audio = MP3(self.current_file)
                    self.song_length = audio.info.length
                    self.time_slider.setMaximum(int(self.song_length))
                    self.total_time.setText(self.format_time(self.song_length))
                except:
                    self.song_length = 0
                    self.time_slider.setMaximum(100)
                    self.total_time.setText("0:00")
            
            # If paused, resume from the current position
            if self.is_paused:
                pygame.mixer.music.unpause()
            else:
                # Start from the beginning or the current position
                pygame.mixer.music.play(start=self.current_position)
            
            self.is_playing = True
            self.is_paused = False
            self.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
            self.timer.start()
        else:
            # Pause the music and store the current position
            pygame.mixer.music.pause()
            self.current_position = pygame.mixer.music.get_pos() / 1000
            self.is_playing = False
            self.is_paused = True
            self.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
            self.timer.stop()

    def stop_music(self):
        if self.current_file:
            pygame.mixer.music.stop()
            self.is_playing = False
            self.is_paused = False
            self.current_position = 0
            self.time_slider.setValue(0)
            self.current_time.setText("0:00")
            self.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
            self.timer.stop()

    def play_next(self):
        if not self.playlist_files:
            return

        self.current_index = (self.current_index + 1) % len(self.playlist_files)
        self.current_file = self.playlist_files[self.current_index]
        self.playlist.setCurrentRow(self.current_index)
        pygame.mixer.music.load(self.current_file)
        pygame.mixer.music.play()
        self.is_playing = True
        self.is_paused = False
        self.current_position = 0
        self.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
        self.timer.start()
        
        # Update song metadata and artwork
        self.update_metadata(self.current_file)
        
        # Update song length
        try:
            audio = MP3(self.current_file)
            self.song_length = audio.info.length
            self.time_slider.setMaximum(int(self.song_length))
            self.total_time.setText(self.format_time(self.song_length))
        except:
            self.song_length = 0
            self.time_slider.setMaximum(100)
            self.total_time.setText("0:00")

    def play_previous(self):
        if not self.playlist_files:
            return

        self.current_index = (self.current_index - 1) % len(self.playlist_files)
        self.current_file = self.playlist_files[self.current_index]
        self.playlist.setCurrentRow(self.current_index)
        pygame.mixer.music.load(self.current_file)
        pygame.mixer.music.play()
        self.is_playing = True
        self.is_paused = False
        self.current_position = 0
        self.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
        self.timer.start()
        
        # Update song metadata and artwork
        self.update_metadata(self.current_file)
        
        # Update song length
        try:
            audio = MP3(self.current_file)
            self.song_length = audio.info.length
            self.time_slider.setMaximum(int(self.song_length))
            self.total_time.setText(self.format_time(self.song_length))
        except:
            self.song_length = 0
            self.time_slider.setMaximum(100)
            self.total_time.setText("0:00")

    def slider_pressed(self):
        self.slider_is_pressed = True
        # Store the current position when slider is pressed
        if pygame.mixer.music.get_busy():
            self.current_position = pygame.mixer.music.get_pos() / 1000

    def slider_released(self):
        if self.current_file and self.song_length > 0:
            position = self.time_slider.value()
            self.current_position = position
            
            # Stop current playback
            pygame.mixer.music.stop()
            
            # Start playing from the new position
            pygame.mixer.music.load(self.current_file)
            pygame.mixer.music.play(start=position)
            
            # Update the current time display
            self.current_time.setText(self.format_time(position))
            
            # Set a flag to prevent the timer from resetting the slider immediately
            self.just_seeked = True
            self.seek_position = position
            self.last_update_time = pygame.mixer.music.get_pos() / 1000
            
            self.is_playing = True
            self.is_paused = False
            self.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
            self.timer.start()
        self.slider_is_pressed = False

    def change_volume(self, value):
        volume = value / 100.0
        pygame.mixer.music.set_volume(volume)

    def update_slider(self):
        if pygame.mixer.music.get_busy() and not self.slider_is_pressed:
            # Get the current time from pygame
            current_time = pygame.mixer.music.get_pos() / 1000
            
            # If we just seeked, use our tracked position instead of pygame's position
            if self.just_seeked:
                # Calculate elapsed time since seeking
                elapsed = current_time - self.last_update_time
                if elapsed > 0:
                    # Update our tracked position
                    self.seek_position += elapsed
                    self.last_update_time = current_time
                
                # Use our tracked position for display
                self.time_slider.setValue(int(self.seek_position))
                self.current_time.setText(self.format_time(self.seek_position))
                
                # Never switch back to normal tracking - keep using our tracked position
                # This ensures the slider stays synchronized throughout playback
            else:
                # Normal update
                self.time_slider.setValue(int(current_time))
                self.current_time.setText(self.format_time(current_time))
                self.current_position = current_time
                self.last_update_time = current_time
        elif not pygame.mixer.music.get_busy() and self.is_playing and not self.is_paused:
            self.play_next()

    def format_time(self, seconds):
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes}:{seconds:02d}"

if __name__ == '__main__':
    app = QApplication(sys.argv)
    player = MusicPlayer()
    player.show()
    sys.exit(app.exec()) 