# api.py: Handles all API requests to the GroupMe API

import requests
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base URL for the GroupMe API
BASE_URL = "https://api.groupme.com/v3"

def load_config():
    """
    Load the entire config.json file.

    Returns:
        dict: Configuration data.

    Raises:
        FileNotFoundError: If config.json is not found.
        json.JSONDecodeError: If config.json is malformed.
    """
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
            logger.info("Configuration loaded successfully.")
            return config
    except FileNotFoundError:
        logger.error("config.json not found. Please create it.")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Malformed config.json: {e}")
        raise

def get_authenticated_user(token):
    """
    Fetch details about the authenticated user to test the token.

    Args:
        token (str): Access token for authentication.

    Returns:
        dict: User information.

    Raises:
        Exception: If the API request fails.
    """
    url = f"{BASE_URL}/users/me"
    params = {"token": token}
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        return response.json()["response"]
    else:
        error_msg = f"API request failed: {response.status_code} - {response.text}"
        logger.error(error_msg)
        raise Exception(error_msg)

def get_user_groups(token):
    """
    Fetch the authenticated user's active groups.

    Args:
        token (str): Access token for authentication.

    Returns:
        list: List of group dictionaries.

    Raises:
        Exception: If the API request fails.
    """
    url = f"{BASE_URL}/groups"
    params = {"token": token, "per_page": 10}
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        return response.json()["response"]
    else:
        error_msg = f"Failed to fetch groups: {response.status_code} - {response.text}"
        logger.error(error_msg)
        raise Exception(error_msg)

def get_group_messages(token, group_id, since_id=None):
    """
    Fetch messages from a specific group.

    Args:
        token (str): Access token for authentication.
        group_id (str): ID of the group to fetch messages from.
        since_id (str, optional): Fetch messages after this ID.

    Returns:
        list: List of message dictionaries.

    Raises:
        Exception: If the API request fails.
    """
    url = f"{BASE_URL}/groups/{group_id}/messages"
    params = {"token": token, "limit": 20}
    if since_id:
        params["since_id"] = since_id
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        return response.json()["response"]["messages"]
    elif response.status_code == 304:
        # No new messages
        return []
    else:
        error_msg = f"Failed to fetch messages: {response.status_code} - {response.text}"
        logger.error(error_msg)
        raise Exception(error_msg)

def create_bot(token, group_id, bot_name="MyBot", callback_url=None):
    """
    Create a bot in a specific group with an optional callback URL.

    Args:
        token (str): Access token for authentication.
        group_id (str): ID of the group to create the bot in.
        bot_name (str, optional): Name of the bot. Defaults to "MyBot".
        callback_url (str, optional): Callback URL for the bot.

    Returns:
        str: Bot ID of the created bot.

    Raises:
        Exception: If the API request fails.
    """
    url = f"{BASE_URL}/bots"
    data = {
        "bot": {
            "name": bot_name,
            "group_id": group_id
        }
    }
    if callback_url:
        data["bot"]["callback_url"] = callback_url
    params = {"token": token}
    response = requests.post(url, json=data, params=params)
    
    if response.status_code == 201:
        bot_id = response.json()["response"]["bot_id"]
        logger.info(f"Bot created successfully with ID: {bot_id}")
        return bot_id
    else:
        error_msg = f"Failed to create bot: {response.status_code} - {response.text}"
        logger.error(error_msg)
        raise Exception(error_msg)

# DEV: Fix the updating callback process if needed in the future, for now this just warns if there is a mismatch
def check_bot_callback(token, bot_id, callback_url):
    """
    Update the bot's callback URL.

    Args:
        token (str): Access token for authentication.
        bot_id (str): ID of the bot to update.
        callback_url (str): New callback URL.

    Raises:
        Exception: If the API request fails.
    """
    url = f"{BASE_URL}/bots"
    params = {"token": token}
    response = requests.get(url, params=params)
    # logger.info(response.json())

    update_callback = None
    
    if response.status_code == 200:
        bots = response.json()["response"]
        found = False
        for bot in bots:
            if bot["bot_id"] == bot_id:
                found = True
                if bot.get("callback_url") == callback_url:
                    logger.info(f"Bot ID {bot_id} has the correct callback URL: {callback_url}")
                else:
                    current_url = bot.get("callback_url", "None")
                    logger.warning(f"Bot ID {bot_id} has an incorrect callback URL. Current: {current_url}, Requested: {callback_url}.")
                    bot["callback_url"] = callback_url
                    update_callback = bot
                break

        if not found:
            logger.warning(f"Bot with ID {bot_id} not found")
            raise Exception(f"Bot with ID {bot_id} not found")
    else:
        error_msg = f"Failed to perform bots get request: {response.status_code} - {response.text}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    if update_callback is not None:
        data = {
            "bot": update_callback
        }
        logger.info(data)
    
    # if update_callback is not None:
    #     response = requests.post(url, json=update_callback, params=params)
    #     if response.status_code == 201:
    #         logger.info(f"Bot ID {bot_id} callback URL updated successfully.")
    #     else:
    #         error_msg = f"Failed to update bot callback URL: {response.status_code} - {response.text}"
    #         logger.error(error_msg)
    #         raise Exception(error_msg)

def create_text_data(bot_id, text):
    data = {
        "bot_id": bot_id,
        "text": text
    }
    return data

def create_image_data(bot_id, img_url):
    data = {
        "bot_id": bot_id,
        "text": "",
        "attachments": [
            {
                "type": "image",
                "url": img_url
            }
        ]
    }
    return data

def post_message(token, bot_id, text):
    """
    Post a message using a bot.

    Args:
        token (str): Access token for authentication.
        bot_id (str): ID of the bot to post the message.
        text (str): Message text to post.

    Returns:
        bool: True if the message was posted successfully.

    Raises:
        Exception: If the API request fails.
    """
    url = f"{BASE_URL}/bots/post"
    if text[:10] == "https://i.":
        data = create_image_data(bot_id, text)
    else:
        data = create_text_data(bot_id, text)

    response = requests.post(url, json=data)
    
    if response.status_code in (201, 202):
        logger.info("Message posted successfully.")
        return True
    else:
        error_msg = f"Failed to post message: {response.status_code} - {response.text}"
        logger.error(error_msg)
        raise Exception(error_msg)