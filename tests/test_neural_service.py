import json
import threading
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer

import pandas as pd
import pytest

from flyworld.brain_adapter import NeuralFrame, empty_spikes
from flyworld.neural_service import NeuralService, handler_for
from flyworld.experiments import get_experiment


class Adapter:
    def __init__(self, experiment, block_ms):
        self.ready = True
        self.pending = False
        self.error = ''
        self.population = 138639
        self.setup_s = 1
        self.frames = []
        self.requests = []
        self.closed = False

    def poll(self):
        if self.frames:
            self.pending = False
            return self.frames.pop(0)

    def request(self, intensity, world_s):
        self.pending = True
        self.requests.append((intensity, world_s))

    def close(self):
        self.closed = True


def test_sensory_request_bounded_and_no_fallback():
    s = NeuralService(Adapter)
    assert s.step(.5, 0)['state'] == 'stopped'
    s.start()
    s.step(.25, 1)
    s.step(1, 2)
    assert s.adapter.requests == [(.25, 1)]
    assert 'frame' not in s.status(True)
    s.adapter.frames.append(NeuralFrame(0, 20, empty_spikes(), .1, 138639, 'sugar', .25, 1))
    result = s.status(True)['frame']
    assert result['command'] == [0, 0]
    assert result['spikes'] == 0
    assert 'frame' not in s.status(True)


def test_real_decoder_only_p9_counts_and_log(tmp_path):
    s = NeuralService(Adapter, tmp_path/'blocks.jsonl')
    s.start()
    left, right = get_experiment('p9')['neu_exc']
    spikes = pd.DataFrame({'flywire_id': [left, right, 123], 'time_ms': [1, 2, 3]})
    s.adapter.frames.append(NeuralFrame(0, 20, spikes, .1, 138639, 'sugar', .8, 2))
    result = s.status(True)['frame']
    assert result['p9_hz'] == 50
    assert result['command'] == [.5, 0]
    assert result['p9_ids'] == [str(left), str(right)]
    assert json.loads((tmp_path/'blocks.jsonl').read_text()) == result
    s.adapter.error = 'network failed'
    assert s.step(1, 3)['state'] == 'error'
    assert 'frame' not in s.status(True)


def test_protocol_switch_closes_old_network_and_requires_explicit_calibration():
    s = NeuralService(Adapter)
    s.start()
    old = s.adapter
    s.start('p9')
    assert old.closed
    s.step(1, 0)
    assert s.adapter.requests == [(0, 0)]
    s.adapter.pending = False
    s.step(0, 1, calibration=1)
    assert s.adapter.requests[-1] == (1, 1)
    s.close()
    assert s.status()['state'] == 'stopped'


def test_reconnect_replaces_a_failed_worker():
    s = NeuralService(Adapter)
    s.start()
    old = s.adapter
    old.error = 'failed'
    assert s.start()['state'] == 'ready'
    assert old.closed
    assert s.adapter is not old
    s.close()


@pytest.mark.parametrize('food,time', [(float('nan'), 0), (1, float('inf')), (-1, 0), (2, 0), (.5, -1), (True, 0)])
def test_invalid_sensors(food, time):
    with pytest.raises(ValueError):
        NeuralService(Adapter).step(food, time)


def test_http_origin_and_json_boundary(tmp_path):
    s = NeuralService(Adapter)
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(s, tmp_path))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f'http://127.0.0.1:{server.server_port}/api/neural/start'
    try:
        request = Request(url, b'{}', headers={'Content-Type': 'application/json'})
        with urlopen(request) as response:
            assert json.load(response)['state'] == 'ready'
        request.add_header('Origin', 'https://unrelated.example')
        with pytest.raises(HTTPError) as error:
            urlopen(request)
        assert error.value.code == 403
        request = Request(url, b'[]', headers={'Content-Type': 'application/json'})
        with pytest.raises(HTTPError) as error:
            urlopen(request)
        assert error.value.code == 400
    finally:
        server.shutdown()
        server.server_close()
        s.close()
