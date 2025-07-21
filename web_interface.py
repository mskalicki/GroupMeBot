from flask import Flask, render_template, request, redirect, url_for, flash, Response
from commands import load_commands  # Assuming this module exists
from functools import wraps
import json
import logging
import os
import fcntl

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration from config.json
try:
    with open("config.json", "r") as config_file:
        config = json.load(config_file)
except FileNotFoundError:
    logger.error("config.json not found. Please create it with required settings.")
    raise
except json.JSONDecodeError:
    logger.error("Invalid JSON in config.json.")
    raise

# Initialize Flask app
app = Flask(__name__)
app.secret_key = config.get("secret_key", "default-secret-key")  # Fallback if not set

def save_commands(commands):
    """Save updated commands to commands.json with file locking."""
    try:
        with open("commands.json", "w") as f:
            try:
                # Attempt to acquire an exclusive lock (Unix systems)
                fcntl.flock(f, fcntl.LOCK_EX)
                json.dump(commands, f, indent=4)
                fcntl.flock(f, fcntl.LOCK_UN)  # Release lock
            except AttributeError:
                # Fallback for Windows or systems without fcntl
                json.dump(commands, f, indent=4)
        logger.info("commands.json updated successfully")
    except Exception as e:
        logger.error(f"Error saving commands.json: {e}")
        raise

# Authentication functions
def check_auth(username, password):
    """Check if provided credentials match those in config.json."""
    return username == config.get("admin_username", "admin") and password == config.get("admin_password", "secret")

def authenticate():
    """Send a 401 response to prompt for credentials."""
    return Response('Login Required', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})

def require_auth(f):
    """Decorator to require authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

@app.route('/commands')
@require_auth
def show_commands():
    """Render a page displaying all commands from commands.json."""
    try:
        commands = load_commands()
        return render_template('commands.html', commands=commands)
    except Exception as e:
        logger.error(f"Error loading commands: {e}")
        return str(e), 500

@app.route('/commands/add', methods=['GET'])
@require_auth
def add_command_page():
    """Render a page to add a new command."""
    return render_template('add_command.html')

@app.route('/commands/add', methods=['POST'])
@require_auth
def add_command():
    """Add a new command to commands.json."""
    try:
        commands = load_commands()
        new_command = request.form.get('new_command', '').strip()
        responses = request.form.getlist('response[]')
        if not new_command:
            flash("Command name cannot be empty.", "error")
            return render_template('add_command.html', new_command=new_command, responses=responses)
        if new_command in commands:
            flash(f"Command '{new_command}' already exists.", "error")
            return render_template('add_command.html', new_command=new_command, responses=responses)
        updated_responses = [{"responseLine1": r.strip()} for r in responses if r.strip()]
        commands[new_command] = updated_responses
        save_commands(commands)
        flash(f"Command '{new_command}' added successfully!", "success")
        return redirect(url_for('show_commands'))
    except Exception as e:
        logger.error(f"Error adding command: {e}")
        flash(f"Error: {str(e)}", "error")
        return render_template('add_command.html', new_command=new_command, responses=responses)

@app.route('/commands/edit/<command>', methods=['GET'])
@require_auth
def edit_command(command):
    """Render a page to edit a specific command."""
    try:
        commands = load_commands()
        if command not in commands:
            flash(f"Command '{command}' not found.", "error")
            return redirect(url_for('show_commands'))
        responses = commands[command]
        return render_template('edit_command.html', command=command, responses=responses)
    except Exception as e:
        logger.error(f"Error loading command {command}: {e}")
        return str(e), 500

@app.route('/commands/edit/<command>', methods=['POST'])
@require_auth
def save_command(command):
    """Save changes to a specific command and update commands.json."""
    try:
        commands = load_commands()
        if command not in commands:
            flash(f"Command '{command}' not found.", "error")
            return redirect(url_for('show_commands'))
        new_responses = request.form.getlist('response[]')
        updated_responses = [{"responseLine1": resp.strip()} for resp in new_responses if resp.strip()]
        commands[command] = updated_responses
        save_commands(commands)
        flash(f"Command '{command}' updated successfully!", "success")
        return redirect(url_for('show_commands'))
    except Exception as e:
        logger.error(f"Error saving command {command}: {e}")
        flash(f"Error: {str(e)}", "error")
        return redirect(url_for('edit_command', command=command))

@app.route('/commands/delete', methods=['POST'])
@require_auth
def delete_command():
    """Delete a specific command from commands.json."""
    try:
        command = request.form.get('command')
        if not command:
            flash("No command specified.", "error")
            return redirect(url_for('show_commands'))
        commands = load_commands()
        if command in commands:
            del commands[command]
            save_commands(commands)
            flash(f"Command '{command}' deleted successfully!", "success")
        else:
            flash(f"Command '{command}' not found.", "error")
        return redirect(url_for('show_commands'))
    except Exception as e:
        logger.error(f"Error deleting command: {e}")
        flash(f"Error: {str(e)}", "error")
        return redirect(url_for('show_commands'))

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors with a custom page."""
    return render_template('error.html', error=error), 500

if __name__ == "__main__":
    app.run(
        host=config.get("host", "0.0.0.0"),
        port=config.get("port", 5001)
    )