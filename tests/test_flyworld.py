import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
from pathlib import Path
import math
import time
import numpy as np
import pandas as pd
import pytest
from flyworld.config import Config, ROOT
from flyworld.world import World, Obstacle
from flyworld.fly_body import FlyBody, MotorCommand
from flyworld.sensors import sense
from flyworld.experiments import get_experiment
from flyworld.brain_adapter import ReplayAdapter, LiveAdapter
from flyworld.neural_decoder import NeuralDecoder

P9 = get_experiment('p9')['neu_exc']

@pytest.fixture
def spikes(tmp_path):
    path = tmp_path/'spikes.parquet'
    pd.DataFrame({'time_ms':[0.,10.,20.,40.,10.], 'trial':[0,0,0,0,1],
        'neuron_index':[0,1,0,1,0], 'flywire_id':[P9[0],P9[1],P9[0],P9[1],P9[0]],
        'exp_name':['p9']*5}).to_parquet(path)
    return path

def test_body_movement():
    body = FlyBody(angle=0)
    world = World(foods=[],obstacles=[])
    body.update(MotorCommand(1),.5,world,Config())
    assert body.x == pytest.approx(655)
    assert body.y == 400
    body.update(MotorCommand(1,stop_drive=1),.5,world,Config())
    assert body.x == pytest.approx(655)

def test_collision_and_tunnelling():
    body = FlyBody(x=50,y=50,angle=0)
    world = World(foods=[],obstacles=[Obstacle(100,0,10,100)])
    body.update(MotorCommand(1),5,world,Config())
    assert body.x < 100-body.radius
    assert body.state == 'colisão'
    assert world.blocked(1,1)
    assert not world.blocked(500,500)

def test_sensors_and_food_contact():
    body = FlyBody(x=100,y=100,angle=0)
    world = World(foods=[(210,100)],obstacles=[])
    sensors = sense(body,world)
    assert sensors['food_distance'] == 110
    assert sensors['food'] == .5
    assert sensors['bearing'] == 0
    assert world.collect(210,100)
    assert world.interactions == 1
    assert not world.collect(210,100)
    assert sense(body,world)['food'] == 0

def test_command_clamp_and_rotation():
    speed, turn = MotorCommand(2,turn_left_drive=3).velocities(Config())
    assert speed == 110
    assert turn == -2.8
    body = FlyBody(angle=0)
    body.update(MotorCommand(turn_right_drive=1),1,World(),Config())
    assert body.angle == pytest.approx(2.8)

def test_replay_windows_trials_and_reset(spikes):
    replay = ReplayAdapter(spikes, duration_ms=50)
    a = replay.advance(20)
    b = replay.advance(20)
    c = replay.advance(20)
    assert a.spikes.time_ms.tolist() == [0,10]
    assert b.spikes.time_ms.tolist() == [20]
    assert c.spikes.time_ms.tolist() == [40]
    assert replay.finished
    replay.reset()
    assert replay.advance(10).spikes.time_ms.tolist() == [0]
    assert ReplayAdapter(spikes,trial=1).advance(20).spikes.time_ms.tolist() == [10]
    with pytest.raises(ValueError):
        ReplayAdapter(spikes,trial=2)

def test_decoder_uses_only_p9(spikes):
    replay = ReplayAdapter(spikes)
    frame = replay.advance(20)
    assert NeuralDecoder().decode(frame.spikes,20).forward_drive == .5
    data = frame.spikes.copy()
    data['flywire_id'] = get_experiment('sugar')['neu_exc'][0]
    assert NeuralDecoder().decode(data,20).forward_drive == 0
    assert NeuralDecoder().decode(frame.spikes,0).forward_drive == 0

def test_parquet_validation_and_legacy(spikes,tmp_path):
    data = pd.read_parquet(spikes)
    data['t'] = data.time_ms/1000
    data = data.drop(columns='time_ms')
    legacy = tmp_path/'legacy.parquet'
    data.to_parquet(legacy)
    assert ReplayAdapter(legacy).advance(20).spikes.time_ms.tolist() == [0,10]
    data['time_ms'] = -1.
    data.to_parquet(legacy)
    with pytest.raises(ValueError,match='não negativos'):
        ReplayAdapter(legacy)
    data = data.drop(columns='flywire_id')
    data.to_parquet(legacy)
    with pytest.raises(ValueError,match='obrigatórios'):
        ReplayAdapter(legacy)

def test_experiments_are_upstream_and_ids_exist():
    ids = set(pd.read_csv(ROOT/'data/2025_Completeness_783.csv',index_col=0).index)
    sugar, p9 = get_experiment('sugar'), get_experiment('p9')
    assert len(sugar['neu_exc']) == 21 and sugar['stim_rate'] == 200
    assert len(p9['neu_exc']) == 2 and p9['stim_rate'] == 100
    assert set(sugar['neu_exc']+p9['neu_exc']) <= ids
    p9['neu_exc'].clear()
    assert len(get_experiment('p9')['neu_exc']) == 2

