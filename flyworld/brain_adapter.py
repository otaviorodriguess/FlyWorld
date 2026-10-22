"""Spike sources. Replay never feeds virtual stimuli back into recorded data."""
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
import multiprocessing as mp
from queue import Empty
import numpy as np
import pandas as pd

COLUMNS = ['time_ms', 'trial', 'neuron_index', 'flywire_id', 'exp_name']

def empty_spikes() -> pd.DataFrame:
    return pd.DataFrame({k: pd.Series(dtype='str' if k == 'exp_name' else ('float64' if k == 'time_ms' else 'int64')) for k in COLUMNS})

@dataclass
class NeuralFrame:
    start_ms: float = 0
    end_ms: float = 0
    spikes: pd.DataFrame = field(default_factory=empty_spikes)
    processing_s: float = 0
    population: int = 0
    experiment: str = ''
    stimulus: float | None = None
    stimulus_world_s: float | None = None

    @property
    def active(self) -> int:
        return self.spikes.flywire_id.nunique()

    @property
    def mean_hz(self) -> float:
        """Population mean, not mean among only neurons that fired."""
        duration = (self.end_ms-self.start_ms)/1000
        return len(self.spikes)/duration/self.population if duration > 0 and self.population else 0

    @property
    def realtime_factor(self) -> float:
        return (self.end_ms-self.start_ms)/1000/self.processing_s if self.processing_s else 0

class ReplayAdapter:
    def __init__(self, path: str | Path, trial: int = 0, exp_name: str | None = None,
                 population: int = 0, duration_ms: float | None = None, trial_count: int | None = None):
        start = perf_counter()
        if trial_count is not None and not 0<=trial<trial_count:
            raise ValueError(f'Trial {trial} fora do intervalo 0..{trial_count-1}.')
        df = pd.read_parquet(path,filters=[('trial','=',trial)]) if trial_count is not None else pd.read_parquet(path)
        if 'time_ms' not in df and 't' in df:
            df['time_ms'] = df['t'] * 1000  # upstream legacy seconds
        missing = set(COLUMNS)-set(df.columns)
        if missing:
            raise ValueError(f'Parquet sem campos obrigatórios: {sorted(missing)}')
        if not np.isfinite(df.time_ms.to_numpy(dtype=float)).all() or (df.time_ms < 0).any():
            raise ValueError('Spikes precisam de tempos finitos e não negativos.')
        for column in ['trial', 'neuron_index', 'flywire_id']:
            if not df.empty and (df[column].isna().any() or df[column].dtype.kind not in 'iu'):
                raise ValueError(f'{column} deve ser inteiro (IDs não podem passar por float).')
        if not df.empty and trial not in df.trial.unique():
            raise ValueError(f'Trial {trial} ausente. Disponíveis: {sorted(df.trial.unique())}')
        df = df[df.trial == trial]
        names = df.exp_name.dropna().unique()
        if exp_name is None and len(names) > 1:
            raise ValueError('Arquivo contém vários experimentos. Use --replay-exp.')
        if exp_name is not None:
            df = df[df.exp_name == exp_name]
            if df.empty:
                raise ValueError(f'Experimento ausente no replay: {exp_name}')
        if df.empty:
            df = empty_spikes()
        self.data = df[COLUMNS].sort_values('time_ms', kind='stable').reset_index(drop=True)
        self.times = self.data.time_ms.to_numpy()
        self.population = population
        self.name = str(exp_name or (names[0] if len(names) else 'vazio'))
        last = float(self.times[-1]) if len(self.times) else 0
        sidecar = Path(path).with_suffix('.json')
        if duration_ms is None and sidecar.exists():
            import json
            duration_ms = json.loads(sidecar.read_text(encoding='utf-8')).get('duration_ms')
        if duration_ms is not None and (not np.isfinite(duration_ms) or duration_ms < last):
            raise ValueError('--duration-ms não pode preceder o último spike.')
        self.duration_ms = duration_ms or last + .1
        self.load_s = perf_counter()-start
        self.reset()

    def reset(self):
        self.cursor = 0
        self.time_ms = 0.

    def advance(self, dt_ms: float) -> NeuralFrame:
        if not np.isfinite(dt_ms) or dt_ms <= 0:
            raise ValueError('Intervalo do replay deve ser positivo e finito.')
        start = perf_counter()
        end = min(self.time_ms+dt_ms, self.duration_ms)
        i = int(np.searchsorted(self.times, end, side='right' if end>=self.duration_ms else 'left'))
        frame = NeuralFrame(self.time_ms, end, self.data.iloc[self.cursor:i].copy(),
                            perf_counter()-start, self.population, self.name)
        self.cursor, self.time_ms = i, end
        return frame

    @property
    def finished(self):
        return self.time_ms >= self.duration_ms

    def close(self):
        pass


def _live_worker(inbox, outbox, experiment, block_ms, comp_path, con_path):
    try:
        from .live_backend import BrianRuntime
        brain = BrianRuntime(experiment, comp_path, con_path)
        outbox.put(('ready', {'population': brain.population, 'setup_s': brain.setup_s}))
        while True:
            request = inbox.get()
            if request is None:
                break
            frame=brain.advance(block_ms,request['intensity'] if isinstance(request,dict) else request)
            frame.stimulus_world_s=request.get('world_s') if isinstance(request,dict) else None
            outbox.put(('frame',frame))
    except Exception as exc:
        outbox.put(('error', f'{type(exc).__name__}: {exc}'))

class LiveAdapter:
    """One request in flight; bounded queues and no render-thread simulation."""
    def __init__(self, experiment='sugar', block_ms=20, comp_path=None, con_path=None):
        from .config import ROOT
        self.context = mp.get_context('spawn')
        self.inbox = self.context.Queue(maxsize=1)
        self.outbox = self.context.Queue(maxsize=2)
        self.ready = self.pending = False
        self.error = ''
        self.population = 0
        self.setup_s = 0
        self.process = self.context.Process(target=_live_worker, args=(self.inbox, self.outbox,
            experiment, block_ms, str(comp_path or ROOT/'data/2025_Completeness_783.csv'),
            str(con_path or ROOT/'data/2025_Connectivity_783.parquet')), daemon=True)
        self.process.start()
        self.closed = False

    def poll(self) -> NeuralFrame | None:
        frame = None
        while True:
            try:
                kind, data = self.outbox.get_nowait()
            except Empty:
                break
            if kind == 'ready':
                self.ready = True
                self.population = data['population']
                self.setup_s = data['setup_s']
            elif kind == 'error':
                self.error, self.pending = data, False
            elif kind == 'frame':
                frame, self.pending = data, False
        if not self.process.is_alive() and not self.error and not self.closed:
            self.error = f'Processo neural encerrado (código {self.process.exitcode}).'
        return frame

    def request(self, intensity: float, world_s: float | None = None):
        if self.ready and not self.pending and not self.error:
            self.inbox.put_nowait({'intensity':float(np.clip(intensity,0,1)),'world_s':world_s})
            self.pending = True

    def close(self):
        if self.closed:
            return
        self.closed = True
        # A running block may take minutes; give cooperative shutdown a bounded wait.
        try:
            self.inbox.put_nowait(None)
        except Exception:
            pass
        self.process.join(timeout=1)
        if self.process.is_alive():
            self.process.terminate()
            self.process.join(timeout=3)
        for queue in (self.inbox, self.outbox):
            queue.cancel_join_thread()
            queue.close()
