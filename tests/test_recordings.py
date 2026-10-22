"""Technical archive fixtures; synthetic rows are not biological recordings."""
import hashlib
import io
import json
import time
import zipfile
import pandas as pd
import pytest
from flyworld.recordings import NeuralArchive, BACKENDS
from flyworld.library import NeuralLibrary
from flyworld.brain_adapter import ReplayAdapter

@pytest.fixture
def bundle(tmp_path):
    path=tmp_path/'bundle.zip'
    rows=[]
    checks=[]
    payloads={}
    for i,backend in enumerate(BACKENDS):
        frame=pd.DataFrame({'time_ms':[0.,20.,100.,10.], 'trial':[0,0,0,1],
            'neuron_index':[0,1,0,0],'flywire_id':[100,200,100,100],'exp_name':[backend]*4})
        buffer=io.BytesIO();frame.to_parquet(buffer,index=False)
        member=f'round_01/{backend}_t0.1s_n2.parquet'
        raw=buffer.getvalue()
        payloads[member]=raw
        checks.append(hashlib.sha256(raw).hexdigest()+'  '+member)
        rows.append({'backend_key':backend,'experiment_key':'sugar','t_run':.1,'n_run':2,'round':1,
            'spike_path':'/upstream/data/nature_test/'+member,'spikes':4,'active_neurons':2,'status':'success'})
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('nature_test/manifest.csv',pd.DataFrame(rows).to_csv(index=False))
        archive.writestr('nature_test/checksums.sha256','\n'.join(checks))
        for member,raw in payloads.items():archive.writestr('nature_test/'+member,raw)
    return path


def test_catalog_selective_import_cache_and_metadata(bundle,tmp_path):
    archive=NeuralArchive(bundle,cache=tmp_path/'cache')
    assert len(archive.records)==6
    record=archive.records[0]
    target=archive.prepare(record)
    assert len(list(archive.cache.rglob('*.parquet')))==1
    assert hashlib.sha256(target.read_bytes()).hexdigest()==record.sha256
    metadata=json.loads(target.with_suffix('.json').read_text(encoding='utf-8'))
    assert metadata['duration_ms']==100 and metadata['checksum_verified']
    target.write_bytes(b'corrupt cache')
    assert hashlib.sha256(archive.prepare(record).read_bytes()).hexdigest()==record.sha256
    registration=tmp_path/'settings.json'
    archive.register(registration)
    assert json.loads(registration.read_text(encoding='utf-8'))['archive']==str(bundle.resolve())


def test_archive_trial_filter_and_closed_final_boundary(bundle,tmp_path):
    archive=NeuralArchive(bundle,cache=tmp_path/'cache')
    adapter=archive.replay(archive.records[0],0,1000)
    first=adapter.advance(20)
    assert first.spikes.time_ms.tolist()==[0]
    assert adapter.advance(80).spikes.time_ms.tolist()==[20,100]
    assert adapter.advance(20).spikes.empty
    assert adapter.finished
    assert archive.replay(archive.records[0],1).data.time_ms.tolist()==[10]
    with pytest.raises(ValueError,match='intervalo'):
        archive.replay(archive.records[0],2)


def test_archive_comparison_matches_condition_and_cpu(bundle,tmp_path):
    archive=NeuralArchive(bundle,cache=tmp_path/'cache')
    report=archive.compare(.1,2,1,0,population=1000)
    assert len(report['rows'])==6
    assert all(row['spikes']==3 for row in report['rows'])
    assert all(row['active_jaccard_cpu']==1 for row in report['rows'])
    assert all(row['mean_population_hz']==pytest.approx(.03) for row in report['rows'])
    with pytest.raises(ValueError,match='ausente'):
        archive.compare(1,2,1)


def test_import_limits_and_checksum_rejection(bundle,tmp_path):
    small=NeuralArchive(bundle,cache=tmp_path/'small',max_mb=.00001)
    with pytest.raises(ValueError,match='limite'):
        small.prepare(small.records[0])
    archive=NeuralArchive(bundle,cache=tmp_path/'cache')
    from dataclasses import replace
    record=replace(archive.records[0],sha256='0'*64)
    archive.records[0]=record
    with pytest.raises(ValueError,match='SHA-256 divergente'):
        archive.prepare(record)
    assert not list(archive.cache.rglob('*.parquet'))
    assert not list(archive.cache.rglob('*.part'))


def test_manifest_cannot_extract_arbitrary_paths(tmp_path):
    path=tmp_path/'unsafe.zip'
    row={'backend_key':'brian2cpp','experiment_key':'sugar','t_run':.1,'n_run':1,'round':1,
         'spike_path':'../../evil.py','spikes':1,'active_neurons':1,'status':'success'}
    with zipfile.ZipFile(path,'w') as archive:
        archive.writestr('bundle/manifest.csv',pd.DataFrame([row]).to_csv(index=False))
        archive.writestr('bundle/checksums.sha256','0'*64+'  ../../evil.py')
    with pytest.raises(ValueError,match='incompatível'):
        NeuralArchive(path,cache=tmp_path/'cache')
    assert not (tmp_path/'evil.py').exists()


def test_background_browser_loading_and_comparison(bundle,tmp_path):
    archive=NeuralArchive(bundle,cache=tmp_path/'cache')
    browser=NeuralLibrary(archive,1000)
    browser.single_trial=False
    try:
        browser.submit('load')
        deadline=time.monotonic()+10
        result=None
        while result is None and time.monotonic()<deadline:
            result=browser.poll();time.sleep(.01)
        assert result[0]=='load'
        adapter,record,trial=result[1]
        assert len(adapter.data)==3 and trial==0
        assert len(adapter.raster[0])<=5000
        browser.submit('compare')
        result=None
        while result is None and time.monotonic()<deadline:
            result=browser.poll();time.sleep(.01)
        assert result[0]=='compare'
        assert len(browser.report['rows'])==6
        assert browser.report['selected_trial']==0
        assert (archive.cache/'comparison_r1_t0.1_n2_trial0.json').exists()
    finally:browser.close()
    assert browser.closed

def test_application_imports_recording_without_replacing_neural_with_heuristics(bundle,tmp_path,monkeypatch):
    import os,pygame
    os.environ['SDL_VIDEODRIVER']='dummy'
    from flyworld.app import App
    from flyworld.__main__ import parser
    monkeypatch.setattr(NeuralArchive,'register',lambda self:None)
    args=parser().parse_args(['--mode','demo','--archive',str(bundle),'--library','--headless','--output',str(tmp_path/'session')])
    app=App(args)
    try:
        before=app.time
        app.update(.1)
        assert app.time==before
        app.library.single_trial=False
        app.library.submit('load')
        deadline=time.monotonic()+10
        while app.library.future and time.monotonic()<deadline:
            app.poll_library();time.sleep(.01)
        assert app.mode=='replay'
        assert app.archive_record is not None
        assert app.speed==.1 and app.dashboard.show_neural
        assert not app.library.opened
        assert app.adapter.data.trial.unique().tolist()==[0]
        app.interact('pet')
        app.update(.1)
        assert app.body.speed==0  # Fixture has no P9; no motor claim from arbitrary spikes.
        app.dashboard.draw(app)
        assert not app.library.error
        metadata=json.loads((app.recorder.directory/'metadata.json').read_text(encoding='utf-8'))
        assert metadata['verified_sha256']==app.archive_record.sha256
    finally:app.close()
