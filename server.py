from flask import Flask, request, jsonify, send_from_directory
from flask import render_template,send_file, session, redirect
from flask import url_for
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet
from datetime import datetime
import os, json, csv

import pandas as pd
import plotly.express as px
import plotly.io as pio
from plotly.subplots import make_subplots
import plotly.graph_objects as go

SETTINGS_FILE = "settings.json"
log_file_path = 'logs.csv'
state_file_path = 'elements_state.json'
MAX_LOGS = 1000
DISPLAY_LIMIT = 100
LAST_PLOT_FILE = "last_plot.html"
last_plot_html = None 

app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app) 

@app.route('/')
def home():
    return render_template('index.html')


# History routes (before catch-all so /history/* is not served as static)
@app.route('/history')
def serve_history_view():
    return render_template('history.html')


@app.route('/history/events', methods=['GET'])
def get_history_events():
    """Return parsed log events as JSON for history timeline."""
    events = load_history_events()
    payload = [
        {
            "ts": e["ts"].strftime("%Y-%m-%d %H:%M:%S"),
            "id": e["id"],
            "state": e["state"],
            "user": e["user"],
        }
        for e in events
    ]
    return jsonify(payload)


@app.route('/history/state/<int:idx>', methods=['GET'])
def get_history_state(idx):
    """Return reconstructed diagram state at history index idx."""
    events = load_history_events()
    if idx < 0 or idx >= len(events):
        return jsonify({"error": "Invalid index"}), 400
    state_now = elements_state_to_bool(elements_state)
    reconstructed = state_at_index(events, state_now, idx)
    return jsonify({"index": idx, "state": reconstructed})


@app.route('/<path:path>')
def serve_static_files(path):
    return send_from_directory(app.static_folder, path)

# Backend routes
elements_state = {}
logs = []

def load_settings():
    """Load settings from a JSON file."""
    if not os.path.exists(SETTINGS_FILE):
        raise FileNotFoundError(f"Settings file '{SETTINGS_FILE}' not found.")
    
    with open(SETTINGS_FILE, 'r') as file:
        try:
            settings = json.load(file)
        except json.JSONDecodeError as e:
            raise ValueError(f"Error parsing '{SETTINGS_FILE}': {e}")
    
    if 'CUDATA_DIRECTORY' not in settings:
        raise KeyError("Missing 'CUDATA_DIRECTORY' in settings.")
    
    return settings['CUDATA_DIRECTORY']