def test_application_lifecycle_and_export(tmp_path,spikes):
    import pygame
    from flyworld.__main__ import parser
    from flyworld.app import App
    args = parser().parse_args(['--mode','demo','--frames','3','--output',str(tmp_path), '--spikes',str(spikes)])
    app = App(args)
    app.update(.1)
    assert app.time > 0
    app.paused = True
    before = app.time
    app.update(.1)
    assert app.time == before
    app.paused = False
    app.reset('replay')
    app.update(.04)
    assert app.frame.end_ms == 40
    app.recorder.save()
    saved = pd.read_parquet(app.recorder.directory/'spikes.parquet')
    assert saved.flywire_id.tolist() == [P9[0],P9[1],P9[0]]
    app.run()
    assert app.closed and not pygame.display.get_init()
    app.close()

@pytest.fixture
def small_connectome(tmp_path):
    comp, con = tmp_path/'comp.csv', tmp_path/'con.parquet'
    pd.DataFrame({'Completed':[True]*2},index=P9).to_csv(comp)
    pd.DataFrame({'Presynaptic_Index':[0,1], 'Postsynaptic_Index':[1,0],
                  'Excitatory x Connectivity':[1,1]}).to_parquet(con)
    return comp,con

def test_brian_state_preserved_and_stimulus_effect(small_connectome):
    from flyworld.live_backend import BrianRuntime
    import brian2 as b
    comp,con = small_connectome
    brain = BrianRuntime('p9',comp,con)
    network = brain.net
    neu = network['default_neurons']
    neu.v[0] = -50*b.mV
    a = brain.advance(10,0)
    assert -52 < float(neu.v[0]/b.mV) < -50
    retained = float(neu.v[0]/b.mV)
    c = brain.advance(10,0)
    assert brain.net is network
    assert -52 < float(neu.v[0]/b.mV) < retained
    assert a.start_ms == 0 and c.start_ms == 10 and c.end_ms == 20
    active = brain.advance(300,1)
    assert len(active.spikes)>20
    assert set(active.spikes.flywire_id) <= set(P9)
    assert a.spikes.empty and c.spikes.empty

def test_worker_start_frame_and_clean_shutdown(small_connectome):
    comp,con = small_connectome
    adapter = LiveAdapter('p9',20,comp,con)
    deadline = time.monotonic()+30
    try:
        while not adapter.ready and not adapter.error and time.monotonic()<deadline:
            adapter.poll()
            time.sleep(.02)
        assert adapter.ready, adapter.error
        adapter.request(1)
        frame = None
        while frame is None and not adapter.error and time.monotonic()<deadline:
            frame = adapter.poll()
            time.sleep(.02)
        assert frame is not None, adapter.error
        assert frame.end_ms == 20
    finally:
        adapter.close()
    assert not adapter.process.is_alive()

def test_worker_reports_error_and_closes(tmp_path):
    adapter = LiveAdapter('p9',20,tmp_path/'missing.csv',tmp_path/'missing.parquet')
    deadline = time.monotonic()+30
    try:
        while not adapter.error and time.monotonic()<deadline:
            adapter.poll()
            time.sleep(.02)
        assert adapter.error
    finally:
        adapter.close()
    assert not adapter.process.is_alive()

def test_avoidance_preserves_stopped_neural_drive():
    from flyworld.controllers import avoid_obstacles
    command = avoid_obstacles(MotorCommand(), {'front':1.,'left':.2,'right':.9})
    assert command.forward_drive == 0
    assert command.turn_left_drive == 1


def test_empty_baseline_and_multiple_experiments(tmp_path,spikes):
    from flyworld.brain_adapter import empty_spikes
    path = tmp_path/'empty.parquet'
    empty_spikes().to_parquet(path)
    replay = ReplayAdapter(path,duration_ms=100)
    assert replay.advance(20).spikes.empty
    assert replay.name == 'vazio'
    data = pd.read_parquet(spikes)
    data.loc[0,'exp_name'] = 'sugar'
    data.to_parquet(path)
    with pytest.raises(ValueError,match='vários experimentos'):
        ReplayAdapter(path)
    assert len(ReplayAdapter(path,exp_name='sugar').advance(10).spikes) == 1


def test_ui_controls_and_demo_export(tmp_path):
    import pygame
    from flyworld.app import App
    from flyworld.__main__ import parser
    app = App(parser().parse_args(['--mode','demo','--output',str(tmp_path),'--frames','1','--view','2d']))
    try:
        app.dashboard.draw(app)
        old = len(app.world.foods)
        pos = app.dashboard.project(100,100)
        app.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=pos))
        assert len(app.world.foods) == old+1
        pos = app.dashboard.project(100,600)
        old = len(app.world.obstacles)
        for expected in [old+1,old]:
            app.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=3,pos=pos))
            assert len(app.world.obstacles) == expected
        app.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_h))
        assert app.dashboard.help
        app.dashboard.draw(app)
        app.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_m))
        assert app.manual
        app.recorder.append(app,app.frame)
        target = app.recorder.save()
        assert pd.read_parquet(target/'spikes.parquet').empty
    finally:
        app.close()

