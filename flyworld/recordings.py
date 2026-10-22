"""Indexed, selective access to the upstream neural recording ZIP.

Metadata and filenames are data only. No archive code is executed and extractall
is never used. Only an explicitly selected Parquet is copied and verified.
"""
from dataclasses import dataclass, asdict
from pathlib import Path, PurePosixPath
import hashlib
import io
import json
import math
import re
import zipfile
import uuid
import numpy as np
import pandas as pd
from .config import ROOT

SETTINGS=ROOT/'flyworld-output/archive-settings.json'
BACKENDS={'brian2cpp':'Brian2 CPU','brian2cuda':'Brian2 CUDA','pytorch':'PyTorch',
          'nestgpu':'NEST GPU','genn':'GeNN','brian2genn':'Brian2GeNN'}

@dataclass(frozen=True)
class Recording:
    member: str
    backend: str
    experiment: str
    duration_s: float
    trials: int
    round: int
    spikes: int
    active: int
    size_bytes: int
    sha256: str

    @property
    def label(self):
        return f'{BACKENDS.get(self.backend,self.backend)} | R{self.round} | {self.duration_s:g}s | {self.trials} trial(s)'

class NeuralArchive:
    def __init__(self,path,cache=None,max_mb=64):
        self.path=Path(path).resolve()
        if not math.isfinite(max_mb) or max_mb<=0:
            raise ValueError('Limite de importação deve ser positivo e finito.')
        self.max_bytes=int(max_mb*1024*1024)
        if self.max_bytes<=0:
            raise ValueError('Limite de importação deve ser positivo.')
        try:
            with zipfile.ZipFile(self.path) as archive:
                names=archive.namelist()
                manifests=[name for name in names if name.endswith('/manifest.csv')]
                if len(manifests)!=1:
                    raise ValueError('O ZIP precisa de um manifesto único.')
                manifest_name=manifests[0]
                self.prefix=manifest_name.removesuffix('manifest.csv')
                if '..' in PurePosixPath(self.prefix).parts or self.prefix.startswith('/') or '\\' in self.prefix:
                    raise ValueError('Raiz de arquivo ZIP inválida.')
                for name in [manifest_name,self.prefix+'checksums.sha256']:
                    if archive.getinfo(name).file_size>4*1024*1024:
                        raise ValueError('Metadados excedem o limite de 4 MB.')
                manifest_raw=archive.read(manifest_name)
                checksum_raw=archive.read(self.prefix+'checksums.sha256')
                manifest=pd.read_csv(io.BytesIO(manifest_raw))
                checks={}
                for line in checksum_raw.decode('utf-8').splitlines():
                    parts=line.split(maxsplit=1)
                    if len(parts)==2 and re.fullmatch('[a-fA-F0-9]{64}',parts[0]):
                        checks[parts[1].lstrip('*')]=parts[0].lower()
                required={'backend_key','experiment_key','t_run','n_run','round','spike_path','spikes','active_neurons','status'}
                if required-set(manifest.columns):
                    raise ValueError('Manifesto incompleto.')
                self.records=[]
                seen=set()
                for row in manifest.to_dict('records'):
                    if row['status']!='success':
                        continue
                    backend=str(row['backend_key'])
                    duration=float(row['t_run'])
                    trials,round_index=int(row['n_run']),int(row['round'])
                    if backend not in BACKENDS or not math.isfinite(duration) or duration<=0 or trials<=0 or round_index<=0:
                        raise ValueError('Condição inválida no manifesto.')
                    filename=PurePosixPath(str(row['spike_path']).replace('\\','/')).name
                    match=re.fullmatch(r'([a-z0-9]+)_t([0-9]+(?:\.[0-9]+)?)s_n([0-9]+)\.parquet',filename)
                    if not match or match[1]!=backend or float(match[2])!=duration or int(match[3])!=trials:
                        raise ValueError(f'Nome Parquet incompatível com o manifesto: {filename}')
                    member=f'round_{round_index:02d}/{filename}'
                    if member in seen:
                        raise ValueError('Entrada duplicada no manifesto.')
                    seen.add(member)
                    full=self.prefix+member
                    if names.count(full)!=1 or member not in checks:
                        raise ValueError(f'Arquivo ou checksum ausente/ambíguo: {member}')
                    info=archive.getinfo(full)
                    self.records.append(Recording(member,backend,str(row['experiment_key']),duration,trials,round_index,
                        int(row['spikes']),int(row['active_neurons']),info.file_size,checks[member]))
                self.records.sort(key=lambda r:(r.duration_s,r.trials,r.round,list(BACKENDS).index(r.backend)))
                stat=self.path.stat()
                token=hashlib.sha256(manifest_raw+checksum_raw+str((stat.st_size,stat.st_mtime_ns)).encode()).hexdigest()[:16]
                self.cache=Path(cache or ROOT/'flyworld-output/recordings-cache')/token
                self.identity=(stat.st_size,stat.st_mtime_ns)
        except zipfile.BadZipFile as exc:
            raise ValueError('ZIP inválido ou incompleto.') from exc
        except (KeyError,UnicodeDecodeError,pd.errors.ParserError) as exc:
            raise ValueError('Metadados ZIP inválidos ou ausentes.') from exc

    def register(self,path=SETTINGS):
        path=Path(path)
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps({'archive':str(self.path)},indent=2,ensure_ascii=False),encoding='utf-8')

    def find(self,member):
        member=member.removeprefix(self.prefix)
        for recording in self.records:
            if recording.member==member:
                return recording
        raise ValueError('Gravação não encontrada no catálogo.')

    def condition(self,duration_s=1,trials=1,round_index=1):
        return [r for r in self.records if r.duration_s==duration_s and r.trials==trials and r.round==round_index]

    def prepare(self,recording,stop=None):
        if recording not in self.records:
            raise ValueError('Gravação não pertence a este catálogo.')
        if recording.size_bytes>self.max_bytes:
            raise ValueError(f'Arquivo tem {recording.size_bytes/1024**2:.1f} MB; limite atual {self.max_bytes/1024**2:g} MB. Escolha uma gravação menor ou ajuste --max-recording-mb.')
        stat=self.path.stat()
        if (stat.st_size,stat.st_mtime_ns)!=self.identity:
            raise ValueError('ZIP foi alterado; reabra a biblioteca.')
        target=self.cache/recording.member
        target.parent.mkdir(parents=True,exist_ok=True)
        def digest(path):
            value=hashlib.sha256()
            with path.open('rb') as stream:
                for chunk in iter(lambda:stream.read(1024*1024),b''):
                    if stop and stop.is_set():
                        raise ValueError('Importação cancelada.')
                    value.update(chunk)
            return value.hexdigest()
        if not target.exists() or digest(target)!=recording.sha256:
            temporary=target.with_name(target.name+'.'+uuid.uuid4().hex+'.part')
            try:
                value=hashlib.sha256()
                total=0
                with zipfile.ZipFile(self.path) as archive,archive.open(self.prefix+recording.member) as source,temporary.open('wb') as destination:
                    while True:
                        if stop and stop.is_set():
                            raise ValueError('Importação cancelada.')
                        chunk=source.read(1024*1024)
                        if not chunk:break
                        total+=len(chunk)
                        if total>self.max_bytes:
                            raise ValueError('Arquivo ultrapassou o limite de importação.')
                        value.update(chunk)
                        destination.write(chunk)
                if value.hexdigest()!=recording.sha256:
                    raise ValueError('SHA-256 divergente: gravação não será usada.')
                temporary.replace(target)
            finally:
                if temporary.exists():temporary.unlink()
        metadata={**asdict(recording),'duration_ms':recording.duration_s*1000,'archive':str(self.path),
                  'source':'recorded fly-brain activity','checksum_verified':True}
        target.with_suffix('.json').write_text(json.dumps(metadata,indent=2,ensure_ascii=False),encoding='utf-8')
        return target

    def replay(self,recording,trial=0,population=0,stop=None):
        from .brain_adapter import ReplayAdapter
        path=self.prepare(recording,stop)
        return ReplayAdapter(path,trial=trial,population=population,duration_ms=recording.duration_s*1000,trial_count=recording.trials)

    def compare(self,duration_s=1,trials=1,round_index=1,trial=0,population=138639,stop=None):
        records=self.condition(duration_s,trials,round_index)
        if len({r.experiment for r in records})>1:
            raise ValueError('Experimentos diferentes não podem ser comparados nesta condição.')
        if not any(r.backend=='brian2cpp' for r in records):
            raise ValueError('Brian2 CPU ausente nesta condição.')
        cpu_record=next(r for r in records if r.backend=='brian2cpp')
        cpu=self.replay(cpu_record,trial,population,stop)
        reference=cpu.data.groupby('flywire_id').size()
        ref_ids=set(reference.index)
        bins=np.linspace(0,duration_s*1000,51)
        ref_bins=np.histogram(cpu.data.time_ms,bins=bins)[0]
        rows=[]
        for record in records:
            adapter=cpu if record.backend=='brian2cpp' else self.replay(record,trial,population,stop)
            rates=adapter.data.groupby('flywire_id').size()
            ids=set(rates.index)
            union=ref_ids|ids
            aligned=pd.concat([reference.rename('cpu'),rates.rename('other')],axis=1).fillna(0)
            correlation=float(aligned.corr().iloc[0,1]) if len(aligned)>1 and aligned.cpu.std()>0 and aligned.other.std()>0 else None
            hist=np.histogram(adapter.data.time_ms,bins=bins)[0]
            temporal=float(np.corrcoef(ref_bins,hist)[0,1]) if np.std(ref_bins)>0 and np.std(hist)>0 else None
            rows.append({'backend':record.backend,'spikes':len(adapter.data),'active':len(ids),
                'mean_population_hz':len(adapter.data)/duration_s/population if population else None,
                'active_jaccard_cpu':len(ref_ids&ids)/len(union) if union else 1.,
                'rate_correlation_cpu':correlation,'population_bin_correlation_cpu':temporal,
                'verified_sha256':record.sha256})
        return {'experiment':records[0].experiment,'duration_s':duration_s,'n_trials_in_file':trials,
                'selected_trial':trial,'round':round_index,'population':population,'reference':'brian2cpp',
                'limitation':'Descriptive comparison of recordings; no validated motor decoding or live responsiveness.',
                'rows':rows}


