# bot.py: Orchestrates the bot’s operation

from api import load_config, get_authenticated_user, get_user_groups, create_bot, check_bot_callback
from utils import sleep
from callback_server import app
from commands import load_commands, update_commands
import threading
import json
import logging
import os
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_bot(token, callback_url, saved_group_id):
    """
    Set up the bot with a callback URL.

    Args:
        token (str): Access token for authentication.
        callback_url (str): Callback URL for the bot.
        saved_group_id (str): Previously saved group ID, if any.

    Returns:
        str: Group ID to use for the bot.

    Raises:
        Exception: If no groups are found or API calls fail.
    """
    # Fetch user info
    user_info = get_authenticated_user(token)
    logger.info(f"Authenticated as: {user_info['name']} (ID: {user_info['id']})")
    
    # Fetch groups
    groups = get_user_groups(token)
    if not groups:
        error_msg = "No groups found. Join a group first!"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    # Display groups
    logger.info("Your groups:")
    for i, group in enumerate(groups):
        logger.info(f"{i + 1}. {group['name']} (ID: {group['id']})")
    
    # Check if a saved group ID was provided and exists
    if saved_group_id:
        saved_group = next((group for group in groups if group['id'] == saved_group_id), None)
        if saved_group:
            logger.info(f"Using saved group: {saved_group['name']} (ID: {saved_group_id})")
            group_id = saved_group_id
        else:
            logger.warning(f"Saved group ID {saved_group_id} not found. Defaulting to the first group.")
            group_id = groups[0]["id"]
    else:
        group_id = groups[0]["id"]
        logger.info(f"No saved group ID provided. Using the first group: {groups[0]['name']} (ID: {group_id})")
    
    return group_id

def monitor_commands():
    """
    Background thread to monitor commands.json for changes and reload if modified.
    """
    last_mtime = None
    while True:
        try:
            current_mtime = os.path.getmtime("commands.json")
            if last_mtime is None or current_mtime > last_mtime:
                commands = load_commands()
                update_commands(commands)
                last_mtime = current_mtime
        except Exception as e:
            logger.error(f"Failed to reload commands.json: {e}")
        sleep(5)  # Check every 5 seconds

def run_bot(token, bot_id, group_id, callback_url):
    """
    Run the bot with callback support.

    Args:
        token (str): Access token for authentication.
        bot_id (str): ID of the bot.
        group_id (str): ID of the group the bot is in.
        callback_url (str): Callback URL for the bot.
    """
    # Initial load of commands
    try:
        commands = load_commands()
        update_commands(commands)
    except Exception as e:
        logger.error(f"Initial load of commands failed: {e}")
        return
    
    # Start the command monitoring thread
    command_thread = threading.Thread(target=monitor_commands, daemon=True)
    command_thread.start()
    logger.info("Started command monitoring thread")

    # Update the bot's callback URL
    try:
        check_bot_callback(token, bot_id, callback_url)
        logger.info(f"Callback URL checked for Bot ID: {bot_id}")
    except Exception as e:
        logger.error(f"Failed to update callback URL: {e}")
        return
    
    logger.info(f"Bot setup complete with Bot ID: {bot_id}. Starting callback server...")
    
    # Run Flask server in a separate thread
    server_thread = threading.Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": 5000})
    server_thread.daemon = True
    server_thread.start()
    logger.info(f"Callback server running. Pinggy URL should be set to {callback_url}")
    
    # Keep the main thread alive
    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")

def main():
    """
    Main function to run the bot.
    """
    # Load configuration
    try:
        config = load_config()
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return
    
    token = config.get("access_token")
    saved_group_id = config.get("group_id")
    bot_id = config.get("bot_id")
    callback_url = config.get("callback_url")
    
    if not token:
        logger.error("Access token not found in config.json")
        return
    
    if not callback_url:
        logger.error("Callback URL not found in config.json")
        return
    
    if not bot_id:
        logger.info("No bot_id found in config.json. Creating a new bot...")
        try:
            group_id = setup_bot(token, callback_url, saved_group_id)
            bot_id = create_bot(token, group_id, callback_url=callback_url)
            config["bot_id"] = bot_id
            with open("config.json", "w") as f:
                json.dump(config, f, indent=4)
            logger.info(f"Bot created with ID: {bot_id}")
        except Exception as e:
            logger.error(f"Failed to create bot: {e}")
            return
    else:
        try:
            group_id = setup_bot(token, callback_url, saved_group_id)
        except Exception as e:
            logger.error(f"Failed to set up bot: {e}")
            return
    
    run_bot(token, bot_id, group_id, callback_url)

if __name__ == "__main__":
    main()