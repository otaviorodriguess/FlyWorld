"""Loopback bridge between the 3D garden and the persistent full Brian2 network.

No navigation policy, target coordinates, or synthetic spikes live here. The
only current sensory mapping is food intensity -> the upstream sugar GRNs.
P9 stimulation is a separate, explicitly selected motor calibration protocol.
"""
import argparse
import json
import math
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .brain_adapter import LiveAdapter
from .config import ROOT
from .neural_decoder import NeuralDecoder


class NeuralService:
    def __init__(self, adapter_factory=LiveAdapter, log_path=None):
        self.factory = adapter_factory
        self.adapter = None
        self.experiment = 'sugar'
        self.decoder = NeuralDecoder()
        self.lock = threading.Lock()
        self.frame = None
        self.sequence = 0
        self.log_path = log_path

    def start(self, experiment='sugar'):
        if experiment not in ('sugar', 'p9'):
            raise ValueError('Experimento deve ser sugar ou p9.')
        with self.lock:
            if self.adapter and (self.experiment != experiment or self.adapter.error):
                self.adapter.close()
                self.adapter = None
                self.frame = None
                self.sequence = 0
            if self.adapter is None:
                self.experiment = experiment
                self.adapter = self.factory(experiment, 20)
            return self._status()

    def _poll(self):
        if self.adapter:
            frame = self.adapter.poll()
            if frame is not None:
                duration = frame.end_ms - frame.start_ms
                command = self.decoder.decode(frame.spikes, duration)
                counts = [int((frame.spikes.flywire_id == n).sum()) for n in self.decoder.ids]
                self.sequence += 1
                self.frame = dict(sequence=self.sequence, start_ms=frame.start_ms,
                    end_ms=frame.end_ms, processing_s=frame.processing_s,
                    population=frame.population, spikes=len(frame.spikes), active=frame.active,
                    stimulus=frame.stimulus, stimulus_world_s=frame.stimulus_world_s,
                    p9_ids=[str(n) for n in self.decoder.ids], p9_counts=counts,
                    p9_hz=sum(counts)/len(counts)/(duration/1000) if duration else 0,
                    command=[command.forward_drive, 0], experiment=self.experiment,
                    controller='Brian2 -> experimental P9 rate decoder',
                    realtime_factor=frame.realtime_factor)
                if self.log_path:
                    path = Path(self.log_path)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    with path.open('a', encoding='utf-8') as stream:
                        stream.write(json.dumps(self.frame, allow_nan=False)+'\n')

    def _status(self):
        adapter = self.adapter
        return dict(state='stopped' if adapter is None else 'error' if adapter.error else
                    'pending' if adapter.pending else 'ready' if adapter.ready else 'loading',
                    error=adapter.error if adapter else '',
                    population=adapter.population if adapter else 0,
                    experiment=self.experiment, frame_available=self.frame is not None,
                    setup_s=adapter.setup_s if adapter else 0,
                    block_ms=20, plasticity=False, turning_validated=False)

    def status(self, consume=False):
        with self.lock:
            self._poll()
            result = self._status()
            if consume and self.frame is not None:
                result['frame'] = self.frame
                self.frame = None
            return result

    def step(self, food, world_s, calibration=0):
        values = (food, world_s, calibration)
        if any(isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) for v in values):
            raise ValueError('Sensores e tempo devem ser números finitos.')
        if not 0 <= food <= 1 or not 0 <= calibration <= 1 or world_s < 0:
            raise ValueError('Intensidades entre 0 e 1; tempo não negativo.')
        with self.lock:
            self._poll()
            if not self.adapter or not self.adapter.ready or self.adapter.error:
                return self._status()
            # Never overwrite an unconsumed block or enqueue a backlog.
            if not self.adapter.pending and self.frame is None:
                self.adapter.request(food if self.experiment == 'sugar' else calibration, world_s)
            return self._status()

    def close(self):
        with self.lock:
            if self.adapter:
                self.adapter.close()
                self.adapter = None


def handler_for(service, directory):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)

        def allowed(self):
            host = self.headers.get('Host', '')
            expected = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            origin = self.headers.get('Origin')
            return (host in expected and (not origin or origin == 'http://'+host)
                    and self.headers.get('Sec-Fetch-Site') != 'cross-site')

        def reply(self, value, status=200):
            body = json.dumps(value, allow_nan=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            try:
                self.end_headers()
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                # Switching browser mode can cancel an in-flight HTTP poll.
                # Its neural block remains owned by the service, not the socket.
                return

        def do_GET(self):
            if not self.allowed():
                return self.reply({'error': 'Origem local inválida.'}, 403)
            if self.path == '/api/neural/status':
                return self.reply(service.status())
            if self.path.startswith('/api/'):
                return self.reply({'error': 'Endpoint inexistente.'}, 404)
            return super().do_GET()

        def do_POST(self):
            if not self.allowed():
                return self.reply({'error': 'Origem local inválida.'}, 403)
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 4096 or self.headers.get_content_type() != 'application/json':
                    raise ValueError('Envie JSON de até 4096 bytes.')
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError('Objeto JSON obrigatório.')
                if self.path == '/api/neural/start':
                    result = service.start(data.get('experiment', 'sugar'))
                elif self.path == '/api/neural/step':
                    result = service.step(data.get('food'), data.get('world_s'), data.get('calibration', 0))
                elif self.path == '/api/neural/poll':
                    result = service.status(consume=True)
                else:
                    return self.reply({'error': 'Endpoint inexistente.'}, 404)
                return self.reply(result)
            except (ValueError, TypeError) as exc:
                return self.reply({'error': str(exc)}, 400)
            except Exception as exc:
                return self.reply({'error': f'{type(exc).__name__}: {exc}'}, 500)

        def log_message(self, fmt, *args):
            if not self.path.startswith('/api/'):
                super().log_message(fmt, *args)

    return Handler


def main():
    parser = argparse.ArgumentParser(description='Jardim 3D com cérebro Brian2 local')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    directory = ROOT/'web/dist'
    if not (directory/'index.html').exists():
        parser.error('Execute npm run build na pasta web antes de iniciar.')
    service = NeuralService(log_path=ROOT/'flyworld-output/neural-live/blocks.jsonl')
    server = ThreadingHTTPServer(('127.0.0.1', args.port), handler_for(service, directory))
    print(f'FlyWorld neural: http://127.0.0.1:{server.server_port}', flush=True)
    print('Rede completa carregada ao conectar. Ctrl+C encerra serviço e cérebro.', flush=True)
    if not args.no_browser:
        webbrowser.open(f'http://127.0.0.1:{server.server_port}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        service.close()


if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    main()