def registered_archive():
    if not SETTINGS.exists():return None
    try:
        return Path(json.loads(SETTINGS.read_text(encoding='utf-8'))['archive'])
    except (ValueError,KeyError,TypeError):
        return None


def main():
    import argparse
    parser=argparse.ArgumentParser(description='Catálogo e comparação de gravações reais fly-brain')
    parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--register',action='store_true')
    parser.add_argument('--compare',action='store_true')
    parser.add_argument('--duration',type=float,default=1.)
    parser.add_argument('--trials',type=int,default=1)
    parser.add_argument('--round',type=int,default=1)
    parser.add_argument('--trial',type=int,default=0)
    parser.add_argument('--report',type=Path)
    parser.add_argument('--max-recording-mb',type=float,default=64)
    args=parser.parse_args()
    try:
        archive=NeuralArchive(args.archive,max_mb=args.max_recording_mb)
        if args.register:archive.register()
        report={'archive':str(archive.path),'recordings':len(archive.records),
            'experiments':sorted({r.experiment for r in archive.records}),
            'backends':sorted({r.backend for r in archive.records}),
            'durations_s':sorted({r.duration_s for r in archive.records}),
            'trial_counts':sorted({r.trials for r in archive.records})}
        if args.compare:report['comparison']=archive.compare(args.duration,args.trials,args.round,args.trial)
        if args.report:
            args.report.parent.mkdir(parents=True,exist_ok=True)
            args.report.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8')
        print(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False))
    except (ValueError,OSError,KeyError) as exc:
        parser.exit(2,f'Biblioteca neural: {exc}\n')

if __name__=='__main__':main()
