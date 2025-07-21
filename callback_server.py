# callback_server.py: Handles incoming GroupMe callback requests

from flask import Flask, request
from api import load_config, post_message
from commands import process_message
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load config once at startup
try:
    config = load_config()
    TOKEN = config["access_token"]
    BOT_ID = config["bot_id"]
except Exception as e:
    logger.error(f"Failed to load configuration: {e}")
    raise

@app.route('/callback', methods=['POST'])
def handle_callback():
    """
    Process incoming callback data from GroupMe.

    Returns:
        tuple: Empty string and 200 status code.
    """
    try:
        data = request.get_json()
        logger.info(f"Received callback: {data}")
        response = process_message(data)
        if response:
            logger.info(f"Responding with: {response}")
            post_message(TOKEN, BOT_ID, response)
    except Exception as e:
        logger.error(f"Error processing callback: {e}")
    return '', 200

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)