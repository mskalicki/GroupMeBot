# commands.py: Manages bot commands and responses loaded from commands.json

import json
import logging
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variable to store commands loaded from JSON, with a lock for thread safety
COMMANDS = {}
COMMANDS_LOCK = threading.Lock()

def load_commands():
    """
    Load commands from commands.json file.

    The file should be formatted as:
    {
        "!command": [
            {"responseLine1": "line1"},
            {"responseLine1": "line2"},
            ...
        ],
        ...
    }

    Returns:
        dict: Dictionary mapping commands to their responses.

    Raises:
        FileNotFoundError: If commands.json is not found.
        json.JSONDecodeError: If commands.json is malformed.
    """
    try:
        with open("commands.json", "r") as f:
            commands = json.load(f)
            logger.info("Commands loaded successfully from commands.json")
            return commands
    except FileNotFoundError:
        logger.error("commands.json not found. Please create it.")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Malformed commands.json: {e}")
        raise

def update_commands(commands):
    """
    Update the global COMMANDS variable with new commands in a thread-safe way.

    Args:
        commands (dict): New commands dictionary to set.
    """
    with COMMANDS_LOCK:
        global COMMANDS
        COMMANDS = commands
        logger.info("COMMANDS updated dynamically")

def process_message(message):
    """
    Check if a message contains a command and return the response.

    Args:
        message (dict): Message data from GroupMe, expected to have 'sender_type' and 'text' keys.

    Returns:
        str or None: Response message (possibly multi-line with newlines) if a command is found,
                     else None.
    """
    
    logger = logging.getLogger(__name__)
    logger.info("process_message called")
    
    
    
    if message.get("sender_type") == "bot":
        # Ignore bot messages to prevent loops
        return None
    
    text = message.get("text", "").strip()
    logger.info(f"Processing message: {text}")
    
    # Access COMMANDS with lock for thread safety
    with COMMANDS_LOCK:
        response_data = COMMANDS.get(text)
    
    if response_data is None:
        return None
    
    # If the response is a list (multi-line), process it
    if isinstance(response_data, list):
        # Extract responseLine1 from each item and join with newlines
        lines = [item.get("responseLine1", "") for item in response_data if isinstance(item, dict)]
        return "\n".join(lines) if lines else None
    
    # If it's a simple string (for backward compatibility, though not expected)
    if isinstance(response_data, str):
        return response_data
    
    # Unexpected format
    logger.warning(f"Invalid response format for command '{text}': {response_data}")
    return None