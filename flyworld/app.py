"""Pygame orchestration with fixed physics and an independent neural clock."""
import math
from pathlib import Path
import pygame
from .config import Config, ROOT
from .world import World
from .fly_body import FlyBody, MotorCommand
from .sensors import sense
from .controllers import DemoController, avoid_obstacles
from .brain_adapter import ReplayAdapter, LiveAdapter, NeuralFrame
from .neural_decoder import NeuralDecoder
from .dashboard import Dashboard
from .recorder import Recorder
from .interactions import InteractionState
from .recordings import NeuralArchive, registered_archive
from .library import NeuralLibrary
from .learning import LearningAgent

class App:
    def __init__(self, args):
        self.args = args
        self.config = Config(dt=args.dt, neural_block_ms=args.block_ms)
        self.world, self.body = World.garden(), FlyBody(x=3000,y=2000)
        self.interaction = InteractionState()
        self.mode = args.mode
        self.experiment = args.experiment
        self.speed = 1.
        self.intensity = 1.
        self.stim_enabled = True
        self.manual = False
        self.paused = False
        self.time = 0.
        self.accumulator = 0.
        self.frame = NeuralFrame()
        self.adapter = None
        self.library = None
        self.archive_record = None
        self.recorder = None
        self.closed = False
        self.notice = ''
        self.demo = DemoController()
        self.learner=LearningAgent(args.memory,enabled=not args.no_learning)
        self.brain_error=''
        self._last_memory_save=0.
        self.decoder = NeuralDecoder(gain=args.decoder_gain)
        self.drive = MotorCommand()
        self.p9_rate = 0.
        self.comparison = {'on':[0,0.], 'off':[0,0.]}
        self.baseline_rate = None
        self.population = 0
        import pandas as pd
        comp = ROOT/'data/2025_Completeness_783.csv'
        if comp.exists():
            self.population = len(pd.read_csv(comp, usecols=[0]))
        try:
            archive_path=args.archive or registered_archive()
            archive=None
            if archive_path and archive_path.exists():
                archive=NeuralArchive(archive_path,max_mb=args.max_recording_mb)
                if args.archive:archive.register()
            elif args.archive:
                raise ValueError('ZIP não encontrado: '+str(args.archive))
            self.library=NeuralLibrary(archive,self.population)
            if args.recording:
                if not archive:raise ValueError('--recording precisa de uma biblioteca ZIP registrada ou --archive.')
                self.archive_record=archive.find(args.recording)
                self.mode=args.mode='replay'
                self.experiment=args.experiment=self.archive_record.experiment
                args.duration_ms=self.archive_record.duration_s*1000
                args.spikes=archive.cache/self.archive_record.member
            self.adapter=self.make_adapter(self.mode)
            self.replay_rate=self.compute_replay_rate()
            if self.mode=='replay':self.speed=args.replay_speed
            if self.mode=='replay':NeuralLibrary.analyze(self.adapter)
            if args.baseline_spikes:
                baseline = ReplayAdapter(args.baseline_spikes, trial=args.trial, population=self.population,
                    duration_ms=args.duration_ms)
                seconds = baseline.duration_ms/1000
                self.baseline_rate = baseline.data.flywire_id.isin(self.decoder.ids).sum()/2/seconds
            pygame.display.init()
            pygame.font.init()
            self.screen = pygame.display.set_mode((1500,900), pygame.RESIZABLE)
            pygame.display.set_caption('FlyWorld 3D — micromundo e atividade neural')
            self.dashboard = Dashboard(self.screen)
            self.dashboard.view3d = args.view == '3d'
            self.dashboard.show_neural=self.mode=='replay' and self.archive_record is not None
            self.library.opened=args.library
            self.start_recorder()
            self.body.sensors = sense(self.body, self.world, self.config.sensor_range)
        except Exception:
            self.close()
            raise

    def make_adapter(self, mode):
        if mode == 'replay':
            if self.archive_record is not None and self.library and self.library.archive:
                return self.library.archive.replay(self.archive_record,self.args.trial,self.population)
            if not self.args.spikes:
                raise ValueError('Modo replay precisa de --spikes caminho/arquivo.parquet.')
            return ReplayAdapter(self.args.spikes, self.args.trial, self.args.replay_exp,
                                 self.population, self.args.duration_ms)
        if mode == 'live' or (mode=='autonomous' and not self.args.no_neural_observer):
            return LiveAdapter(self.experiment, self.config.neural_block_ms)
        return None

    def start_recorder(self):
        if self.recorder:
            self.recorder.close()
        self.recorder = Recorder(Path(self.args.output), {'mode':self.mode,
            'experiment':self.adapter.name if self.mode == 'replay' else self.experiment, 'spikes_source':str(self.args.spikes) if self.mode=='replay' else None,
            'archive_recording':self.archive_record.member if self.mode=='replay' and self.archive_record else None,
            'verified_sha256':self.archive_record.sha256 if self.mode=='replay' and self.archive_record else None,
            'trial':self.args.trial, 'physics_dt_s':self.config.dt,
            'neural_block_ms':self.config.neural_block_ms,
            'decoder':'P9 population rate / 100 Hz, experimental, no validated turning',
            'decoder_gain':self.args.decoder_gain,
            'motor_controller':'artificial Q-learning' if self.mode=='autonomous' else self.mode,
            'learning_memory':str(self.learner.path),
            'neural_role':'asynchronous observer only' if self.mode=='autonomous' else 'experimental decoder',
            'neural_observer_enabled':self.mode=='autonomous' and self.adapter is not None,
            'world_size':[self.world.width,self.world.height], 'interaction_policy':'artificial demo-only',
            'collision_policy':'geometric heuristic', 'demo_neural_data':False})

    def reset(self, mode=None):
        if self.mode=='autonomous':self.learner.save()
        mode = mode or self.mode
        # Construct/validate first: a malformed replay must not kill a working mode.
        adapter = self.make_adapter(mode)
        if self.adapter:
            self.adapter.close()
        self.adapter, self.mode = adapter, mode
        self.replay_rate = self.compute_replay_rate()
        if self.mode=='replay':NeuralLibrary.analyze(self.adapter)
        self.world, self.body = World.garden(), FlyBody(x=3000,y=2000)
        self.interaction = InteractionState()
        self.learner.new_episode()
        self._last_memory_save=0.
        self.brain_error=''
        self.body.sensors = sense(self.body, self.world, self.config.sensor_range)
        self.frame, self.drive = NeuralFrame(), MotorCommand()
        self.time = self.accumulator = self.p9_rate = 0.
        self.paused = False
        self._last_record = -1
        self.comparison = {'on':[0,0.], 'off':[0,0.]}
        self.dashboard.history.clear()
        self.start_recorder()
        self.notice = 'Nova sessão. Live reinicia a rede apenas neste reset/troca de experimento.'

    def manual_command(self):
        keys = pygame.key.get_pressed()
        return MotorCommand(float(keys[pygame.K_UP]), float(keys[pygame.K_LEFT]),
                            float(keys[pygame.K_RIGHT]), float(keys[pygame.K_DOWN]))

    def physics(self, seconds, neural_command=None):
        remaining = seconds
        while remaining > 1e-10:
            dt = min(self.config.dt, remaining)
            sensors = sense(self.body, self.world, self.config.sensor_range)
            self.body.sensors = sensors
            learning_active=False
            if self.manual:
                self.learner.suspend()
                command = self.manual_command()
            elif self.mode=='autonomous':
                guided=self.interaction.command(self.body,sensors,self.time,self.mode)
                if guided is not None:
                    self.learner.suspend()
                    command=guided
                else:
                    command=self.learner.command(self.body,sensors,self.world)
                    learning_active=True
            elif self.mode == 'demo':
                command = self.interaction.command(self.body,sensors,self.time,self.mode) or self.demo.command(sensors, self.time)
            else:
                command = avoid_obstacles(neural_command or self.drive, sensors)
            collected_before=self.world.interactions
            self.body.update(command, dt, self.world, self.config)
            if learning_active:self.learner.observe(self.body,self.world,dt,self.world.interactions-collected_before)
            self.time += dt
            remaining -= dt
        self.body.sensors = sense(self.body, self.world, self.config.sensor_range)

    def accept_frame(self, frame):
        self.frame = frame
        duration = frame.end_ms-frame.start_ms
        self.drive = self.decoder.decode(frame.spikes, duration)
        count = int(frame.spikes.flywire_id.isin(self.decoder.ids).sum())
        self.p9_rate = count/2/(duration/1000) if duration else 0
        if self.mode == 'live':
            group = self.comparison['on' if frame.stimulus else 'off']
            group[0] += count
            group[1] += duration/1000
        self.dashboard.history.append((frame.end_ms,len(frame.spikes)))
        self.physics(duration/1000, self.drive)
        self.recorder.append(self, frame)

    def compute_replay_rate(self):
        if self.mode != 'replay':
            return 0.
        return float(self.adapter.data.flywire_id.isin(self.decoder.ids).sum()/2/(self.adapter.duration_ms/1000))

    def comparison_label(self):
        if self.mode == 'replay':
            if self.baseline_rate is None:
                return 'Baseline ausente (--baseline-spikes)'
            return f'{self.replay_rate:.1f} / {self.baseline_rate:.1f} Hz (P9)'
        values = []
        for key in ['on','off']:
            count, seconds = self.comparison[key]
            values.append(f'{count/2/seconds:.1f} Hz' if seconds else 'sem dados')
        return ' / '.join(values)

    def update(self, elapsed):
        if self.paused or (self.library and self.library.opened):
            return
        if self.mode in ('demo','autonomous'):
            self.accumulator += min(elapsed,.1)*self.speed
            while self.accumulator >= self.config.dt:
                self.physics(self.config.dt)
                self.accumulator -= self.config.dt
            if int(self.time*10) != getattr(self, '_last_record', -1):
                self._last_record = int(self.time*10)
                if self.mode=='autonomous':
                    self.recorder.append(self,self.frame,include_spikes=False)
                else:
                    self.recorder.append(self,NeuralFrame())
            if self.mode=='autonomous':
                self.update_neural_observer()
                if self.time-self._last_memory_save>=10:
                    self.learner.save()
                    self._last_memory_save=self.time
        elif self.mode == 'replay':
            self.accumulator += min(elapsed,.1)*self.speed*1000
            while self.accumulator >= self.config.neural_block_ms and not self.adapter.finished:
                self.accept_frame(self.adapter.advance(self.config.neural_block_ms))
                self.accumulator -= self.config.neural_block_ms
            if self.adapter.finished:
                self.notice = 'Fim do replay. R para reiniciar; estímulos atuais não alteram a gravação.'
                self.paused = True
        else:
            frame = self.adapter.poll()
            if frame is not None:
                self.accept_frame(frame)
            if self.adapter.error:
                self.notice = 'Erro neural: '+self.adapter.error
                self.paused = True
            elif not self.adapter.ready:
                self.notice = 'Carregando conectoma em processo separado...'
            else:
                self.notice = f'Brian2 CPU | setup {self.adapter.setup_s:.1f}s | mundo aguarda blocos neurais'
                self.accumulator += min(elapsed,.1)*self.speed*1000
                if self.accumulator >= self.config.neural_block_ms and not self.adapter.pending:
                    strength = self.intensity * self.stim_enabled
                    if self.experiment == 'sugar':
                        strength *= self.body.sensors.get('food',0)
                    self.adapter.request(strength)
                    # No backlog: neural throughput sets the effective live speed.
                    self.accumulator = 0.

    def update_neural_observer(self):
        if self.adapter is None:return
        frame=self.adapter.poll()
        if frame is not None:
            self.frame=frame
            duration=frame.end_ms-frame.start_ms
            count=int(frame.spikes.flywire_id.isin(self.decoder.ids).sum())
            self.p9_rate=count/2/(duration/1000) if duration else 0.
            self.dashboard.history.append((frame.end_ms,len(frame.spikes)))
            self.recorder.append(self,frame)
        if self.adapter.error:
            self.brain_error=self.adapter.error
        elif self.adapter.ready:
            strength=self.intensity*float(self.stim_enabled)
            if self.experiment=='sugar':strength*=self.body.sensors.get('food',0)
            self.adapter.request(strength,world_s=self.time)

    def event(self, event):
        if event.type == pygame.QUIT:
            return False
        if self.library and self.library.opened and event.type!=pygame.VIDEORESIZE:
            self.library.handle(event)
            return True
        if event.type==pygame.KEYDOWN and event.key==pygame.K_o:
            self.library.opened=True
            return True
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1 and self.dashboard.library_button.collidepoint(event.pos):
            self.library.opened=True
            return True
        if event.type == pygame.VIDEORESIZE:
            self.screen = pygame.display.set_mode((max(1100,event.w),max(820,event.h)), pygame.RESIZABLE)
            self.dashboard.screen = self.screen
        if event.type == pygame.MOUSEWHEEL:
            self.dashboard.zoom = max(.6,min(3.5,self.dashboard.zoom+event.y*.15))
        if event.type == pygame.MOUSEMOTION and len(event.buttons)>1 and event.buttons[1]:
            camera = self.dashboard.scene3d.camera
            camera.yaw += event.rel[0]*.008
            camera.elevation = max(.25,min(1.35,camera.elevation-event.rel[1]*.006))
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 3 and self.dashboard.minimap_rect.collidepoint(event.pos) and not self.dashboard.help:
                camera=self.dashboard.scene3d.camera
                self.dashboard.view3d=True
                camera.focus=self.dashboard.minimap_to_world(event.pos,self.world)
                camera.follow=False
                self.dashboard.zoom=1.
                return True
            if event.button == 1 and not self.dashboard.help:
                for action, rect in self.dashboard.interaction_buttons.items():
                    if rect.collidepoint(event.pos):
                        self.interact(action)
                        return True
                if self.dashboard.minimap_rect.collidepoint(event.pos):
                    point=self.dashboard.minimap_to_world(event.pos,self.world)
                    self.interaction.selected='call'
                    self.interact('call',point)
                    return True
            point = self.dashboard.unproject(event.pos)
            if point and not self.dashboard.help:
                x,y = point
                if 0<=x<=self.world.width and 0<=y<=self.world.height:
                    if event.button == 1 and not self.world.blocked(x,y,12):
                        if self.interaction.selected in ('call','play'):
                            self.interact(self.interaction.selected,(x,y))
                        elif self.interaction.selected == 'pet':
                            if math.hypot(x-self.body.x,y-self.body.y)<65:
                                self.interact('pet')
                            else:
                                self.notice='Clique perto da mosca para interagir com ela.'
                        else:
                            self.world.foods.append((x,y))
                    elif event.button == 3:
                        self.world.edit_obstacle(x,y,self.body)
        if event.type == pygame.KEYDOWN:
            key = event.key
            if key == pygame.K_ESCAPE:
                return False
            if key == pygame.K_SPACE:
                self.paused = not self.paused
            elif key == pygame.K_r:
                self.reset()
            elif key in (pygame.K_1,pygame.K_2,pygame.K_3,pygame.K_4):
                self.reset({pygame.K_1:'demo',pygame.K_2:'replay',pygame.K_3:'live',pygame.K_4:'autonomous'}[key])
            elif key == pygame.K_u:
                self.learner.enabled=not self.learner.enabled
                self.learner.suspend()
                self.notice='Aprendizagem Q '+('ligada' if self.learner.enabled else 'pausada')+' · agente artificial'
            elif key == pygame.K_n:
                self.dashboard.show_neural=not self.dashboard.show_neural
            elif key == pygame.K_b:
                self.interact('feed')
            elif key == pygame.K_j:
                self.interact('play')
            elif key == pygame.K_k:
                self.interact('pet')
            elif key == pygame.K_l:
                self.interact('explore')
            elif key == pygame.K_v:
                self.dashboard.view3d = not self.dashboard.view3d
            elif key == pygame.K_c:
                camera = self.dashboard.scene3d.camera
                camera.follow = not camera.follow
                camera.focus = None
                self.dashboard.zoom = 1.
            elif key in (pygame.K_a,pygame.K_d):
                self.dashboard.scene3d.camera.yaw += .18 if key == pygame.K_d else -.18
            elif key in (pygame.K_w,pygame.K_x):
                camera = self.dashboard.scene3d.camera
                camera.elevation = max(.25,min(1.35,camera.elevation+(.1 if key == pygame.K_w else -.1)))
            elif key == pygame.K_f:
                self.dashboard.scene3d.show_sensors = not self.dashboard.scene3d.show_sensors
            elif key == pygame.K_m:
                self.manual = not self.manual
            elif key == pygame.K_g:
                self.dashboard.show_graphs = not self.dashboard.show_graphs
            elif key == pygame.K_h:
                self.dashboard.help = not self.dashboard.help
            elif key == pygame.K_t:
                self.stim_enabled = not self.stim_enabled
                self.notice = 'Estímulo '+('ligado' if self.stim_enabled else 'desligado')
            elif key in (pygame.K_LEFTBRACKET,pygame.K_RIGHTBRACKET):
                self.intensity = max(0,min(1,self.intensity+(.1 if key==pygame.K_RIGHTBRACKET else -.1)))
            elif key in (pygame.K_MINUS,pygame.K_EQUALS,pygame.K_PLUS):
                self.speed = max(.01,min(4,self.speed*(.5 if key==pygame.K_MINUS else 2)))
            elif key == pygame.K_e:
                if self.mode == 'replay':
                    self.notice = 'O experimento do replay é fixo; selecione outro arquivo na CLI.'
                else:
                    self.experiment = 'p9' if self.experiment=='sugar' else 'sugar'
                    self.reset()
            elif key == pygame.K_s:
                self.notice = 'Dados salvos: '+str(self.recorder.save())
        return True

    def interact(self,action,point=None):
        if action in ('call','play','pet'):
            self.interaction.selected=action
        else:
            self.interaction.selected='food'
        self.interaction.start(action,self.body,self.world,self.time,point)
        self.notice=self.interaction.message
        if self.mode not in ('demo','autonomous'):
            self.notice+=' | modo neural: sem resposta motora artificial'
        if self.recorder:
            self.recorder.record_interaction(self,action,point)

    def poll_library(self):
        if not self.library:return
        result=self.library.poll()
        if not result:return
        kind,value=result
        if kind=='error':
            self.notice='Biblioteca: '+value
        elif kind=='compare':
            self.notice='Comparação salva. Feche a biblioteca para retornar ao jardim.'
        else:
            adapter,record,trial=value
            if self.mode=='autonomous':self.learner.save()
            if self.adapter:self.adapter.close()
            self.adapter=adapter
            self.archive_record=record
            self.mode=self.args.mode='replay'
            self.experiment=self.args.experiment=record.experiment
            self.args.spikes=self.library.archive.cache/record.member
            self.args.trial=trial
            self.args.duration_ms=record.duration_s*1000
            self.args.replay_exp=None
            self.frame=NeuralFrame(population=self.population,experiment=record.experiment)
            self.accumulator=0.
            self.drive=MotorCommand()
            self.body.speed=0.
            self.manual=False
            self.interaction=InteractionState()
            self.paused=False
            self.speed=min(self.args.replay_speed,.1)
            self.baseline_rate=None
            self.replay_rate=self.compute_replay_rate()
            self.dashboard.history.clear()
            self.dashboard.show_neural=True
            self.library.opened=False
            self.start_recorder()
            self.notice=record.label+' · SHA-256 conferido · N: raster neural'

    def run(self):
        clock = pygame.time.Clock()
        running, frames = True, 0
        try:
            while running:
                elapsed = clock.tick(60)/1000
                for event in pygame.event.get():
                    try:
                        running = self.event(event) and running
                    except (ValueError, OSError) as exc:
                        self.notice = str(exc)
                if not running:
                    break
                self.poll_library()
                self.update(elapsed)
                self.dashboard.draw(self)
                frames += 1
                if self.args.frames and frames>=self.args.frames:
                    break
            if self.args.screenshot:
                pygame.image.save(self.screen,self.args.screenshot)
            self.recorder.save()
        finally:
            self.close()

    def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            if self.mode=='autonomous':self.learner.save()
        finally:
            if self.library:
                self.library.close()
            if self.adapter:
                self.adapter.close()
            if self.recorder:
                self.recorder.close()
            pygame.quit()
