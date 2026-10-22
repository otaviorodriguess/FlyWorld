"""Lightweight Pygame dashboard; neural evidence and policy are labelled."""
from collections import deque
import math
import pygame
from .scene3d import Scene3D

BG = (19, 31, 29)
TEXT = (226, 231, 211)
GREEN = (185, 218, 137)
CYAN = (102, 201, 239)
AMBER = (244, 185, 95)

class Dashboard:
    def __init__(self, screen):
        self.screen = screen
        self.scene3d = Scene3D()
        self.view3d = True
        self.font = pygame.font.SysFont('segoeui', 16)
        self.small = pygame.font.SysFont('consolas', 13)
        self.title = pygame.font.SysFont('segoeui', 27, bold=True)
        self.history = deque(maxlen=240)
        self.show_graphs = True
        self.help = False
        self.zoom = 1.
        self.offset = (0., 0.)
        self.scale = 1.
        self.library_button=pygame.Rect(380,21,210,32)
        self.show_neural=False
        self.interaction_buttons = {}
        self.minimap_rect = pygame.Rect(0,0,0,0)
        self.arena_rect = pygame.Rect(0, 0, 1, 1)

    def text(self, text, pos, color=TEXT, font=None):
        self.screen.blit((font or self.font).render(str(text), True, color), pos)

    def project(self, x, y):
        if self.view3d:
            point, _ = self.scene3d.camera.project([[x,y,0]])
            return tuple(round(v) for v in point[0])
        return (round(self.offset[0]+x*self.scale), round(self.offset[1]+y*self.scale))

    def unproject(self, point):
        if self.view3d:
            return self.scene3d.camera.pick_ground(point)
        if not self.arena_rect.collidepoint(point):
            return None
        return ((point[0]-self.offset[0])/self.scale, (point[1]-self.offset[1])/self.scale)

    def draw_interactions(self,app,available):
        width=(available.width-48)//5
        self.interaction_buttons={}
        labels=[('feed','B · Oferecer fruta'),('call','Chamar até aqui'),('pet','K · Fazer carinho'),('play','J · Brincar com luz'),('explore','L · Explorar livre')]
        mouse=pygame.mouse.get_pos()
        for index,(action,label) in enumerate(labels):
            rect=pygame.Rect(available.x+16+index*(width+4),available.bottom-71,width,47)
            self.interaction_buttons[action]=rect
            active=app.interaction.action==action and (action=='explore' or app.time<app.interaction.until)
            color=(97,132,80) if active else ((66,91,68) if rect.collidepoint(mouse) else (30,50,40))
            pygame.draw.rect(self.screen,color,rect,border_radius=10)
            pygame.draw.rect(self.screen,(166,193,132) if active else (103,126,91),rect,1,border_radius=10)
            self.text(label,(rect.x+12,rect.y+13),TEXT,self.font if width>175 else self.small)
        if app.interaction.action!='explore' and app.time<app.interaction.until:
            message=app.interaction.message
            card=pygame.Rect(available.centerx-240,available.y+80,480,35)
            pygame.draw.rect(self.screen,(29,49,38),card,border_radius=12)
            self.text(message[:67],(card.x+12,card.y+9),GREEN,self.small)

    def draw_minimap(self,app,available):
        rect=pygame.Rect(available.right-196,available.top+16,180,120)
        self.minimap_rect=rect
        pygame.draw.rect(self.screen,(35,57,43),rect,border_radius=9)
        pygame.draw.rect(self.screen,(157,184,120),rect,1,border_radius=9)
        def project(x,y):
            return (rect.x+int(x/app.world.width*rect.width),rect.y+int(y/app.world.height*rect.height))
        if app.mode=='autonomous':
            for cell in app.learner.visits:
                cx,cy=(int(v) for v in cell.split(','))
                pygame.draw.circle(self.screen,(76,104,61),project((cx+.5)*app.learner.cell_size,(cy+.5)*app.learner.cell_size),2)
        for x,y,rx,ry in app.world.ponds:
            center=project(x,y)
            pygame.draw.ellipse(self.screen,(79,155,164),(center[0]-rx/app.world.width*rect.width,
                center[1]-ry/app.world.height*rect.height,rx*2/app.world.width*rect.width,ry*2/app.world.height*rect.height))
        for obstacle in app.world.obstacles:
            pygame.draw.circle(self.screen,(105,143,74),project(obstacle.x,obstacle.y),2)
        for food in app.world.foods:
            pygame.draw.circle(self.screen,(224,206,128),project(*food),1)
        point=project(app.body.x,app.body.y)
        pygame.draw.circle(self.screen,(250,238,180),point,4)
        pygame.draw.line(self.screen,(250,238,180),point,(point[0]+int(math.cos(app.body.angle)*8),point[1]+int(math.sin(app.body.angle)*8)),2)
        if app.interaction.target:
            pygame.draw.circle(self.screen,(248,179,102),project(*app.interaction.target),4,1)
        self.text('JARDIM / você está aqui',(rect.x+8,rect.bottom+7),TEXT,self.small)

    def minimap_to_world(self,point,world):
        rect=self.minimap_rect
        return ((point[0]-rect.x)/rect.width*world.width,(point[1]-rect.y)/rect.height*world.height)

    def draw_raster(self,app,available):
        adapter=app.adapter
        if not self.show_neural or app.mode!='replay' or not hasattr(adapter,'raster'):return
        rect=pygame.Rect(available.x+18,available.y+80,min(850,available.width-38),340)
        pygame.draw.rect(self.screen,(20,37,34),rect,border_radius=12)
        pygame.draw.rect(self.screen,(123,167,131),rect,1,border_radius=12)
        self.text('ATIVIDADE REGISTRADA · N para ocultar',(rect.x+18,rect.y+12),GREEN,self.small)
        summary=adapter.neural_summary
        self.text(f'{summary["spikes"]:,} spikes / {summary["active"]} neurônios · Sugar GRNs: {summary["sugar_spikes"]:,} · P9: {summary["p9_spikes"]:,}',(rect.x+18,rect.y+37),font=self.small)
        left,top=rect.x+90,rect.y+72
        chart_width,chart_height=rect.width-110,220
        times,rows,ids=adapter.raster
        for i,neuron in enumerate(ids):
            yy=top+i*chart_height/16
            self.text(str(neuron)[-8:],(rect.x+12,yy-4),font=self.small)
            pygame.draw.line(self.screen,(34,56,49),(left,yy),(left+chart_width,yy))
        for time_ms,row in zip(times,rows):
            x=left+time_ms/adapter.duration_ms*chart_width
            y=top+row*chart_height/16
            pygame.draw.line(self.screen,(113,210,198),(x,y-1),(x,y+2))
        cursor=left+min(1,adapter.time_ms/adapter.duration_ms)*chart_width
        pygame.draw.line(self.screen,(239,192,108),(cursor,top-4),(cursor,top+chart_height),2)
        self.text('16 mais ativos · IDs abreviados · até 5.000 eventos', (rect.x+18,rect.bottom-30),font=self.small)
        self.text(f'0 — {adapter.duration_ms:g} ms',(rect.right-135,rect.bottom-30),font=self.small)

    def draw(self, app):
        surface = self.screen
        body = app.body
        w, h = surface.get_size()
        panel_x = w-340
        surface.fill(BG)
        self.text('FlyWorld · jardim 3D' if self.view3d else 'FlyWorld · mapa 2D', (22, 16), GREEN, self.title)
        label = {'autonomous':'LIVRE · agente aprendiz + cérebro observador','demo':'DEMO HEURÍSTICO', 'replay':'REPLAY NEURAL / gravação', 'live':'LIVE NEURAL / Brian2 CPU'}[app.mode]
        self.text(label, (22, 48), AMBER if app.mode in ('demo','autonomous') else CYAN)
        pygame.draw.rect(surface,(53,80,59),self.library_button,border_radius=8)
        self.text('Biblioteca neural · O',(self.library_button.x+12,self.library_button.y+6),GREEN)
        available = pygame.Rect(18, 84, panel_x-36, h-150)
        self.scale = min(available.width/app.world.width, available.height/app.world.height)*self.zoom
        cx, cy = (app.body.x, app.body.y) if self.zoom > 1 else (app.world.width/2, app.world.height/2)
        self.offset = (available.centerx-cx*self.scale, available.centery-cy*self.scale)
        self.arena_rect = available
        if self.view3d:
            camera = self.scene3d.camera
            camera.distance = (500. if camera.follow or camera.focus else max(app.world.width,app.world.height)*1.08) / self.zoom
            self.scene3d.draw(surface, available, app)
            self.text('CLAREIRAS, LAGOS E PEQUENAS DESCOBERTAS', (available.x+20,available.y+17), (242,245,216), self.small)
            self.text(f'{int(app.world.width):,} × {int(app.world.height):,} · 25× mais espaço para explorar', (available.x+20,available.y+38), (228,236,206), self.small)
            self.text('C: câmera geral / seguir   A/D: girar   W/X: inclinar   F: sensores',
                      (available.x+16,available.bottom-98), (190,215,178), self.small)
        else:
            surface.set_clip(available)
            pygame.draw.rect(surface, (19, 32, 43), available, border_radius=8)
            for x in range(0, int(app.world.width)+1, 250):
                pygame.draw.line(surface, (28, 44, 56), self.project(x, 0), self.project(x, app.world.height))
            for y in range(0, int(app.world.height)+1, 250):
                pygame.draw.line(surface, (28, 44, 56), self.project(0, y), self.project(app.world.width, y))
            for obstacle in app.world.obstacles:
                pos = self.project(obstacle.x, obstacle.y)
                rect = pygame.Rect(*pos, round(obstacle.width*self.scale), round(obstacle.height*self.scale))
                pygame.draw.rect(surface, (85, 101, 119), rect, border_radius=6)
                pygame.draw.rect(surface, (125, 145, 162), rect, 1, border_radius=6)
            for x,y in app.world.foods:
                pygame.draw.circle(surface, (31, 75, 52), self.project(x,y), max(3, round(25*self.scale)), 1)
                pygame.draw.circle(surface, GREEN, self.project(x,y), max(3, round(10*self.scale)))
            body = app.body
            pos = self.project(body.x, body.y)
            for name, offset in [('left', -.6), ('front', 0), ('right', .6)]:
                distance = app.config.sensor_range*(1-body.sensors.get(name, 0))
                endpoint = self.project(body.x+math.cos(body.angle+offset)*distance, body.y+math.sin(body.angle+offset)*distance)
                pygame.draw.line(surface, AMBER if body.sensors.get(name, 0) > .7 else (48, 87, 105), pos, endpoint)
            # Local coordinates preserve a recognisable top-down fly at any angle.
            def local(x, y):
                return self.project(body.x+x*math.cos(body.angle)-y*math.sin(body.angle), body.y+x*math.sin(body.angle)+y*math.cos(body.angle))
            pygame.draw.line(surface, (155,180,191), local(-14,-15), local(6,12), max(2,round(9*self.scale)))
            pygame.draw.line(surface, (155,180,191), local(-14,15), local(6,-12), max(2,round(9*self.scale)))
            for side in (-1,1):
                for dx in (-8, 0, 8):
                    pygame.draw.line(surface, AMBER, local(dx,side*5), local(dx-7,side*20), 1)
                pygame.draw.line(surface, CYAN, local(15,side*4), local(25,side*12), 1)
            pygame.draw.line(surface, (213,191,119), local(-13,0), local(9,0), max(5,round(13*self.scale)))
            pygame.draw.circle(surface, (238,216,151), local(14,0), max(4,round(7*self.scale)))
            pygame.draw.rect(surface, (73,111,128), pygame.Rect(*self.project(0,0), round(app.world.width*self.scale), round(app.world.height*self.scale)), 2)
            surface.set_clip(None)
        self.draw_raster(app,available)
        self.draw_interactions(app, available)
        self.draw_minimap(app,available)
        tool={'food':'oferecer comida','call':'chamar até o ponto','pet':'interagir perto da mosca','play':'mover a luz'}[app.interaction.selected]
        self.text(f'Clique: {tool} | botão direito: criar/remover obstáculo', (20,h-53), font=self.small)
        self.text('Espaço: pausa  R: reset  1/2/3/4: modo  H: ajuda', (20,h-31), font=self.small)
        pygame.draw.line(surface, (42,60,74), (panel_x,15), (panel_x,h-15))
        x, y = panel_x+18, 20
        self.text('Sua mosca', (x,y), GREEN, self.title)
        y += 14
        frame = app.frame
        status = 'PAUSADO' if app.paused else ('MANUAL' if app.manual else 'OBSERVAÇÃO')
        rows = [status, f'Mundo {app.time:8.2f} s', f'Neural {frame.end_ms:8.1f} ms',
                f'Velocidade {body.speed:6.1f} u/s', f'Estado: {body.state}',
                f'Comidas: {app.world.interactions}', f'Experimento: {frame.experiment or app.experiment}',
                ('Estímulo: gravado / imutável' if app.mode=='replay' else f'Estímulo: {app.intensity:.2f} / {"ON" if app.stim_enabled else "OFF"}'), f'Velocidade tempo: {app.speed:.2f}x',
                f'Alimento: {body.sensors.get("food",0):.2f}', f'Obstáculo: {body.sensors.get("front",0):.2f}']
        if app.mode=='autonomous':
            if app.adapter is None:brain_status='observador desligado'
            elif app.brain_error:brain_status='erro (agente continua)'
            elif not app.adapter.ready:brain_status='carregando Brian2 CPU'
            else:brain_status='ativo / assíncrono'
            rows=[status, f'Mundo {app.time:.1f} s · {body.speed:.1f} u/s',
                'Controle: Q-learning artificial',
                'Aprendizagem: '+('ligada / U pausa' if app.learner.enabled else 'pausada / U liga'),
                f'Experiências: {app.learner.steps:,}',f'Estados aprendidos: {len(app.learner.q)}',
                f'Comidas nesta sessão: {app.world.interactions}',
                f'Rede disponível: {app.population:,} neurônios',f'SNN: {brain_status}',
                f'Relógio neural: {frame.end_ms:.1f} ms',
                f'Spikes/bloco: {len(frame.spikes)} · ativos: {frame.active}',
                f'Média/população: {frame.mean_hz:.5f} Hz',
                f'Fator neural: {frame.realtime_factor:.4f}x',
                'Entrada do mundo: '+(f'{frame.stimulus_world_s:.1f} s' if frame.stimulus_world_s is not None else 'aguardando')]
        elif app.mode == 'demo':
            rows += ['Spikes: não processados', 'Cérebro disponível · demo inativo']
        else:
            rows += [f'Spikes/bloco: {len(frame.spikes)}', f'Ativos/bloco: {frame.active}',
                     f'Média/população: {frame.mean_hz:.4f} Hz' if frame.population else 'Média/população: N/D',
                     f'Processamento: {frame.processing_s:.3f} s',
                     f'Fator neural: {frame.realtime_factor:.4f}x' if app.mode == 'live' else 'Gravação: sem feedback neural']
        for row in rows:
            y += 25
            self.text(row, (x,y), font=self.small if len(row)>32 else self.font)
        y += 38
        self.text('NEURAL: spikes reais do modelo', (x,y), CYAN, self.small)
        self.text('SNN observa; agente aprende a mover' if app.mode=='autonomous' else 'P9 -> avanço: hipótese experimental', (x,y+21), CYAN, self.small)
        self.text('Q-learning não modifica o conectoma' if app.mode=='autonomous' else 'HEURÍSTICA: colisões / demo', (x,y+42), AMBER, self.small)
        if app.mode=='autonomous':
            top=y+85
            self.text('MEMÓRIA E EXPERIÊNCIA', (x,top),GREEN,self.small)
            self.text(f'Ação: {app.learner.last_action_label}',(x,top+28),font=self.small)
            self.text(f'Regiões visitadas: {len(app.learner.visits)}',(x,top+52),font=self.small)
            self.text(f'Alimentos lembrados: {len(app.learner.food_memory)}',(x,top+75),font=self.small)
            self.text(f'Última recompensa: {app.learner.last_reward:+.3f}',(x,top+98),font=self.small)
            self.text(f'Exploração aleatória: {app.learner.epsilon:.0%}',(x,top+121),font=self.small)
            self.text('Memória salva a cada 10s e ao sair.',(x,top+151),font=self.small)
            self.text('4: livre   U: pausar aprendizagem',(x,top+175),font=self.small)
            if app.brain_error:self.text(app.brain_error[:38],(x,top+198),AMBER,self.small)
            if self.show_graphs and len(self.history)>1:
                values=[count for _,count in self.history]
                maximum=max(1,max(values))
                points=[(x+i*285/(len(values)-1),top+270-value/maximum*40) for i,value in enumerate(values)]
                self.text('Spikes / bloco neural (observação)',(x,top+214),CYAN,self.small)
                pygame.draw.lines(surface,CYAN,False,points,2)
        if self.show_graphs and app.mode not in ('demo','autonomous'):
            top = y+78
            self.text('Spikes/bloco (relógio neural)', (x,top), CYAN, self.small)
            values = [n for _,n in self.history]
            if len(values)>1:
                maximum = max(1,max(values))
                points = [(x+i*290/(len(values)-1), top+100-v/maximum*70) for i,v in enumerate(values)]
                pygame.draw.lines(surface, CYAN, False, points, 2)
            self.text(f'P9 média Hz: {app.p9_rate:.1f}', (x,top+115), font=self.small)
            self.text('P9: replay / baseline' if app.mode == 'replay' else 'P9: estimulado / sem estímulo', (x,top+137), font=self.small)
            self.text(app.comparison_label(), (x,top+158), font=self.small)
            if app.mode == 'live':
                for index, key in enumerate(['on','off']):
                    count, seconds = app.comparison[key]
                    rate = count/2/seconds if seconds else 0
                    pygame.draw.rect(surface, CYAN if key == 'on' else AMBER,
                        (x+40,top+183+index*19,min(230,rate*2),10))
                    self.text(key, (x,top+178+index*19), font=self.small)
            elif app.mode == 'replay' and app.baseline_rate is not None:
                rate = app.replay_rate
                for index, (label, value) in enumerate([('replay',rate),('base',app.baseline_rate)]):
                    pygame.draw.rect(surface, CYAN if index == 0 else AMBER,
                        (x+55,top+183+index*19,min(210,value*2),10))
                    self.text(label, (x,top+178+index*19), font=self.small)
        if app.mode == 'demo':
            self.text('ENCONTROS NO JARDIM', (x,y+92), GREEN, self.small)
            self.text(f'Interações: {app.interaction.count}', (x,y+122))
            self.text('Respostas lúdicas / heurísticas', (x,y+148), AMBER, self.small)
            self.text('Não representam cognição biológica.', (x,y+169), TEXT, self.small)
            self.text('B: alimentar    K: carinho', (x,y+215), TEXT, self.small)
            self.text('J: brincar      L: explorar', (x,y+237), TEXT, self.small)
            self.text('Mapa: clique para chamar.', (x,y+280), TEXT, self.small)
            self.text('Botão direito: visitar a região.', (x,y+302), TEXT, self.small)
        if app.notice:
            self.text(app.notice[:105], (22,69), AMBER, self.small)
        if self.help:
            overlay = pygame.Surface((920,650))
            overlay.fill((24,38,51))
            surface.blit(overlay, (50,130))
            help_lines = ['CONTROLES', 'Espaço: iniciar/pausar | R: reiniciar sessão',
                'Clique esquerdo: alimento | direito: obstáculo', '1: demo | 2: replay (--spikes) | 3: live | 4: livre',
                'M: manual | setas: avançar/girar/parar', '[ / ]: intensidade do estímulo (0..1)',
                '- / =: velocidade do tempo (0.25..4x)', 'E: alternar sugar/P9 | T: ligar/desligar estímulo',
                'G: gráficos | roda: zoom | C: câmera geral/seguir', 'S: exportar dados | H: fechar ajuda | Esc: sair',
                'Azul: observação neural / decodificação experimental', 'Âmbar: decisões heurísticas / sensores geométricos',
                'Replay ignora estímulos atuais: gravação imutável.', 'Live avança o mundo por blocos neurais concluídos.',
                '3D: A/D ou arrastar botão central gira a câmera.',
                'W/X: inclinar | F: sensores | V: alternar 3D/2D',
                'Botões no jardim: alimentar, chamar, carinho, brincar.',
                'Minimapa: clique chama; botão direito visita uma região.',
                'O: biblioteca neural | N: raster do replay | F8 no catálogo: comparar',
                'U: pausar/ligar Q-learning | Livre: memória salva automaticamente']
            for i,line in enumerate(help_lines):
                self.text(line, (72,150+i*29), CYAN if i==0 else TEXT)
        if app.library:app.library.draw(self)
        pygame.display.flip()
