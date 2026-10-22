from dataclasses import dataclass, field
import math
from .config import Config
from .world import World

@dataclass(frozen=True)
class MotorCommand:
    forward_drive: float = 0
    turn_left_drive: float = 0
    turn_right_drive: float = 0
    stop_drive: float = 0

    def velocities(self, config: Config) -> tuple[float, float]:
        clip = lambda v: max(0., min(1., v))
        return (config.max_speed * clip(self.forward_drive) * (1-clip(self.stop_drive)),
                config.max_turn * (clip(self.turn_right_drive)-clip(self.turn_left_drive)))

@dataclass
class FlyBody:
    x: float = 600
    y: float = 400
    angle: float = -1.3
    speed: float = 0
    angular_speed: float = 0
    state: str = 'parada'
    food_contact: bool = False
    sensors: dict = field(default_factory=dict)
    radius: float = 12

    def update(self, command: MotorCommand, dt: float, world: World, config: Config) -> None:
        self.speed, self.angular_speed = command.velocities(config)
        self.angle = (self.angle + self.angular_speed * dt) % math.tau
        distance = self.speed * dt
        # Substeps prevent tunnelling even when a caller uses a large dt.
        steps = max(1, math.ceil(abs(distance) / (self.radius / 2)))
        collided = False
        for _ in range(steps):
            nx = self.x + math.cos(self.angle) * distance / steps
            ny = self.y + math.sin(self.angle) * distance / steps
            if world.blocked(nx, ny, self.radius):
                collided = True
                self.speed = 0
                break
            self.x, self.y = nx, ny
        self.food_contact = world.collect(self.x, self.y)
        self.state = 'colisão' if collided else ('caminhando' if self.speed else 'parada')
