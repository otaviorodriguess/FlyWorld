"""Motor policy layers always carry explicit provenance."""
import math
from .fly_body import MotorCommand

def avoid_obstacles(command: MotorCommand, sensors: dict) -> MotorCommand:
    if sensors.get('front', 0) > .70:
        # Fixed tie-break avoids an indecisive symmetric response.
        left = sensors.get('left', 0) < sensors.get('right', 0)
        return MotorCommand(min(command.forward_drive, .12), float(left), float(not left), command.stop_drive)
    return command

class DemoController:
    def command(self, sensors: dict, t: float) -> MotorCommand:
        turn = sensors['bearing'] if sensors['food'] > 0 else .35 * math.sin(t*.7) + .18
        return avoid_obstacles(MotorCommand(.65, max(0, -turn), max(0, turn)), sensors)
