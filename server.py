from flask import Flask, request, jsonify, send_from_directory,render_template
from flask_cors import CORS
from datetime import datetime
import os
import json

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
log_file_path = 'logs.json'
state_file_path = 'elements_state.json'

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

    # Append log entry to the log file
    try:
        # Load existing logs if the file exists
        if os.path.exists(log_file_path):
            with open(log_file_path, 'r') as f:
                existing_logs = json.load(f)
        else:
            existing_logs = []

        # Append the new entry and write back
        existing_logs.append(logs[-1])
        with open(log_file_path, 'w') as f:
            json.dump(existing_logs, f, indent=4)
    except json.JSONDecodeError:
        # Handle case where log file is corrupted or empty
        with open(log_file_path, 'w') as f:
            json.dump([logs[-1]], f, indent=4)

    return jsonify({'message': 'State updated successfully', 'state': elements_state}), 200

@app.route('/logs-raw', methods=['GET'])
def get_logs():
    return jsonify(logs)

# @app.route('/logs')
# def serve_logs_view():
#     return send_from_directory(app.static_folder, 'logs.html')

@app.route('/logs')
def serve_logs_view():
    return render_template('logs.html', logs=logs)


@app.route('/state', methods=['GET'])
def get_state():
    return jsonify(elements_state)

@app.route('/navbar')
def navbar():
    return render_template('navbar.html')

# MARK: Vacuum State


# Initialize the elements state from the file (if it exists)
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


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000,debug=True)

