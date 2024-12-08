from flask import Flask, request, jsonify, send_from_directory,render_template
from flask_cors import CORS
from datetime import datetime

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


@app.route('/update', methods=['POST'])
def update_element():
    data = request.json
    element_id = data.get('id')
    status = data.get('status')  # 'active' or 'inactive'
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")#.isoformat()
    print(f"Element {element_id} status updated to {status}")

    if not element_id or not status:
        return jsonify({'error': 'Invalid data'}), 400

    # Update the state
    elements_state[element_id] = status

    # Log the change
    logs.append({
        'id': element_id,
        'status': status,
        'timestamp': timestamp#.strftime("%Y-%m-%d %H:%M:%S")
    })

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


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000,debug=True)

