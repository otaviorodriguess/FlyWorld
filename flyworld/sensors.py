"""Virtual proximity is geometry, not a biological sensory transduction model."""
import math
from .world import World
from .fly_body import FlyBody

def sense(body: FlyBody, world: World, reach: float = 220) -> dict:
    nearest = min(world.foods, key=lambda f: math.hypot(f[0]-body.x, f[1]-body.y), default=None)
    distance = math.hypot(nearest[0]-body.x, nearest[1]-body.y) if nearest else math.inf
    bearing = ((math.atan2(nearest[1]-body.y, nearest[0]-body.x)-body.angle+math.pi) % math.tau-math.pi) if nearest else 0
    rays = {}
    for name, offset in [('left', -.6), ('front', 0), ('right', .6)]:
        hit = reach
        for d in range(12, int(reach)+1, 5):
            if world.blocked(body.x+math.cos(body.angle+offset)*d, body.y+math.sin(body.angle+offset)*d, 12):
                hit = d
                break
        rays[name] = max(0., 1-hit/reach)
    return {'food': max(0., 1-distance/reach), 'food_distance': distance,
            'bearing': bearing, **rays}
