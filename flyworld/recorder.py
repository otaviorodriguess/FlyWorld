"""Disk-backed experiment logging; demo never writes invented spikes."""
import csv
from datetime import datetime
from pathlib import Path
import json
import pandas as pd
from .brain_adapter import COLUMNS

class Recorder:
    def __init__(self, directory: Path, metadata: dict):
        self.directory = directory / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        self.directory.mkdir(parents=True)
        (self.directory/'metadata.json').write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding='utf-8')
        self.telemetry = (self.directory/'telemetry.csv').open('w', newline='', encoding='utf-8')
        self.spikes = (self.directory/'spikes.csv').open('w', newline='', encoding='utf-8')
        self.writer = csv.writer(self.telemetry)
        self.writer.writerow(['world_s', 'neural_ms', 'mode', 'controller', 'x', 'y', 'speed', 'food', 'front', 'stimulus', 'spikes', 'active', 'mean_population_hz', 'processing_s', 'interaction_action','q_updates','q_reward','stimulus_world_s','event_kind'])
        self.spike_writer = csv.writer(self.spikes)
        self.spike_writer.writerow(COLUMNS)
        self.events=(self.directory/'interactions.jsonl').open('w',encoding='utf-8')
        self.closed = False
        self.neural_end_ms = 0.

    def append(self, app, frame, include_spikes=True):
        self.neural_end_ms = max(self.neural_end_ms, frame.end_ms)
        self.writer.writerow([app.time, frame.end_ms, app.mode, 'manual' if app.manual else ('artificial_Q_learning' if app.mode=='autonomous' else ('heuristic' if app.mode == 'demo' else 'experimental_P9_plus_heuristic_collision')),
            app.body.x, app.body.y, app.body.speed, app.body.sensors.get('food', 0), app.body.sensors.get('front', 0),
            frame.stimulus, len(frame.spikes) if include_spikes else 0, frame.active, frame.mean_hz, frame.processing_s, app.interaction.action,app.learner.steps,app.learner.last_reward,frame.stimulus_world_s,'neural_block' if include_spikes and app.mode!='demo' else 'world_tick'])
        if include_spikes and app.mode != 'demo' and not frame.spikes.empty:
            self.spike_writer.writerows(frame.spikes[COLUMNS].itertuples(index=False, name=None))

    def record_interaction(self,app,action,point):
        self.events.write(json.dumps({'world_s':app.time,'mode':app.mode,'action':action,
            'target':point,'controller':'artificial interaction; Q suspended' if app.mode=='autonomous' else 'artificial demo-only'},ensure_ascii=False)+'\n')
        self.events.flush()

    def save(self) -> Path:
        import pyarrow as pa
        import pyarrow.parquet as pq
        self.telemetry.flush()
        self.spikes.flush()
        target = self.directory/'spikes.parquet'
        schema = pa.schema([('time_ms', pa.float64()), ('trial', pa.int64()), ('neuron_index', pa.int64()), ('flywire_id', pa.int64()), ('exp_name', pa.string())])
        # Bounded-memory export, including a valid empty parquet in demo.
        with pq.ParquetWriter(target, schema) as writer:
            for chunk in pd.read_csv(self.directory/'spikes.csv', chunksize=100000,
                dtype={'time_ms':'float64', 'trial':'int64', 'neuron_index':'int64', 'flywire_id':'int64', 'exp_name':'str'}):
                writer.write_table(pa.Table.from_pandas(chunk, schema=schema, preserve_index=False))
        if self.neural_end_ms > 0:
            target.with_suffix('.json').write_text(json.dumps({'duration_ms':self.neural_end_ms,
                'source':'FlyWorld session export; see metadata.json and telemetry.csv'}),encoding='utf-8')
        return self.directory

    def close(self):
        if not self.closed:
            self.telemetry.close()
            self.spikes.close()
            self.events.close()
            self.closed = True
