from flask import Flask, request, jsonify, send_from_directory,render_template,send_file
from flask_cors import CORS
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

#app = Flask(__name__, static_folder='static')
app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app) # Allow all origins

# # Serve the frontend
# @app.route('/')
# def serve_frontend():
#    return send_from_directory(app.static_folder, 'index.html')

@app.route('/')
def home():
    return render_template('index.html')

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

@app.route('/download_logs')
def download_logs():
    # Return the file as a download
    return send_file(log_file_path, as_attachment=True)

@app.route('/update', methods=['POST'])
def update_element():
    data = request.json
    print(data)
    element_id = data.get('id')
    status = data.get('status')  # 'active' or 'inactive'
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")#.isoformat()
    print(f"Element {element_id} status updated to {status}")

    if not element_id or not status:
        return jsonify({'error': 'Invalid data'}), 400

    # Update the state
    elements_state[element_id] = status

    # Save updated state to file
    with open(state_file_path, 'w') as f:
        json.dump(elements_state, f, indent=4)

    # Log the change
    logs.append({
        'id': element_id,
        'status': status,
        'timestamp': timestamp#.strftime("%Y-%m-%d %H:%M:%S")
    })
    #save_log_json(logs[-1],log_file_path)
    save_log_csv(logs[-1],log_file_path)

    return jsonify({'message': 'State updated successfully', 'state': elements_state}), 200

def save_log_json(log_entry,log_file_path):
    """Load json log, append, rewrite"""
    try:
        if os.path.exists(log_file_path):
            with open(log_file_path, 'r') as f:
                existing_logs = json.load(f)
        else:
            existing_logs = []

        existing_logs.append(log_entry)
        with open(log_file_path, 'w') as f:
            json.dump(existing_logs, f, indent=4)
    except json.JSONDecodeError:
        # Handle case where log file is corrupted or empty
        with open(log_file_path, 'w') as f:
            json.dump([log_entry], f, indent=4)


def save_log_csv(log_entry, log_file_path):
    """Append a log entry to a CSV file."""
    # Ensure the log file exists and create it with headers if not
    file_exists = os.path.exists(log_file_path)
    try:
        with open(log_file_path, 'a', newline='') as csvfile:
            fieldnames = ["timestamp","id", "status"]
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

# @app.route('/logs')
# def serve_logs_view():
#     return send_from_directory(app.static_folder, 'logs.html')

# @app.route('/logs')
# def serve_logs_view():
#     sorted_logs = sorted(logs, key=lambda log: log['timestamp'], reverse=True)
#     return render_template('logs.html', logs=sorted_logs)

@app.route('/logs')
def serve_logs_view():
    # Load logs from CSV file
    logs_file_path = "logs.csv"
    logs = load_logs_from_csv(logs_file_path)

    # Sort logs by timestamp, most recent first
    sorted_logs = sorted(logs, key=lambda log: log['timestamp'], reverse=True)

    # Limit logs to the display limit
    limited_logs = sorted_logs[:DISPLAY_LIMIT]

    # Truncate the logs list to maintain size
    logs = sorted_logs[:MAX_LOGS]

    return render_template('logs.html', logs=limited_logs)


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
# Directory to list files from
CUDATA_DIRECTORY = load_settings()

@app.route('/plasmaplots')
def plasmaplots():
    # Get list of CSV files
    files = [f for f in os.listdir(CUDATA_DIRECTORY) if f.endswith('.csv')]
    return render_template('plasmaplots.html', files=files)

@app.route('/plot', methods=['POST','GET'])
def plot_file():
    # Get selected file from the form
    file_name = request.form['file']
    file_path = os.path.join(CUDATA_DIRECTORY, file_name)
    columns = get_cu_columns(file_path)
    # Load data
    df = pd.read_csv(file_path, skiprows=10,names=columns)

    plot_html = generate_plot_html(df, ['Ip_c'],['Pu_c','Pd_c','Bu_c'])
    return jsonify(plot=plot_html)


def simple_plot():
    columns_to_plot = ['Ip_c', 'Pu_c','Pd_c','Bu_c']
    fig = px.line(df, x='date', y=columns_to_plot)  # Adjust columns as needed
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Signals",
        legend_title="Signal Types",
    )

    return pio.to_html(fig, full_html=False)


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



if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000,debug=True)

