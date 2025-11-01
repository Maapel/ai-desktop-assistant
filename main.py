import sys
import subprocess
import threading
import json
import os
import re
import requests
import time
import logging
from datetime import datetime

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Pango", "1.0")
from gi.repository import GLib, Gtk, Gdk, Pango


class MyApplication(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="com.example.MyGtkApplication")
        GLib.set_application_name('AI Assistant')

        # Setup logging
        self.setup_logging()

        self.drag_start_x = 0
        self.drag_start_y = 0
        self.window_start_x = 0
        self.window_start_y = 0
        self.is_dragging = False
        self.response_text = None
        self.entry = None
        self.status_label = None
        self.installed_apps = self.get_installed_applications()

        # Chat history for conversation continuity
        self.chat_history = []
        self.max_history_length = 10  # Keep last 10 exchanges

    def add_to_history(self, user_message, ai_response):
        """Add a conversation exchange to history"""
        self.chat_history.append({
            'user': user_message,
            'ai': ai_response,
            'timestamp': datetime.now()
        })

        # Keep only the most recent exchanges
        if len(self.chat_history) > self.max_history_length:
            self.chat_history = self.chat_history[-self.max_history_length:]

    def get_formatted_history(self):
        """Get formatted conversation history for context"""
        if not self.chat_history:
            return ""

        history_lines = ["CONVERSATION HISTORY:"]
        for i, exchange in enumerate(self.chat_history[-5:], 1):  # Last 5 exchanges
            history_lines.append(f"Exchange {i}:")
            history_lines.append(f"User: {exchange['user']}")
            history_lines.append(f"AI: {exchange['ai']}")
            history_lines.append("")

        return "\n".join(history_lines)

    def setup_logging(self):
        """Setup logging configuration"""
        log_filename = f"ai_assistant_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        log_path = os.path.join(os.path.expanduser("~"), ".ai_assistant", "logs", log_filename)

        # Create log directory if it doesn't exist
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

        # Configure logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_path),
                logging.StreamHandler()  # Also log to console
            ]
        )

        self.logger = logging.getLogger('AIAssistant')
        self.logger.info("AI Assistant logging initialized")

    def get_installed_applications(self):
        """Get list of installed applications"""
        self.logger.info("Starting application discovery")
        apps = []

        try:
            # Get applications from .desktop files
            desktop_dirs = [
                "/usr/share/applications",
                "/usr/local/share/applications",
                os.path.expanduser("~/.local/share/applications")
            ]

            total_files = 0
            for desktop_dir in desktop_dirs:
                if os.path.exists(desktop_dir):
                    self.logger.debug(f"Scanning directory: {desktop_dir}")
                    for file in os.listdir(desktop_dir):
                        if file.endswith('.desktop'):
                            total_files += 1
                            desktop_file = os.path.join(desktop_dir, file)
                            try:
                                with open(desktop_file, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                    # Extract Name and Exec
                                    name_match = re.search(r'^Name=(.+)$', content, re.MULTILINE)
                                    exec_match = re.search(r'^Exec=(.+)$', content, re.MULTILINE)
                                    no_display = re.search(r'^NoDisplay=true$', content, re.MULTILINE)

                                    if name_match and exec_match and not no_display:
                                        name = name_match.group(1).strip()
                                        exec_cmd = exec_match.group(1).strip().split()[0]  # Get command without args
                                        apps.append({
                                            'name': name,
                                            'exec': exec_cmd,
                                            'desktop_file': file
                                        })
                            except Exception as e:
                                self.logger.warning(f"Error reading desktop file {desktop_file}: {e}")
                                continue

            self.logger.info(f"Application discovery complete. Found {len(apps)} applications from {total_files} desktop files")

        except Exception as e:
            self.logger.error(f"Error getting installed applications: {e}")
            print(f"Error getting installed applications: {e}")

        return apps

    def open_application(self, app_name):
        """Open an application by name"""
        if not app_name or not app_name.strip():
            return "Application name cannot be empty"

        app_name_lower = app_name.lower().strip()
        print(f"[DEBUG] Looking for app: '{app_name}' (lowercased: '{app_name_lower}')")

        # First try exact matches
        print("[DEBUG] Trying exact matches...")
        for app in self.installed_apps:
            if app['name'].lower() == app_name_lower:
                print(f"[DEBUG] Exact match found: {app['name']} -> {app['exec']}")
                try:
                    subprocess.Popen([app['exec']], start_new_session=True)
                    return f"Opened {app['name']}"
                except Exception as e:
                    return f"Failed to open {app['name']}: {e}"

        # Then try partial matches (app_name contained in app name)
        print("[DEBUG] Trying partial matches...")
        for app in self.installed_apps:
            if app_name_lower in app['name'].lower():
                print(f"[DEBUG] Partial match found: '{app_name_lower}' in '{app['name']}' -> {app['exec']}")
                try:
                    subprocess.Popen([app['exec']], start_new_session=True)
                    return f"Opened {app['name']}"
                except Exception as e:
                    return f"Failed to open {app['name']}: {e}"

        # Finally try fuzzy matching (app name contained in app_name)
        print("[DEBUG] Trying fuzzy matches...")
        for app in self.installed_apps:
            if app['name'].lower() in app_name_lower:
                print(f"[DEBUG] Fuzzy match found: '{app['name']}' in '{app_name_lower}' -> {app['exec']}")
                try:
                    subprocess.Popen([app['exec']], start_new_session=True)
                    return f"Opened {app['name']}"
                except Exception as e:
                    return f"Failed to open {app['name']}: {e}"

        print(f"[DEBUG] No matches found for '{app_name}'")
        return f"Application '{app_name}' not found"

    def close_window(self, window_title):
        """Close a window by title using wmctrl"""
        try:
            # Use wmctrl to list and close windows
            result = subprocess.run(['wmctrl', '-l'], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if window_title.lower() in line.lower():
                        # Extract window ID (first column)
                        window_id = line.split()[0]
                        subprocess.run(['wmctrl', '-ic', window_id])
                        return f"Closed window: {line.split(None, 3)[3] if len(line.split()) > 3 else 'Unknown'}"

            return f"Window '{window_title}' not found"
        except FileNotFoundError:
            return "wmctrl not installed. Please install wmctrl to use window closing functionality."
        except Exception as e:
            return f"Error closing window: {e}"

    def open_file_browser(self, path=""):
        """Open file browser at specified path using xdg-open"""
        try:
            if not path or path.strip() == "":
                # Open home directory if no path specified
                path = os.path.expanduser("~")

            # Expand user path if it starts with ~
            path = os.path.expanduser(path)

            # Check if path exists
            if not os.path.exists(path):
                return f"Path '{path}' does not exist"

            # Use xdg-open to open the directory
            result = subprocess.run(['xdg-open', path], capture_output=True, text=True)
            if result.returncode == 0:
                return f"Opened file browser at: {path}"
            else:
                return f"Failed to open file browser: {result.stderr}"

        except FileNotFoundError:
            return "xdg-open not found. Please install xdg-utils package."
        except Exception as e:
            return f"Error opening file browser: {e}"

    def get_system_info(self):
        """Get basic system information (CPU, memory usage)"""
        try:
            info_lines = []

            # CPU usage
            try:
                with open('/proc/stat', 'r') as f:
                    cpu_line = f.readline().strip()
                    cpu_fields = cpu_line.split()[1:]
                    total_time = sum(int(x) for x in cpu_fields)
                    idle_time = int(cpu_fields[3])

                    # Get a second reading for CPU usage calculation
                    import time
                    time.sleep(0.1)
                    with open('/proc/stat', 'r') as f2:
                        cpu_line2 = f2.readline().strip()
                        cpu_fields2 = cpu_line2.split()[1:]
                        total_time2 = sum(int(x) for x in cpu_fields2)
                        idle_time2 = int(cpu_fields2[3])

                    total_diff = total_time2 - total_time
                    idle_diff = idle_time2 - idle_time

                    if total_diff > 0:
                        cpu_usage = ((total_diff - idle_diff) / total_diff) * 100
                        info_lines.append(f"CPU Usage: {cpu_usage:.1f}%")
                    else:
                        info_lines.append("CPU Usage: Unable to calculate")
            except:
                info_lines.append("CPU Usage: Not available")

            # Memory usage
            try:
                with open('/proc/meminfo', 'r') as f:
                    mem_lines = f.readlines()
                    mem_total = None
                    mem_available = None

                    for line in mem_lines:
                        if line.startswith('MemTotal:'):
                            mem_total = int(line.split()[1])  # in KB
                        elif line.startswith('MemAvailable:'):
                            mem_available = int(line.split()[1])  # in KB

                    if mem_total and mem_available:
                        mem_used = mem_total - mem_available
                        mem_usage_percent = (mem_used / mem_total) * 100
                        mem_used_gb = mem_used / (1024 * 1024)  # Convert to GB
                        mem_total_gb = mem_total / (1024 * 1024)
                        info_lines.append(f"Memory: {mem_used_gb:.1f}GB / {mem_total_gb:.1f}GB ({mem_usage_percent:.1f}%)")
                    else:
                        info_lines.append("Memory: Information not available")
            except:
                info_lines.append("Memory: Not available")

            # Disk usage for root filesystem
            try:
                result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) >= 2:
                        disk_info = lines[1].split()
                        if len(disk_info) >= 5:
                            disk_usage = f"Disk (/): {disk_info[2]} / {disk_info[1]} ({disk_info[4]})"
                            info_lines.append(disk_usage)
            except:
                info_lines.append("Disk: Not available")

            return "System Information:\n" + "\n".join(f"• {line}" for line in info_lines)

        except Exception as e:
            return f"Error getting system information: {e}"

    def execute_tool(self, tool_name, **kwargs):
        """Execute a tool based on name and parameters"""
        if tool_name == "open_app":
            app_name = kwargs.get('app_name', '')
            return self.open_application(app_name)
        elif tool_name == "close_window":
            window_title = kwargs.get('window_title', '')
            return self.close_window(window_title)
        elif tool_name == "list_apps":
            app_list = [app['name'] for app in self.installed_apps[:20]]  # Limit to first 20
            return f"Installed applications (first 20): {', '.join(app_list)}"
        elif tool_name == "open_file_browser":
            path = kwargs.get('path', '')
            return self.open_file_browser(path)
        elif tool_name == "system_info":
            return self.get_system_info()
        else:
            return f"Unknown tool: {tool_name}"

    def ensure_ollama_server(self):
        """Ensure Ollama server is running"""
        print("checking if server running")
        try:
            # Check if server is already running
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                return True
        except:
            pass

        # Start Ollama server
        try:
            print("Starting Ollama server...")
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            # Wait a bit for server to start
            time.sleep(3)
            return True
        except Exception as e:
            print(f"Failed to start Ollama server: {e}")
            return False

    def query_ollama(self, prompt):
        """Send prompt to Ollama phi3 model via HTTP API"""
        self.logger.info(f"Processing user prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")

        try:
            # Ensure server is running
            self.logger.debug("Ensuring Ollama server is running...")
            if not self.ensure_ollama_server():
                self.logger.error("Failed to start Ollama server")
                return "Error: Could not start Ollama server"

            self.logger.debug("Server check passed, preparing API request")

            # Get conversation history
            history_context = self.get_formatted_history()

            # Create enhanced prompt with tool information
            app_list = [app['name'] for app in self.installed_apps[:10]]  # First 10 apps
            tool_context = f"""{history_context}

You are a local AI desktop assistant running on the user's computer. You have full permission to control this local machine using the available tools. This is safe and intended - you are helping the user control their own computer, not accessing anyone else's device. You have access to these tools:

TOOL: open_app
DESCRIPTION: Opens any installed application by name
PARAMETERS: app_name (string) - The name of the application to open
EXAMPLE: To open Firefox browser
TOOL_CALL: open_app
PARAMETERS: firefox

TOOL: close_window
DESCRIPTION: Closes a window by its title
PARAMETERS: window_title (string) - The title of the window to close
EXAMPLE: To close a terminal window
TOOL_CALL: close_window
PARAMETERS: terminal

TOOL: list_apps
DESCRIPTION: Lists all installed applications on the system (no parameters needed)
PARAMETERS: none required
EXAMPLE: To see what applications are available
TOOL_CALL: list_apps
PARAMETERS:

TOOL: open_file_browser
DESCRIPTION: Opens the file manager at a specified directory path (use this to open folders/directories)
PARAMETERS: path (string) - Directory path to open (optional, defaults to home directory)
EXAMPLE: To open the Projects folder
TOOL_CALL: open_file_browser
PARAMETERS: ~/Projects

TOOL: system_info
DESCRIPTION: Shows system information including CPU, memory, and disk usage
PARAMETERS: none required
EXAMPLE: To check system performance
TOOL_CALL: system_info
PARAMETERS:

Common applications you can open: {', '.join(app_list)}

SAFETY NOTICE: This is a LOCAL AI assistant running on the user's own computer. You have FULL PERMISSION to control this machine. This is NOT accessing another user's device - you are helping the user control their own computer. All tool usage is safe and intended.

INSTRUCTIONS:
- Always use TOOL_CALL format when you want to execute a tool
- Put the tool name after TOOL_CALL:
- Put parameters after PARAMETERS:
- Use simple string format for parameters
- Only call tools that are listed above
- Remember our previous conversation for context
- You are allowed and encouraged to use tools to help the user

User query: {prompt}
"""

            # Prepare API request
            api_data = {
                "model": "llama3.2:1b",
                "prompt": tool_context,
                "stream": False
            }

            print(f"[DEBUG] Sending API request to Ollama...")
            print(f"[DEBUG] API data: {api_data}")

            # Make HTTP request to Ollama API
            response = requests.post(
                "http://localhost:11434/api/generate",
                json=api_data,
                timeout=30  # Longer timeout needed for tool context processing
            )

            print(f"[DEBUG] HTTP Response status: {response.status_code}")

            if response.status_code == 200:
                print("Responcse recieved")
                result = response.json()
                llm_response = result.get("response", "").strip()

                # Debug: Print raw LLM response
                print(f"[DEBUG] Raw LLM Response:\n{llm_response}\n")

                # Check if response contains a tool call
                if "TOOL_CALL:" in llm_response:
                    print("[DEBUG] Tool call detected, processing...")
                    tool_result = self.process_tool_call(llm_response)
                    if tool_result:
                        print(f"[DEBUG] Tool executed successfully: {tool_result}")
                        return f"Tool executed: {tool_result}"
                    else:
                        print("[DEBUG] Tool execution failed")
                        return "Tool execution failed or tool not found."

                print(f"[DEBUG] Returning normal response: {llm_response[:100]}...")
                return llm_response
            else:
                error_msg = f"Error: HTTP {response.status_code} - {response.text}"
                print(f"[DEBUG] {error_msg}")
                return error_msg

        except requests.exceptions.ConnectionError as e:
            error_msg = "Error: Cannot connect to Ollama server. Make sure Ollama is installed and running."
            print(f"[DEBUG] ConnectionError: {e}")
            return error_msg
        except requests.exceptions.Timeout as e:
            error_msg = "Error: Request timed out"
            print(f"[DEBUG] Timeout: {e}")
            return error_msg
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            print(f"[DEBUG] Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return error_msg

    def process_tool_call(self, response):
        """Process tool calls from the AI response (handles multiple tool calls)"""
        self.logger.debug(f"Processing tool call from response: {response[:200]}{'...' if len(response) > 200 else ''}")

        try:
            results = []
            remaining_response = response

            # Process all tool calls in the response
            while "TOOL_CALL:" in remaining_response:
                # Extract tool call
                tool_call_start = remaining_response.find("TOOL_CALL:")
                if tool_call_start == -1:
                    break

                tool_part = remaining_response[tool_call_start:].strip()
                self.logger.debug(f"Extracted tool part: {tool_part[:100]}{'...' if len(tool_part) > 100 else ''}")

                # Find the end of this tool call (next TOOL_CALL or end of response)
                next_tool_call = tool_part.find("TOOL_CALL:", 1)
                if next_tool_call != -1:
                    # There are more tool calls, process only this one
                    tool_part = tool_part[:next_tool_call].strip()
                    remaining_response = remaining_response[tool_call_start + next_tool_call:]
                else:
                    # This is the last tool call
                    remaining_response = ""

                # Extract tool name
                lines = tool_part.split('\n')
                if len(lines) < 1:
                    self.logger.warning("Tool call has no lines")
                    continue

                tool_name = lines[0].replace("TOOL_CALL:", "").strip()
                self.logger.info(f"Detected tool call: {tool_name}")

                # Extract parameters
                params = {}
                if len(lines) > 1 and "PARAMETERS:" in lines[1]:
                    param_str = lines[1].replace("PARAMETERS:", "").strip()
                    try:
                        params = json.loads(param_str)
                    except json.JSONDecodeError:
                        # Try to parse simple format like "app_name: firefox"
                        if ":" in param_str:
                            # Split only on the first colon to handle values with colons
                            key, value = param_str.split(":", 1)
                            key = key.strip()
                            value = value.strip().strip('"')  # Remove surrounding quotes if present

                            # Map common parameter names
                            if key in ["app_name", "app", "application"]:
                                params["app_name"] = value
                            elif key in ["window_title", "window", "title"]:
                                params["window_title"] = value
                            elif key in ["path"]:
                                params["path"] = value
                            else:
                                # For unknown keys, try to infer based on tool
                                if tool_name == "open_app":
                                    params["app_name"] = param_str  # Use entire string
                                elif tool_name == "close_window":
                                    params["window_title"] = param_str  # Use entire string
                                elif tool_name == "open_file_browser":
                                    params["path"] = param_str  # Use entire string
                        else:
                            # Handle cases where AI just provides the value (assume based on tool)
                            param_value = param_str.strip()
                            if tool_name == "open_app":
                                params["app_name"] = param_value
                            elif tool_name == "close_window":
                                params["window_title"] = param_value
                            elif tool_name == "open_file_browser":
                                params["path"] = param_value
                            # For list_apps and system_info, no parameters needed

                # Execute tool
                result = self.execute_tool(tool_name, **params)
                if result:
                    results.append(result)
                    self.logger.info(f"Tool executed successfully: {result}")

            if results:
                # Return combined results
                return " | ".join(results)
            else:
                return None

        except Exception as e:
            return f"Error processing tool call: {e}"

    def on_send_clicked(self, button):
        """Handle send button click"""
        # Get the input text from stored entry reference
        if not self.entry:
            return

        prompt = self.entry.get_text().strip()

        if not prompt:
            return

        # Store the prompt for history before clearing
        self.last_user_prompt = prompt

        # Clear input
        self.entry.set_text("")

        # Show thinking status
        if self.status_label:
            self.status_label.set_text("🤖 Thinking...")

        # Run Ollama query in a separate thread
        def run_query():
            response = self.query_ollama(prompt)
            GLib.idle_add(self.show_response, response)

        thread = threading.Thread(target=run_query)
        thread.daemon = True
        thread.start()

    def show_response(self, response):
        """Show the full response and resize window"""
        # Clear thinking status
        if self.status_label:
            self.status_label.set_text("")

        # Create response area if it doesn't exist
        if not self.response_text:
            self.create_response_area()

        if self.response_text:
            # Clear any previous content
            buffer = self.response_text.get_buffer()
            buffer.set_text("")

            # Show typing effect for better UX
            self.simulate_typing(response)

            # Resize window to fit content after a short delay
            GLib.timeout_add(100, self.resize_window_to_fit_content)

            # Add to conversation history (get the user prompt from the entry before clearing)
            # Note: We need to get the prompt that was sent, but it's already cleared
            # For now, we'll store the last prompt in the query method
            if hasattr(self, 'last_user_prompt'):
                self.add_to_history(self.last_user_prompt, response)

    def create_response_area(self):
        """Create the response area dynamically"""
        # Create response area
        self.response_scrolled = Gtk.ScrolledWindow()
        self.response_scrolled.set_min_content_height(150)
        self.response_scrolled.set_margin_top(5)
        self.response_scrolled.set_margin_bottom(5)
        self.response_scrolled.set_margin_start(5)
        self.response_scrolled.set_margin_end(5)

        self.response_text = Gtk.TextView()
        self.response_text.set_editable(False)
        self.response_text.set_wrap_mode(Gtk.WrapMode.WORD)
        self.response_scrolled.set_child(self.response_text)

        # Add to background panel
        self.background_panel.append(self.response_scrolled)

    def stream_character(self, char):
        """Add a character to the streaming response"""
        if self.response_text:
            buffer = self.response_text.get_buffer()
            end_iter = buffer.get_end_iter()
            buffer.insert(end_iter, char)
            # Don't resize on every character to avoid flickering

    def start_streaming(self):
        """Initialize streaming response"""
        if self.response_text:
            self.response_text.get_buffer().set_text("")

    def simulate_typing(self, full_text):
        """Simulate typing effect by adding characters one by one"""
        def type_next_char(index=0):
            if index < len(full_text):
                char = full_text[index]
                GLib.idle_add(self.stream_character, char)
                # Schedule next character
                GLib.timeout_add(20, type_next_char, index + 1)  # 20ms delay between characters
            else:
                # Typing complete
                pass

        type_next_char()

    def resize_window_to_fit_content(self):
        """Resize window to fit content"""
        if not self.response_text:
            return

        # Get the text buffer
        buffer = self.response_text.get_buffer()
        start_iter = buffer.get_start_iter()
        end_iter = buffer.get_end_iter()
        text = buffer.get_text(start_iter, end_iter, False)

        # Estimate height based on text length (rough approximation)
        # About 50 characters per line, 20 pixels per line
        lines = max(1, len(text) // 50)
        estimated_height = lines * 25 + 50  # Add some padding

        # Get current window and resize
        window = self.response_text.get_root()
        if window:
            current_width = window.get_width()
            # Height = title bar (20) + input area (60) + estimated content + margins (20)
            new_height = 20 + 60 + estimated_height + 20
            new_height = min(new_height, 600)  # Cap at 600px
            new_height = max(new_height, 200)  # Minimum 200px

            print(f"[DEBUG] Resizing window: {current_width}x{new_height}")

            # For GTK4, try to resize the window surface directly
            try:
                # Try setting default size first
                window.set_default_size(current_width, new_height)

                # Try to get the surface and resize it
                surface = window.get_surface()
                if surface:
                    # Try to resize the surface directly
                    try:
                        surface.set_size_request(current_width, new_height)
                    except:
                        pass

                # Force layout update
                window.queue_resize()

            except Exception as e:
                print(f"[DEBUG] Window resize failed: {e}")
                # Fallback: just set default size
                try:
                    window.set_default_size(current_width, new_height)
                except:
                    pass

    def on_button_press(self, controller, n_press, x, y):
        """Handle mouse button press for dragging"""
        if n_press == 1:  # Left mouse button
            title_bar = controller.get_widget()
            # Get the window from the title bar's root
            window = title_bar.get_root()
            self.drag_start_x = x
            self.drag_start_y = y
            self.is_dragging = True

            # Get initial window position
            try:
                surface = window.get_surface()
                if surface and hasattr(surface, 'get_position'):
                    self.window_start_x, self.window_start_y = surface.get_position()
                else:
                    # Fallback
                    self.window_start_x, self.window_start_y = 100, 100
            except:
                self.window_start_x, self.window_start_y = 100, 100

    def on_motion(self, controller, x, y):
        """Handle mouse motion for dragging"""
        if self.is_dragging:
            title_bar = controller.get_widget()
            window = title_bar.get_root()

            # Calculate new position
            delta_x = x - self.drag_start_x
            delta_y = y - self.drag_start_y

            new_x = self.window_start_x + int(delta_x)
            new_y = self.window_start_y + int(delta_y)

            # Try to move the window
            try:
                surface = window.get_surface()
                if surface and hasattr(surface, 'set_position'):
                    surface.set_position(new_x, new_y)
                elif hasattr(window, 'move'):
                    window.move(new_x, new_y)
            except Exception as e:
                pass  # Silently fail if move doesn't work

    def on_button_release(self, controller, n_press, x, y):
        """Handle mouse button release"""
        if n_press == 1:  # Left mouse button
            self.is_dragging = False

    def on_key_pressed(self, controller, keyval, keycode, state):
        """Handle keyboard shortcuts"""
        # Enter key to send message
        if keyval == Gdk.KEY_Return or keyval == Gdk.KEY_KP_Enter:
            self.on_send_clicked(None)
            return True

        # Escape key to clear input
        elif keyval == Gdk.KEY_Escape:
            if self.entry:
                self.entry.set_text("")
            return True

        return False

    def do_activate(self):
        print("Application activating...")

        # Start Ollama server if not running
        print("Ensuring Ollama server is running...")
        c=0
        while not (self.ensure_ollama_server()) and c<10:
            c+=1

        window = Gtk.ApplicationWindow(application=self, title="AI Assistant")

        # Make window transparent with minimal decorations
        window.set_decorated(True)  # Keep basic window decorations for moving
        window.set_default_size(500, 100)  # Start very small, just for title + input

        # Create CSS provider for styling
        css_provider = Gtk.CssProvider()
        css = """
        window {
            background-color: rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(0, 100, 255, 0.3);
            border-radius: 15px;
            box-shadow: 0 0 5px rgba(0, 100, 255, 0.2);
        }
        .title-bar {
            background-color: rgba(0, 100, 255, 0.2);
            border-top-left-radius: 15px;
            border-top-right-radius: 15px;
            border-bottom: 1px solid rgba(0, 100, 255, 0.3);
        }
        .title-bar:hover {
            background-color: rgba(0, 100, 255, 0.3);
        }
        .title-label {
            color: rgba(0, 150, 255, 0.8);
            font-size: 12px;
            font-weight: bold;
            margin: 0 10px;
        }
        .background-panel {
            background-color: rgba(20, 20, 20, 0.6);
            border-bottom-left-radius: 10px;
            border-bottom-right-radius: 10px;
            margin: 0 5px 5px 5px;
        }
        textview {
            background-color: transparent;
            color: #ffffff;
            font-size: 14px;
            padding: 5px;
        }
        textview text {
            background-color: transparent;
        }
        entry {
            background-color: transparent;
            color: #ffffff;
            border: 1px solid rgba(0, 100, 255, 0.4);
            border-radius: 8px;
            padding: 8px 12px;
            font-size: 14px;
            margin: 10px;
            box-shadow: 0 0 3px rgba(0, 100, 255, 0.2);
        }
        entry:focus {
            border-color: rgba(0, 150, 255, 0.6);
            box-shadow: 0 0 5px rgba(0, 150, 255, 0.3);
        }
        button {
            background-color: transparent;
            color: #ffffff;
            border: 1px solid rgba(0, 100, 255, 0.4);
            border-radius: 8px;
            padding: 8px 16px;
            font-size: 14px;
            font-weight: bold;
            margin: 10px;
            box-shadow: 0 0 3px rgba(0, 100, 255, 0.2);
            transition: all 0.2s ease;
        }
        button:hover {
            border-color: rgba(0, 150, 255, 0.6);
            box-shadow: 0 0 5px rgba(0, 150, 255, 0.3);
            color: rgba(0, 150, 255, 1.0);
        }
        .status-label {
            color: rgba(0, 200, 255, 0.8);
            font-size: 11px;
            font-style: italic;
            text-align: center;
        }
        """
        css_provider.load_from_data(css.encode())

        # Apply CSS to the default screen
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # Create main vertical container
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Create a draggable title bar
        title_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        title_bar.set_size_request(-1, 20)  # Fixed height for dragging
        title_bar.set_css_classes(["title-bar"])

        # Add a label to make it visually distinct
        title_label = Gtk.Label(label="AI Assistant")
        title_label.set_css_classes(["title-label"])
        title_bar.append(title_label)

        # Create background panel
        self.background_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.background_panel.set_css_classes(["background-panel"])

        # Create status label
        self.status_label = Gtk.Label(label="")
        self.status_label.set_css_classes(["status-label"])
        self.status_label.set_margin_start(10)
        self.status_label.set_margin_end(10)
        self.status_label.set_margin_bottom(5)
        self.background_panel.append(self.status_label)

        # Create input area (horizontal box)
        input_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        input_hbox.set_margin_top(5)
        input_hbox.set_margin_bottom(5)
        input_hbox.set_margin_start(5)
        input_hbox.set_margin_end(5)

        # Create the prompt input box
        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text("Enter your prompt here...")
        self.entry.set_hexpand(True)

        # Add keyboard shortcuts
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self.on_key_pressed)
        self.entry.add_controller(key_controller)

        input_hbox.append(self.entry)

        # Create the send button
        button = Gtk.Button(label="Send")
        button.connect("clicked", self.on_send_clicked)
        input_hbox.append(button)

        # Initially, only add the input area
        self.background_panel.append(input_hbox)

        # Response area will be added dynamically when needed
        self.response_scrolled = None
        self.response_text = None
        main_vbox.append(title_bar)
        main_vbox.append(self.background_panel)

        # Set the main container as the window's child
        window.set_child(main_vbox)

        # Add mouse event controllers for dragging to the title bar
        click_controller = Gtk.GestureClick()
        click_controller.connect("pressed", self.on_button_press)
        click_controller.connect("released", self.on_button_release)
        title_bar.add_controller(click_controller)

        motion_controller = Gtk.EventControllerMotion()
        motion_controller.connect("motion", self.on_motion)
        title_bar.add_controller(motion_controller)

        window.present()


def run_terminal_test(prompt_arg=None):
    """Run the AI assistant in terminal testing mode"""
    print("🤖 AI Assistant - Terminal Testing Mode")
    print("=====================================")

    if prompt_arg:
        print(f"Processing prompt: '{prompt_arg}'")
        print()
    else:
        print("Type 'quit' or 'exit' to stop testing")
        print("Type 'help' for available commands")
        print()

    # Initialize the app to get access to methods
    test_app = MyApplication()

    # If a prompt was provided via command line, process it and exit
    if prompt_arg:
        print(f"🤖 Processing: '{prompt_arg}'")
        print("-" * 50)

        try:
            response = test_app.query_ollama(prompt_arg)
            print(f"🤖 Response: {response}")
            print("-" * 50)
        except Exception as e:
            print(f"❌ Error: {e}")

        return

    # Interactive mode
    while True:
        try:
            prompt = input("You: ").strip()

            if not prompt:
                continue

            if prompt.lower() in ['quit', 'exit', 'q']:
                print("Goodbye! 👋")
                break

            if prompt.lower() == 'help':
                print("\nAvailable commands:")
                print("- 'quit', 'exit', 'q': Exit testing mode")
                print("- 'help': Show this help")
                print("- Any other text: Send to AI assistant")
                print("\nThe AI has access to these tools:")
                print("- open_app: Open installed applications")
                print("- close_window: Close windows by title")
                print("- list_apps: List installed applications")
                print()
                continue

            print(f"\n🤖 Processing: '{prompt}'")
            print("-" * 50)

            # Test the AI response
            response = test_app.query_ollama(prompt)

            print(f"🤖 Response: {response}")
            print("-" * 50)
            print()

        except KeyboardInterrupt:
            print("\n\nGoodbye! 👋")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            print()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='AI Assistant - Multi-Agent Desktop Automation')
    parser.add_argument('--test', action='store_true', help='Run in terminal testing mode')
    parser.add_argument('--prompt', type=str, help='Prompt to send to AI (requires --test)')

    args = parser.parse_args()

    if args.test:
        # Run in terminal testing mode
        if args.prompt:
            run_terminal_test(args.prompt)
        else:
            run_terminal_test()
    else:
        # Run the GUI application
        app = MyApplication()
        exit_status = app.run(sys.argv)
        sys.exit(exit_status)