def load_logs_from_csv(file_path):
    """load logs from csv"""
    logs = []
    try:
        with open(file_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Convert timestamp back to the desired format
                row["timestamp"] = row["timestamp"]  # If needed, parse with datetime
                logs.append(row)
    except FileNotFoundError:
        print(f"Log file {file_path} not found.")
    return logs


# MARK: History (reverse state replay)
def load_history_events(file_path=None):
    """
    Load logs.csv and return events as list of:
    {"ts": datetime, "id": str, "state": bool, "user": str}
    Order preserved as in file (chronological).
    """
    path = file_path or log_file_path
    events = []
    try:
        with open(path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ts_str = row.get("timestamp", "")
                try:
                    ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    ts = datetime.min
                status = (row.get("status", "inactive") or "inactive").strip().lower()
                state = status == "active"
                events.append({
                    "ts": ts,
                    "id": row.get("id", ""),
                    "state": state,
                    "user": row.get("user", ""),
                })
    except FileNotFoundError:
        pass
    return events


def state_at_index(events, state_now, idx):
    """
    Reconstruct diagram state at history index `idx` by reverse-applying
    later events. Log entries are absolute state assignments; we restore
    the previous value (prev), not toggle. Returns {id: bool}.
    """
    state = dict(state_now)
    # Precompute prev[i] = state of event[i].id before this event (from last prior modification)
    last_by_id = {}
    prev = [None] * len(events)
    for i in range(len(events)):
        pid = events[i]["id"]
        prev[i] = last_by_id.get(pid)
        last_by_id[pid] = events[i]["state"]
    # Reverse replay: undo each event after idx by restoring prev (most recent first)
    for i in range(len(events) - 1, idx, -1):
        e = events[i]
        rid = e["id"]
        if prev[i] is not None:
            state[rid] = prev[i]
        else:
            state[rid] = False
    return state


def elements_state_to_bool(d):
    """Convert {id: 'active'|'inactive'} to {id: bool}."""
    return {k: (v == "active") for k, v in d.items()}

@app.route('/download_logs')
def download_logs():
    # Return the file as a download
    return send_file(log_file_path, as_attachment=True)

# MARK: Update
@app.route('/update', methods=['POST'])
def update_element():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    username = session['username']
    element_id = data.get('id')
    status = data.get('status')
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not element_id or not status:
        return jsonify({'error': 'Invalid data'}), 400

    # Update the state
    elements_state[element_id] = status

    # Save updated state to file
    with open(state_file_path, 'w') as f:
        json.dump(elements_state, f, indent=4)

    # Log the change with username
    logs.append({
        'timestamp': timestamp,
        'id': element_id,
        'status': status,
        'user': username,
    })
    save_log_csv({
        "timestamp": timestamp,
        "id": element_id,
        "status": status,
        "user": username
    }, log_file_path)

    return jsonify({'message': 'State updated successfully', 'state': elements_state}), 200

def save_log_csv(log_entry, log_file_path):
    """Append a log entry to a CSV file."""
    # Ensure the log file exists and create it with headers if not
    file_exists = os.path.exists(log_file_path)
    try:
        with open(log_file_path, 'a', newline='') as csvfile:
            fieldnames = ["timestamp","id", "status","user"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            # Write header only if the file is new
            if not file_exists:
                writer.writeheader()

            # Format timestamp as string if not already formatted
            if isinstance(log_entry.get("timestamp"), datetime):
                log_entry["timestamp"] = log_entry["timestamp"].strftime("%Y-%m-%d %H:%M:%S")

            # Write the log entry
            writer.writerow(log_entry)
    except Exception as e:
        print(f"Error saving log entry: {e}")



@app.route('/logs-raw', methods=['GET'])
def get_logs():
    return jsonify(logs)

@app.route('/state', methods=['GET'])
def get_state():
    return jsonify(elements_state)

@app.route('/navbar')
def navbar():
    return render_template('navbar.html')

# MARK: Vacuum State
if os.path.exists(state_file_path):
    with open(state_file_path, 'r') as f:
        elements_state = json.load(f)
else:
    elements_state = {}

# Fetch the current state of all elements
@app.route('/elements-state', methods=['GET'])
def get_elements_state():
    return jsonify(elements_state)

@app.route('/elements-config', methods=['GET'])
def serve_config():
    return send_from_directory(directory='./static', path='elementsConfig.json')

# MARK: Plotly
@app.route('/plasmaplots')
def plasmaplots():
    files = [f for f in os.listdir(load_settings()) if f.endswith('.csv') and f.startswith('cu_')]

    def parse_datetime_from_filename(fname):
        datetime_str = fname[3:3+15]  # Extract the datetime part: YYYYMMDD_HHMMSS
        return datetime.strptime(datetime_str, "%Y%m%d_%H%M%S")

    files.sort(key=parse_datetime_from_filename, reverse=True)

    return render_template('plasmaplots.html', files=files)


@app.route('/plot', methods=['POST','GET'])
def plot_file():
    global last_plot_html
    file_name = request.form['file']
    file_path = os.path.join(load_settings(), file_name)
    columns = get_cu_columns(file_path)
    df = pd.read_csv(file_path, skiprows=10,names=columns)
    plot_html = generate_plot_html(df, ['Ip_c'],['Pu_c','Pd_c','Bu_c'])
    last_plot_html = plot_html
    with open(LAST_PLOT_FILE, 'w', encoding='utf-8') as f:
        f.write(plot_html)
    return jsonify(plot=plot_html)

@app.route('/get_last_plot', methods=['GET'])
def get_last_plot():
    global last_plot_html
    if last_plot_html:
        print("last plot in memory")
        return jsonify({'plot': last_plot_html})
    try:
        # Fallback to disk if the variable is not set
        with open(LAST_PLOT_FILE, 'r', encoding='utf-8') as f:
            return jsonify({'plot': f.read()})
    except FileNotFoundError:
        return jsonify({'plot': '<p>No plot available. Please generate one.</p>'}), 404
    except Exception as e:
        print(f"Error reading last plot: {e}")
        return jsonify({'plot': f'<p>Error fetching last plot, plot something first?: {e}</p>'}), 500

def generate_plot_html(df,columns_lin, columns_log):
    # Create subplots with shared x-axis
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1, 
    )

    # Add traces for the linear y-axis plot
    for column in columns_lin:
        fig.add_trace(
            go.Scatter(x=df['date'], y=df[column], mode='lines', name=column),
            row=1, col=1
        )

    # Add traces for the log y-axis plot
    for column in columns_log:
        fig.add_trace(
            go.Scatter(x=df['date'], y=df[column], mode='lines', name=column),
            row=2, col=1
        )

    # Update layout
    fig.update_layout(
        height=800,
        yaxis=dict(title="Signals (Linear)", type="linear"),
        yaxis2=dict(title="Signals (Log)", type="log",tickformat=".1e"),
        legend=dict(title="Signals"),
    )

    return pio.to_html(fig, full_html=False)


def get_cu_columns(file_path):
    with open(file_path, 'r') as file:
        for line in file:
            if line.startswith('# Columns'):
                columns = line.split(',', 1)[1].strip().split(', ')
                break
    return columns 

@app.route('/download_controlunit_csv', methods=['GET'])
def download_controlunit_csv():
    file_name = request.args.get('file')
    if not file_name:
        return "No file specified", 400

    file_path = os.path.join(load_settings(), file_name)

    if not os.path.isfile(file_path):
        return "File not found", 404

    return send_file(file_path, as_attachment=True, download_name=file_name)

# MARK: LOGIN
app.secret_key = 'app secret key'
USERS_FILE_ENCRYPTED = "users.json.enc"
DECRYPTED_FILE_TEMP = "users.json"

def load_key():
    try:
        with open("secret.key", "rb") as key_file:
            key = key_file.read()
            return key
    except FileNotFoundError:
        raise ValueError("Key file 'secret.key' not found. Please generate it first.")


def decrypt_users_file():
    key = load_key()
    fernet = Fernet(key)

    with open(USERS_FILE_ENCRYPTED, "rb") as encrypted_file:
        encrypted_data = encrypted_file.read()

    decrypted_data = fernet.decrypt(encrypted_data)

    with open(DECRYPTED_FILE_TEMP, "wb") as decrypted_file:
        decrypted_file.write(decrypted_data)

def load_users():
    # Decrypt the file
    decrypt_users_file()

    # Load users
    with open(DECRYPTED_FILE_TEMP, "r") as file:
        users = json.load(file)

    # Clean up: optionally delete the temporary decrypted file
    os.remove(DECRYPTED_FILE_TEMP)

    return users

# Load the users at startup
users = load_users()

# Login route
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    if username in users and check_password_hash(users[username], password):
        session['username'] = username
        return jsonify({"message": "Login successful", "username": username}), 200
    return jsonify({"message": "Invalid username or password"}), 401

@app.route('/logout', methods=['GET'])
def logout():
    session.pop('username', None)
    return redirect(url_for('login_page'))

@app.route('/loginpage', methods=['GET'])
def login_page():
    return render_template('login.html')

@app.route('/get_current_user', methods=['GET'])
def get_current_user():
    is_authenticated = 'username' in session
    username = session.get('username', None)
    return jsonify({"is_authenticated": is_authenticated, "username": username})



if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000,debug=True)

