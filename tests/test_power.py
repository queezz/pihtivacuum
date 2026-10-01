import json
from test_server import make_app


def power_app(tmp_path):
    return make_app(tmp_path, POWER_LOG_FILE=tmp_path / 'legacy.jsonl',
                    POWER_HISTORY_FILE=tmp_path / 'power.csv')


def identify(client):
    with client.session_transaction() as session:
        session['username'] = 'Preview'


def test_read_only_and_separate_history(tmp_path):
    app = power_app(tmp_path)
    client = app.test_client()
    assert client.get('/power').status_code == 200
    assert client.get('/power/history').status_code == 200
    assert client.get('/power/state').json['state'] == {}
    assert client.post('/power/update', json={'id': 'cathode-water', 'status': 'active'}).status_code == 428
    assert client.post('/power/practice/save', json={'presses': [{'id': 'cathode-water', 'status': 'active'}]}).status_code == 428
    assert not (tmp_path / 'power.csv').exists()
    identify(client)
    assert client.post('/power/update', json={'id': 'cathode-water', 'status': 'active'}).status_code == 200
    assert client.get('/power/state').json['state']['cathode-water'] == 'active'
    events = client.get('/power/history/events').json
    assert len(events) == 1 and events[0]['user'] == 'Preview'
    assert client.get('/history/events').json == []
    assert b'cathode-water' in client.get('/power/download_logs').data
    assert not (tmp_path / 'state.json').exists()
    assert power_app(tmp_path).test_client().get('/power/state').json == client.get('/power/state').json


def test_power_dependencies_are_one_record_and_unplug_clears_filament(tmp_path):
    client = power_app(tmp_path).test_client()
    identify(client)
    result = client.post('/power/update', json={'id': 'plasma-ig-gauge', 'status': 'active'})
    assert result.status_code == 200
    state = result.json['state']
    assert state['plasma-ig-power'] == state['plasma-ig-plug-switch'] == state['plasma-ig-gauge'] == 'active'
    assert len(client.get('/power/history/events').json) == 1
    result = client.post('/power/update', json={'id': 'plasma-ig-plug-switch', 'status': 'inactive'})
    assert all(value == 'inactive' for value in result.json['state'].values())
    assert len(client.get('/power/history/events').json) == 2


def test_practice_sequence_and_invalid_input(tmp_path):
    client = power_app(tmp_path).test_client()
    identify(client)
    for item in ({'id': 'GVU', 'status': 'active'}, {'id': 'cathode-water', 'status': 'bad'}, None):
        assert client.post('/power/update', json=item).status_code == 400
    assert client.post('/power/practice/save', json={'presses': []}).status_code == 400
    presses = [{'id': 'anode-power-switch', 'status': 'active'}, {'id': 'cathode-water', 'status': 'active'}]
    result = client.post('/power/practice/save', json={'presses': presses, 'auto': True})
    assert result.status_code == 200
    events = client.get('/power/history/events').json
    assert len(events) == 1 and len(events[0]['changes']) == 3
    assert events[0]['note'] == 'practice sequence, 2 presses, saved by the timer'
    assert client.get('/history/events').json == []


def test_legacy_power_snapshots_remain_in_power_history(tmp_path):
    path = tmp_path / 'legacy.jsonl'
    path.write_text(json.dumps({'timestamp': '2026-10-01T10:00:00+09:00', 'operator': 'Preview',
                               'state': {'cathode-water': 'on', 'anode-plug-switch': 'unplugged'}}) + '\n')
    before = path.read_bytes()
    client = power_app(tmp_path).test_client()
    assert client.get('/power/state').json['state']['cathode-water'] == 'active'
    assert len(client.get('/power/history/events').json) == 1
    assert client.get('/history/events').json == []
    assert path.read_bytes() == before
