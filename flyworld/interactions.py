"""Playful interaction policies: explicitly artificial and demo-only motor control."""
from dataclasses import dataclass
import math
from .fly_body import MotorCommand
from .controllers import avoid_obstacles

@dataclass
class InteractionState:
    action: str = 'explore'
    target: tuple[float,float] | None = None
    until: float = 0.
    count: int = 0
    selected: str = 'food'
    message: str = 'Explore o jardim ou escolha uma interação.'

    def start(self, action: str, body, world, now: float, point=None):
        if action not in {'feed','call','pet','play','explore'}:
            raise ValueError('Interação desconhecida.')
        self.action, self.count = action, self.count+1
        self.target = None
        self.until = now + {'feed':12,'call':20,'pet':4,'play':16,'explore':0}[action]
        if action=='explore':
            self.message='Exploração livre.'
        elif action=='pet':
            self.message='Limpando as antenas · animação lúdica'
        else:
            target = point or (body.x+math.cos(body.angle)*100,body.y+math.sin(body.angle)*100)
            target=(max(30,min(world.width-30,target[0])),max(30,min(world.height-30,target[1])))
            if world.blocked(*target,25):
                self.action='explore'
                self.message='Escolha um ponto livre, longe da água e dos obstáculos.'
                return
            self.target=target
            if action=='feed':
                world.foods.append(target)
                self.message='Fruta oferecida. Aproxime-se para comer.'
            elif action=='call':
                self.message='Investigando seu marcador · controle heurístico'
            else:
                self.message='Seguindo a luz · brincadeira artificial'

    def command(self, body, sensors, now: float, mode: str):
        if mode not in ('demo','autonomous'):
            return None  # Never override or forge neural motor output.
        if now >= self.until or self.action=='explore':
            self.action='explore'
            self.target=None
            return None
        if self.action=='pet':
            return MotorCommand(stop_drive=1)
        if self.target is None:
            return None
        tx,ty=self.target
        if self.action=='play':
            tx += math.cos(now*1.4)*45
            ty += math.sin(now*1.4)*45
        dx,dy=tx-body.x,ty-body.y
        distance=math.hypot(dx,dy)
        turn=(math.atan2(dy,dx)-body.angle+math.pi)%math.tau-math.pi
        if distance<24:
            return MotorCommand(stop_drive=1)
        return avoid_obstacles(MotorCommand(.7 if abs(turn)<.8 else .22,
            max(0,-turn),max(0,turn)),sensors)
