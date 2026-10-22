"""Geometry only: no neural or rendering dependencies."""
from dataclasses import dataclass, field
import math

@dataclass
class Obstacle:
    x: float
    y: float
    width: float = 90
    height: float = 70
    kind: str = "rock"

    def distance(self, x: float, y: float) -> float:
        return math.hypot(max(self.x-x, 0, x-self.x-self.width), max(self.y-y, 0, y-self.y-self.height))

@dataclass
class World:
    width: float = 1200
    height: float = 800
    foods: list[tuple[float, float]] = field(default_factory=lambda: [(240, 200), (980, 640), (850, 200), (755, 360), (470, 560)])
    obstacles: list[Obstacle] = field(default_factory=lambda: [Obstacle(400, 280), Obstacle(740, 480)])
    interactions: int = 0
    ponds: list[tuple[float,float,float,float]] = field(default_factory=list)

    @classmethod
    def garden(cls):
        """25x the original area; deterministic scenery and safe central spawn."""
        import random
        rng=random.Random(74)
        foods=[(3155,1960),(2870,2160),(3250,1800),(2740,1880)]
        obstacles=[Obstacle(2710,1730,90,70,'mushroom'),Obstacle(3210,2200,100,80,'mushroom')]
        ponds=[(3150,1690,180,100),(3490,2110,210,125),(1750,1200,280,175),(4380,2850,350,180)]
        world=cls(6000,4000,foods,obstacles,ponds=ponds)
        for _ in range(54):
            x,y=rng.uniform(100,5900),rng.uniform(100,3900)
            if math.hypot(x-3000,y-2000)<350 or world.blocked(x,y,60):
                continue
            obstacles.append(Obstacle(x,y,45,45,'tree' if rng.random()<.65 else 'mushroom'))
        # Frame the starting clearing with foliage without hiding the fly.
        obstacles.extend([Obstacle(2580,2050,45,45,'tree'),Obstacle(3180,1570,45,45,'tree'),Obstacle(3440,1720,45,45,'tree')])
        for _ in range(48):
            x,y=rng.uniform(80,5920),rng.uniform(80,3920)
            if not world.blocked(x,y,35):
                foods.append((x,y))
        return world

    def _near_obstacles(self,x,y,radius):
        # Editor adds/removes objects; cache by count and explicit invalidation.
        if getattr(self,'_obstacle_count',-1)!=len(self.obstacles):
            self._cells={}
            for index,o in enumerate(self.obstacles):
                for cx in range(int(o.x//250),int((o.x+o.width)//250)+1):
                    for cy in range(int(o.y//250),int((o.y+o.height)//250)+1):
                        self._cells.setdefault((cx,cy),[]).append(index)
            self._obstacle_count=len(self.obstacles)
        found=set()
        for cx in range(int((x-radius)//250),int((x+radius)//250)+1):
            for cy in range(int((y-radius)//250),int((y+radius)//250)+1):
                found.update(self._cells.get((cx,cy),()))
        return (self.obstacles[i] for i in found)

    def blocked(self, x: float, y: float, radius: float = 12) -> bool:
        return (x < radius or y < radius or x > self.width-radius or y > self.height-radius
                or any(o.distance(x, y) < radius for o in self._near_obstacles(x,y,radius))
                or any(((x-px)/(rx+radius))**2+((y-py)/(ry+radius))**2 < 1 for px,py,rx,ry in self.ponds))

    def collect(self, x: float, y: float, radius: float = 25) -> bool:
        found = [f for f in self.foods if math.hypot(f[0]-x, f[1]-y) <= radius]
        self.interactions += len(found)
        for f in found:
            self.foods.remove(f)
        return bool(found)

    def edit_obstacle(self, x: float, y: float, body) -> None:
        self._obstacle_count=-1
        for obstacle in self.obstacles:
            if obstacle.distance(x, y) == 0:
                self.obstacles.remove(obstacle)
                return
        obstacle = Obstacle(max(0, min(self.width-90, x-45)), max(0, min(self.height-70, y-35)))
        if obstacle.distance(body.x, body.y) >= body.radius:
            self.obstacles.append(obstacle)
