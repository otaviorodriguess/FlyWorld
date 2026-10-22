"""Tests of artificial learning; none assert biological learning or sentience."""
import math
import json
import pandas as pd
import pytest
from flyworld.learning import LearningAgent,rollout
from flyworld.fly_body import FlyBody
from flyworld.world import World
from flyworld.sensors import sense


def test_reward_changes_action_values_and_memory_persists(tmp_path):
    path=tmp_path/'memory.json'
    agent=LearningAgent(path)
    state='4:1:0:0:0:1'
    assert agent.values(state)[0]>agent.values(state)[2]
    for _ in range(8):agent.update_value(state,2,3,state,terminal=True)
    assert agent.values(state)[2]>agent.values(state)[0]
    agent.visits={'2,3':4};agent.food_memory={'20,30':(400,600)}
    agent.save()
    loaded=LearningAgent(path)
    assert loaded.q==agent.q and loaded.steps==8
    assert loaded.visits==agent.visits and loaded.food_memory==agent.food_memory
    assert json.loads(path.read_text())['kind'].startswith('artificial')


def test_memory_uses_observed_food_and_learning_can_freeze():
    agent=LearningAgent(None,enabled=False)
    body=FlyBody(x=400,y=400,angle=0)
    world=World(foods=[(900,700)],obstacles=[])
    agent.command(body,sense(body,world),world)
    assert not agent.food_memory  # No omniscient read of hidden world.foods.
    world.foods=[(500,400)]
    agent.command(body,sense(body,world),world)
    assert agent.food_memory
    agent.elapsed=1
    agent.command(body,sense(body,world),world)
    assert agent.steps==0
    agent.observe(body,world,.1,collected=1)
    assert agent.meals==1 and agent.reward>=15


def test_small_arena_learning_improves_heldout_food_acquisition():
    baseline=rollout(LearningAgent(None,enabled=False),episodes=30,seed=2026,train=False)
    learner=LearningAgent(None)
    rollout(learner,episodes=120,seed=42,train=True)
    before=learner.steps
    evaluated=rollout(learner,episodes=30,seed=2026,train=False)
    assert evaluated['success_rate']>baseline['success_rate']+.5
    assert evaluated['success_rate']>=.9
    assert learner.steps==before


def test_autonomous_agent_moves_learns_and_suspends_for_manual_interactions(tmp_path):
    from flyworld.app import App
    from flyworld.__main__ import parser
    args=parser().parse_args(['--mode','autonomous','--no-neural-observer','--headless',
        '--memory',str(tmp_path/'memory.json'),'--output',str(tmp_path/'session')])
    app=App(args)
    try:
        assert app.adapter is None
        start=(app.body.x,app.body.y)
        for _ in range(20):app.update(.1)
        assert math.hypot(app.body.x-start[0],app.body.y-start[1])>0
        assert app.learner.steps>0
        count=app.learner.steps
        app.interact('pet')
        for _ in range(10):app.update(.1)
        assert app.learner.steps==count and app.body.speed==0
        app.dashboard.draw(app)
        app.recorder.save()
        assert pd.read_parquet(app.recorder.directory/'spikes.parquet').empty
    finally:app.close()
    assert (tmp_path/'memory.json').exists()


def test_asynchronous_brain_observation_does_not_advance_body_clock_or_duplicate_spikes(tmp_path):
    from flyworld.app import App
    from flyworld.__main__ import parser
    from flyworld.brain_adapter import NeuralFrame
    from flyworld.experiments import get_experiment
    args=parser().parse_args(['--mode','autonomous','--no-neural-observer','--headless',
        '--memory',str(tmp_path/'memory.json'),'--output',str(tmp_path/'session')])
    app=App(args)
    data=pd.DataFrame({'time_ms':[1.], 'trial':[0], 'neuron_index':[0],
        'flywire_id':[get_experiment('sugar')['neu_exc'][0]],'exp_name':['sugar']})
    class Observer:
        ready=True
        error=''
        closed=False
        def __init__(self):self.frame=NeuralFrame(0,20,data,.2,138639,'sugar',.5,.0);self.requests=[]
        def poll(self):frame,self.frame=self.frame,None;return frame
        def request(self,strength,world_s=None):self.requests.append((strength,world_s))
        def close(self):self.closed=True
    observer=Observer();app.adapter=observer
    try:
        app.update(.1)
        assert app.time==pytest.approx(.1)
        assert app.frame.end_ms==20
        assert observer.requests[-1][1]==pytest.approx(.1)
        app.update(.1)
        assert app.time==pytest.approx(.2)
        target=app.recorder.save()
        assert len(pd.read_parquet(target/'spikes.parquet'))==1
        assert app.learner.steps==0  # Decision interval has not elapsed.
    finally:app.close()
    assert observer.closed
