import os
import subprocess
import threading
import time
from datetime import datetime

import numpy as np
import rumps
import sounddevice as sd
import soundfile as sf
from CoreFoundation import CFRunLoopRun
from openai import OpenAI
from pydub import AudioSegment
from Quartz import (
    CFMachPortCreateRunLoopSource,
    CFRunLoopAddSource,
    CFRunLoopGetCurrent,
    CGEventGetFlags,
    CGEventMaskBit,
    CGEventTapCreate,
    CGEventTapEnable,
    kCFRunLoopCommonModes,
    kCGEventFlagsChanged,
    kCGEventFlagMaskAlphaShift,
    kCGHIDEventTap,
    kCGHeadInsertEventTap,
)

# Constants
CAPS_LOCK_MASK = kCGEventFlagMaskAlphaShift


class Talk2TypeApp(rumps.App):
    """
    A macOS menu bar app that records voice when Caps Lock is ON,
    transcribes it using OpenAI Whisper, and types the result into the focused app.
    """

    def __init__(self):
        print("🚀 Initializing Talk2Type app...")
        super(Talk2TypeApp, self).__init__(
            "Talk2Type", icon="off.png", quit_button=None
        )
        self.menu = ["Toggle Icon", None, "Quit"]

        # State management
        self.icon_state = (
            False  # False: idle (off.png/white), True: recording (on.png/green)
        )
        self.caps_lock_on = False

        # Audio recording setup
        self.recording = False
        self.audio_data = []
        self.sample_rate = 16000
        self.stream = None

        # OpenAI setup
        self.openai_client = OpenAI()

        # Ensure data directory exists
        os.makedirs("./data", exist_ok=True)
        print("📁 Created ./data directory")
        print("📱 Menu bar app created with off.png icon")

        # Start keyboard monitor in separate thread
        print("🎹 Starting Caps Lock monitor thread...")
        threading.Thread(target=self.monitor_keys, daemon=True).start()

    def type_text(self, text):
        """Type text into the currently focused application using AppleScript."""
        print(f"⌨️  Typing text into focused app: {text}")
        try:
            # Escape special characters for AppleScript
            escaped_text = text.replace("\\", "\\\\").replace('"', '\\"')

            # Use AppleScript to type the text
            script = f"""
            tell application "System Events"
                keystroke "{escaped_text}"
            end tell
            """

            subprocess.run(["osascript", "-e", script], check=True)
            print("✅ Text typed successfully")

        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to type text: {e}")
        except Exception as e:
            print(f"❌ Error typing text: {e}")

    def transcribe_audio(self, filename):
        """Transcribe audio file using OpenAI Whisper API and auto-type the result."""
        print(f"🔄 Transcribing audio: {filename}")
        try:
            with open(filename, "rb") as audio_file:
                # Enhanced transcription with prompt for better English recognition
                transcription = self.openai_client.audio.transcriptions.create(
                    model="gpt-4o-transcribe",
                    file=audio_file,
                    response_format="text",
                    prompt="This is a dictation in English. Please transcribe accurately with proper punctuation and capitalization. Common words and phrases may include technical terms, proper nouns, and everyday speech.",
                )

            print(f"📝 Transcription: {transcription}")

            # Automatically type the transcribed text into the focused app
            if transcription and transcription.strip():
                self.type_text(transcription.strip())
            else:
                print("⚠️  No transcription text to type")

            return transcription

        except Exception as e:
            print(f"❌ Transcription failed: {e}")
            return None

    def start_recording(self):
        """Start audio recording from the microphone."""
        if self.recording:
            return

        self.recording = True
        self.audio_data = []
        print("🎤 Starting audio recording...")

        def audio_callback(indata, frames, time, status):
            if self.recording:
                self.audio_data.append(indata.copy())

        try:
            self.stream = sd.InputStream(
                callback=audio_callback,
                channels=1,
                samplerate=self.sample_rate,
                dtype=np.float32,
            )
            self.stream.start()
            print("✅ Audio recording started")
        except Exception as e:
            print(f"❌ Failed to start recording: {e}")

    def stop_recording(self):
        """Stop audio recording and save to MP3 file."""
        if not self.recording:
            return

        self.recording = False
        print("🛑 Stopping audio recording...")

        try:
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None

            if self.audio_data:
                # Concatenate all audio chunks
                audio_array = np.concatenate(self.audio_data, axis=0)

                # Generate filename with ISO timestamp
                timestamp = (
                    datetime.utcnow().isoformat().replace(":", "-").replace(".", "-")
                )
                filename = f"./data/{timestamp}.mp3"

                # Save audio file as MP3
                audio_segment = AudioSegment(
                    data=audio_array.tobytes(),
                    sample_width=audio_array.dtype.itemsize,
                    frame_rate=self.sample_rate,
                    channels=1,
                )
                audio_segment.export(filename, format="mp3")
                print(f"💾 Audio saved to: {filename}")
                duration = len(audio_array) / self.sample_rate
                print(f"📊 Duration: {duration:.1f} seconds")

                # Transcribe the audio in a separate thread to avoid blocking
                threading.Thread(
                    target=self.transcribe_audio, args=(filename,), daemon=True
                ).start()

            else:
                print("⚠️  No audio data to save")

        except Exception as e:
            print(f"❌ Failed to save recording: {e}")

    def handle_caps_lock_change(self, caps_lock_on):
        """Handle Caps Lock state changes."""
        if caps_lock_on and not self.caps_lock_on:
            # Caps Lock turned ON - start recording
            print("🔒 Caps Lock ON - starting recording")
            self.caps_lock_on = True
            self.icon_state = True
            self.icon = "on.png"
            self.start_recording()

        elif not caps_lock_on and self.caps_lock_on:
            # Caps Lock turned OFF - stop recording
            print("🔓 Caps Lock OFF - stopping recording")
            self.caps_lock_on = False
            self.icon_state = False
            self.icon = "off.png"
            self.stop_recording()

    def monitor_keys(self):
        """Monitor Caps Lock state changes."""
        print("🎯 Setting up Caps Lock event monitoring...")
        print("💡 Toggle Caps Lock on/off to control recording")
        print("🎤 Caps Lock ON = Start Recording, Caps Lock OFF = Stop Recording\n")

        def callback(proxy, type_, event, refcon):
            if type_ == kCGEventFlagsChanged:
                flags = CGEventGetFlags(event)
                caps_lock_on = bool(flags & CAPS_LOCK_MASK)

                print(
                    f"🔐 Caps Lock: {'🔒 ON' if caps_lock_on else '🔓 OFF'} (flags: {flags})"
                )
                self.handle_caps_lock_change(caps_lock_on)

            return event

        # Create event tap for Caps Lock monitoring
        print("🔧 Creating CGEventTap for Caps Lock...")
        mask = CGEventMaskBit(kCGEventFlagsChanged)
        tap = CGEventTapCreate(
            kCGHIDEventTap, kCGHeadInsertEventTap, 0, mask, callback, None
        )

        if tap is None:
            print("❌ Failed to create event tap! Check Accessibility permissions.")
            print("📝 Go to: System Settings → Privacy & Security → Accessibility")
            print("📝 Add Terminal (or Python) and enable it")
            return
        else:
            print("✅ Event tap created successfully")

        print("🔗 Setting up run loop source...")
        source = CFMachPortCreateRunLoopSource(None, tap, 0)
        if source is None:
            print("❌ Failed to create run loop source")
            return
        else:
            print("✅ Run loop source created")

        CFRunLoopAddSource(CFRunLoopGetCurrent(), source, kCFRunLoopCommonModes)
        CGEventTapEnable(tap, True)
        print("✅ Caps Lock monitoring active!")
        print("🧪 Turn Caps Lock ON to start recording, OFF to stop!")

        try:
            CFRunLoopRun()
        except KeyboardInterrupt:
            print("\n👋 Caps Lock monitoring stopped")

    @rumps.clicked("Toggle Icon")
    def toggle_icon(self, _):
        """Manually toggle the menu bar icon for testing purposes."""
        print("🔄 Manual toggle icon clicked")
        self.icon_state = not self.icon_state
        icon_name = "on.png" if self.icon_state else "off.png"
        self.icon = icon_name
        print(f"🎯 Manually toggled icon to: {icon_name}")

    @rumps.clicked("Quit")
    def quit_app(self, _):
        """Quit the application."""
        print("👋 Quit button clicked - shutting down app")
        rumps.quit_application()


if __name__ == "__main__":
    print("🎬 Starting Talk2Type application...")
    Talk2TypeApp().run()
