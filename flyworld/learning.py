"""Persistent tabular Q-learning and spatial memory, NOT fly-brain plasticity."""
from collections import deque
from pathlib import Path
import json
import math
import random
from .fly_body import MotorCommand
from .controllers import avoid_obstacles
from .config import ROOT

DEFAULT_MEMORY=ROOT/'flyworld-output/learning/memory.json'
ACTIONS=(MotorCommand(.85),MotorCommand(.55,.65,0),MotorCommand(.55,0,.65),
         MotorCommand(0,1,0),MotorCommand(0,0,1),MotorCommand(.3),MotorCommand(stop_drive=1))

class LearningAgent:
    """Learns motor-action values. Geometric goals and safety are explicit aids."""
    interval=.35
    cell_size=160

    def __init__(self,path=DEFAULT_MEMORY,enabled=True,seed=42):
        self.path=Path(path) if path else None
        self.enabled=enabled
        self.rng=random.Random(seed)
        self.q={}
        self.visits={}
        self.food_memory={}
        self.steps=0
        self.meals=0
        self.collisions=0
        self.total_reward=0.
        self.last_reward=0.
        self.history=deque(maxlen=120)
        self.state=None
        self.action=0
        self.elapsed=0.
        self.reward=0.
        self.goal=None
        self.exploration_goal=None
        self.previous_distance=None
        self.previous_cell=None
        self.collision_pending=False
        self.last_safety=False
        self.last_action_label='avançar'
        self.load()

    @property
    def epsilon(self):
        return max(.05,.28*math.exp(-self.steps/6000)) if self.enabled else 0.

    def load(self):
        if not self.path or not self.path.exists():return
        data=json.loads(self.path.read_text(encoding='utf-8'))
        if data.get('schema')!=1:raise ValueError('Memória de aprendizagem incompatível.')
        q=data.get('q',{})
        if len(q)>10000 or any(len(values)!=len(ACTIONS) or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in values) for values in q.values()):
            raise ValueError('Tabela de aprendizagem inválida.')
        self.q={key:[float(v) for v in values] for key,values in q.items()}
        self.visits={str(key):int(value) for key,value in data.get('visits',{}).items() if int(value)>=0}
        self.food_memory={str(key):(float(value[0]),float(value[1])) for key,value in data.get('foods',{}).items() if len(value)==2 and all(math.isfinite(float(v)) for v in value)}
        self.steps=int(data.get('steps',0));self.meals=int(data.get('meals',0));self.collisions=int(data.get('collisions',0))
        self.total_reward=float(data.get('total_reward',0))
        if not math.isfinite(self.total_reward):raise ValueError('Recompensa da memória inválida.')

    def save(self):
        if not self.path:return
        self.path.parent.mkdir(parents=True,exist_ok=True)
        data={'schema':1,'kind':'artificial Q-learning; original connectome unchanged',
            'steps':self.steps,'meals':self.meals,'collisions':self.collisions,'total_reward':self.total_reward,
            'q':self.q,'visits':self.visits,'foods':self.food_memory}
        temporary=self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(data,ensure_ascii=False,allow_nan=False),encoding='utf-8')
        temporary.replace(self.path)

    def cell(self,body):
        return f'{int(body.x//self.cell_size)},{int(body.y//self.cell_size)}'

    def perceive(self,body,sensors,world):
        observed=None
        if sensors.get('food',0)>0:
            angle=body.angle+sensors['bearing']
            distance=sensors['food_distance']
            point=(body.x+math.cos(angle)*distance,body.y+math.sin(angle)*distance)
            key=f'{round(point[0]/20)},{round(point[1]/20)}'
            self.food_memory[key]=point
            observed=point
        # A remembered food close enough to inspect must still be observed.
        self.food_memory={key:point for key,point in self.food_memory.items()
            if math.hypot(point[0]-body.x,point[1]-body.y)>45
            or (observed is not None and math.hypot(point[0]-observed[0],point[1]-observed[1])<25)}
        # Only remember observed food; no reading hidden world.foods coordinates.
        if self.food_memory:
            self.goal=min(self.food_memory.values(),key=lambda p:math.hypot(p[0]-body.x,p[1]-body.y))
        else:
            if self.exploration_goal is None or math.hypot(self.exploration_goal[0]-body.x,self.exploration_goal[1]-body.y)<55:
                candidates=[]
                for index in range(8):
                    angle=index*math.tau/8
                    x=max(35,min(world.width-35,body.x+math.cos(angle)*260))
                    y=max(35,min(world.height-35,body.y+math.sin(angle)*260))
                    cell=f'{int(x//self.cell_size)},{int(y//self.cell_size)}'
                    candidates.append((self.visits.get(cell,0)+self.rng.random()*.5,(x,y)))
                self.exploration_goal=min(candidates,key=lambda item:item[0])[1]
            self.goal=self.exploration_goal
        dx,dy=self.goal[0]-body.x,self.goal[1]-body.y
        distance=math.hypot(dx,dy)
        bearing=(math.atan2(dy,dx)-body.angle+math.pi)%math.tau-math.pi
        direction=min(7,int((bearing+math.pi)/math.tau*8))
        danger=min(2,int(sensors.get('front',0)*3))
        left=int(sensors.get('left',0)>.55);right=int(sensors.get('right',0)>.55)
        state=f'{direction}:{min(2,int(distance/80))}:{danger}:{left}:{right}:{int(bool(self.food_memory))}'
        return state,distance

    def values(self,state):
        if state not in self.q:
            # Explicit small forward prior, not experience or neural evidence.
            self.q[state]=[.02,0.,0.,0.,0.,0.,-.02]
        return self.q[state]

    def update_value(self,state,action,reward,next_state,terminal=False):
        values=self.values(state)
        target=reward+(0 if terminal else .92*max(self.values(next_state)))
        values[action]+=.18*(target-values[action])
        self.steps+=1
        self.total_reward+=reward
        self.last_reward=reward
        self.history.append(reward)

    def select(self,state):
        if self.rng.random()<self.epsilon:return self.rng.randrange(len(ACTIONS))
        values=self.values(state)
        best=max(values)
        return self.rng.choice([i for i,value in enumerate(values) if value==best])

    def command(self,body,sensors,world):
        state,distance=self.perceive(body,sensors,world)
        if self.state is None or self.elapsed+1e-9>=self.interval:
            if self.state is not None and self.enabled:
                self.update_value(self.state,self.action,self.reward-.02,state)
            self.state=state
            self.action=self.select(state)
            self.elapsed=self.reward=0.
            self.previous_distance=distance
            self.collision_pending=False
        self.last_action_label=('avançar','curvar esquerda','curvar direita','girar esquerda','girar direita','avançar devagar','parar')[self.action]
        command=ACTIONS[self.action]
        safe=avoid_obstacles(command,sensors)
        self.last_safety=safe!=command
        return safe

    def observe(self,body,world,dt,collected=0):
        self.elapsed+=dt
        cell=self.cell(body)
        if cell!=self.previous_cell:
            visits=self.visits.get(cell,0)
            self.reward+=1.2 if visits==0 else -.035
            self.visits[cell]=visits+1
            self.previous_cell=cell
        if self.goal is not None:
            distance=math.hypot(self.goal[0]-body.x,self.goal[1]-body.y)
            if self.previous_distance is not None:
                self.reward+=max(-.2,min(.2,(self.previous_distance-distance)*.018))
            self.previous_distance=distance
        if collected:
            self.meals+=collected
            self.reward+=15*collected
            self.food_memory={k:p for k,p in self.food_memory.items() if math.hypot(p[0]-body.x,p[1]-body.y)>45}
            self.exploration_goal=None
            self.previous_distance=None
        if body.state=='colisão' and not self.collision_pending:
            self.collisions+=1
            self.collision_pending=True
            self.reward-=2
            self.exploration_goal=None
        if self.last_safety:
            self.reward-=dt*.12

    def suspend(self):
        """Do not attribute manual/guided interaction movement to Q actions."""
        self.state=None
        self.elapsed=self.reward=0.
        self.previous_distance=None
        self.previous_cell=None

    def new_episode(self):
        self.suspend()
        self.exploration_goal=None
        self.goal=None
        self.food_memory={}


