# 🤖 AI Assistant - Multi-Agent Desktop Automation

A powerful AI assistant with desktop automation capabilities built with GTK4 and Ollama.

## Features

- **Multi-Agent System**: AI can execute tools to interact with your desktop
- **Tool Integration**: Open apps, close windows, list applications
- **Beautiful GUI**: Modern transparent interface with drag functionality
- **Terminal Testing**: Easy command-line testing mode
- **Debug Logging**: Comprehensive logging for development

## Installation

1. **Install Dependencies**:
   ```bash
   pip install requests
   sudo apt install wmctrl  # For window management
   ```

2. **Install Ollama**:
   ```bash
   curl -fsSL https://ollama.ai/install.sh | sh
   ollama pull llama3.2:1b  # Fast model for testing
   ```

3. **Run the Application**:
   ```bash
   python3 main.py
   ```

## Usage

### GUI Mode (Default)
```bash
python3 main.py
```
- Launches the beautiful GTK interface
- Type messages in the input box
- AI responds with tool execution or conversation

### Terminal Testing Mode
```bash
python3 main.py --test
```

**Direct Prompt Mode:**
```bash
python3 main.py --test --prompt "Open Firefox"
```

**Commands Available (Interactive Mode):**
- `help` - Show available commands and tools
- `quit`, `exit`, `q` - Exit testing mode
- Any text - Send to AI assistant

**Example Session:**
```
🤖 AI Assistant - Terminal Testing Mode
=====================================
Type 'quit' or 'exit' to stop testing
Type 'help' for available commands

You: help

Available commands:
- 'quit', 'exit', 'q': Exit testing mode
- 'help': Show this help
- Any other text: Send to AI assistant

The AI has access to these tools:
- open_app: Open installed applications
- close_window: Close windows by title
- list_apps: List installed applications

You: Open Firefox
🤖 Processing: 'Open Firefox'
--------------------------------------------------
[DEBUG] Starting query_ollama with prompt: Open Firefox
[DEBUG] Ensuring Ollama server is running...
[DEBUG] Server check passed, preparing API request
[DEBUG] Sending API request to Ollama...
[DEBUG] HTTP Response status: 200
Responcse recieved
[DEBUG] Raw LLM Response:
TOOL_CALL: open_app
PARAMETERS: Firefox

[DEBUG] Tool call detected, processing...
[DEBUG] Tool executed successfully: Opened Firefox Web Browser
🤖 Response: Tool executed: Opened Firefox Web Browser
--------------------------------------------------
```

## Available Tools

### 1. open_app
Opens installed applications by name.
```python
TOOL_CALL: open_app
PARAMETERS: firefox
```

### 2. close_window
Closes windows by their title.
```python
TOOL_CALL: close_window
PARAMETERS: terminal
```

### 3. list_apps
Lists all installed applications.
```python
TOOL_CALL: list_apps
PARAMETERS:  # No parameters needed
```

## Architecture

- **GTK4 Interface**: Modern, draggable GUI
- **Ollama Integration**: Local LLM with HTTP API
- **Tool System**: Extensible multi-agent framework
- **Application Discovery**: Automatic scanning of .desktop files
- **Window Management**: wmctrl integration for window control

## Development

### Adding New Tools
1. Add tool function to `MyApplication` class
2. Register in `execute_tool()` method
3. Update prompt context with tool description
4. Test in terminal mode

### Debug Logging
All operations include comprehensive debug output:
- Server status checks
- API requests/responses
- Tool execution details
- Application matching logic

## Future Enhancements

See `tool_suggestions.md` for planned features:
- File system operations
- System information tools
- Web browsing capabilities
- Media controls
- Productivity automation

## Troubleshooting

**Timeout Issues:**
- Use `llama3.2:1b` model for faster responses
- Increase timeout in `query_ollama()` if needed

**Tool Not Working:**
- Check debug output for parameter parsing
- Verify application names in terminal mode
- Ensure wmctrl is installed for window operations

**Server Issues:**
- Run `ollama serve` manually if auto-start fails
- Check `http://localhost:11434/api/tags` for server status

---

**Built with ❤️ using GTK4, Ollama, and Python**
