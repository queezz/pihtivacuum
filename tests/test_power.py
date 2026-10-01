from test_server import make_app


def test_power_snapshot_identity_validation_and_conflict(tmp_path):
    path = tmp_path / 'power.jsonl'
    client = make_app(tmp_path, POWER_LOG_FILE=path).test_client()
    assert client.get('/power').status_code == 200
    assert client.get('/power/state').json['state'] == {}
    assert not path.exists()
    payload = {'state': {'anode-power-switch': 'on', 'anode-plug-switch': 'plugged', 'cathode-water': 'on'}, 'base_timestamp': None}
    assert client.post('/power/state', json=payload).status_code == 428
    with client.session_transaction() as session:
        session['username'] = 'Preview'
    assert client.post('/power/state', json={'state': {'bad': 'on'}}).status_code == 400
    assert client.post('/power/state', json={'state': {'anode-plug-switch': 'on'}}).status_code == 400
    assert client.post('/power/state', json={'state': {'anode-power-switch': 'on'}}).status_code == 400
    assert client.post('/power/state', json={'state': {'plasma-ig-gauge': 'on'}}).status_code == 400
    result = client.post('/power/state', json=payload)
    assert result.status_code == 200
    assert result.json['operator'] == 'Preview'
    assert client.post('/power/state', json=payload).status_code == 409
    assert len(path.read_text().splitlines()) == 1
    assert make_app(tmp_path, POWER_LOG_FILE=path).test_client().get('/power/state').json == result.json