def test_3d_camera_ground_picking():
    from flyworld.scene3d import Camera3D
    import pygame
    camera=Camera3D()
    for yaw in (.2,1.3,3.8):
        camera.yaw=yaw
        camera.configure(pygame.Rect(20,80,1000,700),FlyBody())
        points=np.array([[600.,400.,0.],[630.,420.,0.],[550.,390.,0.]])
        screen,depth=camera.project(points)
        assert (depth>0).all()
        for expected,projected in zip(points,screen):
            result=camera.pick_ground(projected)
            assert result == pytest.approx(expected[:2],abs=1e-8)
    assert camera.pick_ground((-1,-1)) is None


def test_3d_scene_interactions_and_world_cache(tmp_path):
    import pygame
    from flyworld.app import App
    from flyworld.__main__ import parser
    app=App(parser().parse_args(['--mode','demo','--output',str(tmp_path),'--frames','1']))
    try:
        assert app.dashboard.view3d
        app.dashboard.draw(app)
        scene=app.dashboard.scene3d
        original=scene.world_mesh
        assert len(scene.transparent)==2
        app.dashboard.draw(app)
        assert scene.world_mesh is original
        point=app.dashboard.project(app.body.x+80,app.body.y)
        before=len(app.world.foods)
        app.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=point))
        assert len(app.world.foods)==before+1
        app.dashboard.draw(app)
        assert scene.world_mesh is not original
        before=scene.camera.yaw
        app.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_d))
        assert scene.camera.yaw>before
        app.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_c))
        assert not scene.camera.follow
        app.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_v))
        assert not app.dashboard.view3d
        # Renderer switches never change physical position or neural source.
        assert app.body.x==3000 and app.body.y==2000
        assert app.mode=='demo' and app.adapter is None
    finally:
        app.close()

def test_expanded_garden_and_water_collisions():
    world=World.garden()
    assert world.width*world.height == 25*1200*800
    assert not world.blocked(3000,2000,12)
    assert len(world.foods)>30 and len(world.obstacles)>30
    assert len(world.ponds)>=3
    px,py,rx,ry=world.ponds[0]
    assert world.blocked(px,py,12)
    assert world.blocked(px+rx-2,py,12)
    assert not world.blocked(world.width-50,world.height-50,12)


def test_interactions_are_artificial_and_mode_limited():
    from flyworld.interactions import InteractionState
    state=InteractionState()
    body=FlyBody()
    world=World(foods=[],obstacles=[])
    sensors=sense(body,world)
    state.start('pet',body,world,0)
    assert state.command(body,sensors,1,'demo').stop_drive==1
    assert state.command(body,sensors,1,'live') is None
    assert state.command(body,sensors,1,'replay') is None
    state.start('call',body,world,0,(body.x+100,body.y))
    body.angle=0
    command=state.command(body,sensors,1,'demo')
    assert command.forward_drive>0
    assert state.command(body,sensors,25,'demo') is None
    assert state.action=='explore'
    before=len(world.foods)
    state.start('feed',body,world,26)
    assert len(world.foods)==before+1
    state.start('play',body,world,27,(700,500))
    assert state.command(body,sensors,28,'demo') is not None
    state.start('explore',body,world,28)
    assert state.target is None


def test_interaction_buttons_map_and_event_log(tmp_path):
    import pygame,json
    from flyworld.app import App
    from flyworld.__main__ import parser
    app=App(parser().parse_args(['--mode','demo','--output',str(tmp_path),'--frames','1']))
    try:
        app.dashboard.draw(app)
        before=len(app.world.foods)
        button=app.dashboard.interaction_buttons['feed']
        app.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=button.center))
        assert len(app.world.foods)==before+1
        assert app.interaction.action=='feed'
        button=app.dashboard.interaction_buttons['pet']
        app.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=button.center))
        app.physics(.1)
        assert app.body.speed==0
        assert app.interaction.action=='pet'
        target=app.dashboard.minimap_rect.center
        app.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=3,pos=target))
        assert app.dashboard.scene3d.camera.focus==pytest.approx((3000,2000))
        assert not app.dashboard.scene3d.camera.follow
        app.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=target))
        assert app.interaction.selected=='call'
        records=[json.loads(line) for line in (app.recorder.directory/'interactions.jsonl').read_text(encoding='utf-8').splitlines()]
        assert [record['action'] for record in records][:2]==['feed','pet']
        assert all(record['controller']=='artificial demo-only' for record in records)
    finally:
        app.close()

def test_garden_collision_index_matches_geometry():
    world=World.garden()
    rng=np.random.default_rng(8)
    for x,y in rng.uniform([0,0],[world.width,world.height],(120,2)):
        radius=24
        expected=(x<radius or y<radius or x>world.width-radius or y>world.height-radius
            or any(o.distance(x,y)<radius for o in world.obstacles)
            or any(((x-px)/(rx+radius))**2+((y-py)/(ry+radius))**2<1 for px,py,rx,ry in world.ponds))
        assert world.blocked(x,y,radius)==expected
    body=FlyBody(x=3000,y=2000)
    assert not world.blocked(3000,2100,12)
    world.edit_obstacle(3000,2100,body)
    assert world.blocked(3000,2100,12)
    world.edit_obstacle(3000,2100,body)
    assert not world.blocked(3000,2100,12)
