# Talk2Type

A macOS menu bar app that converts speech to text using OpenAI Whisper. Hold backspace for 1+ second to record, release to transcribe and auto-type into any application.

## Installation

```bash
git clone https://github.com/username/talk2type.git
cd talk2type
make init
make install
```

## Configuration

### 1. Set OpenAI API Key
```bash
export OPENAI_API_KEY="your-api-key-here"
```

### 2. Grant Mac Permissions

**Accessibility Permission:**
- System Settings → Privacy & Security → Accessibility
- Add Terminal and enable it

**Microphone Permission:**
- System Settings → Privacy & Security → Microphone
- Add Terminal and enable it

## Usage

1. Start the app:
   ```bash
   make run
   ```

2. Look for the menu bar icon (white = idle, green = recording)

3. To dictate text:
   - Click in any text field
   - Hold Backspace for 1+ second
   - Speak clearly while icon is green
   - Release Backspace to stop and auto-type

## Troubleshooting

- **No keyboard detection**: Check Accessibility permissions
- **No audio recording**: Check Microphone permissions
- **Transcription fails**: Verify API key is set
- **Text doesn't appear**: Ensure cursor is in a text field

Audio files are saved in `./data/` for debugging.