def rollout(agent,episodes=80,seed=7,train=True):
    """Small explicit curriculum; reports measured outcomes, not biological learning."""
    from .world import World
    from .fly_body import FlyBody
    from .config import Config
    from .sensors import sense
    rng=random.Random(seed)
    config=Config()
    agent.enabled=train
    meals=0;returns=[]
    for episode in range(episodes):
        body=FlyBody(x=400,y=400,angle=rng.uniform(-math.pi,math.pi))
        angle=rng.uniform(-math.pi,math.pi)
        food=(400+math.cos(angle)*130,400+math.sin(angle)*130)
        world=World(width=800,height=800,foods=[food],obstacles=[])
        agent.new_episode()
        total=0.
        for _ in range(100):
            sensors=sense(body,world)
            command=agent.command(body,sensors,world)
            old=world.interactions
            # Same body and collision code, with a fixed 1/60 s physics step.
            for tick in range(21):
                body.update(command,1/60,world,config)
                agent.observe(body,world,1/60,world.interactions-old)
                old=world.interactions
            total+=agent.reward
            if world.interactions:
                if train and agent.state is not None:
                    agent.update_value(agent.state,agent.action,agent.reward,agent.state,terminal=True)
                agent.suspend()
                break
        meals+=world.interactions
        returns.append(total)
    return {'episodes':episodes,'foods_collected':meals,'success_rate':meals/episodes,
            'mean_shaped_return':sum(returns)/len(returns),'seed':seed,'training':train}


def main():
    import argparse
    parser=argparse.ArgumentParser(description='Treinamento artificial Q-learning, separado do conectoma')
    parser.add_argument('--memory',type=Path,default=DEFAULT_MEMORY)
    parser.add_argument('--episodes',type=int,default=120)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    if args.episodes<1:parser.error('--episodes deve ser positivo')
    agent=LearningAgent(args.memory)
    baseline=LearningAgent(None,enabled=False)
    before=rollout(baseline,40,seed=2026,train=False)
    training=rollout(agent,args.episodes,seed=42,train=True)
    after=rollout(agent,40,seed=2026,train=False)
    agent.enabled=True
    agent.new_episode()
    agent.visits={}
    agent.save()
    report={'kind':'artificial Q-learning, not connectome plasticity','before':before,
        'training':training,'after':after,'q_states':len(agent.q),'updates':agent.steps,
        'limitation':'Open small arena curriculum; does not establish improvement across the larger garden.'}
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
