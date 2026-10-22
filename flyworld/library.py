"""In-app neural recording browser and background import/comparison jobs."""
from concurrent.futures import ThreadPoolExecutor
import json
import threading
import pygame
from .recordings import BACKENDS
from .experiments import get_experiment

class NeuralLibrary:
    def __init__(self,archive,population):
        self.archive=archive
        self.population=population
        self.opened=False
        self.backend=None
        self.short_only=True
        self.single_trial=True
        self.selected=0
        self.trial=0
        self.error=''
        self.report=None
        self.future=None
        self.job=''
        self.stop=threading.Event()
        self.executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='neural-library')
        self.buttons={}
        self.row_rects=[]
        self.closed=False

    def records(self):
        if not self.archive:return []
        return [r for r in self.archive.records if (self.backend is None or r.backend==self.backend)
                and (not self.short_only or r.duration_s<=1) and (not self.single_trial or r.trials==1)]

    def current(self):
        records=self.records()
        if not records:return None
        self.selected=max(0,min(self.selected,len(records)-1))
        self.trial=min(self.trial,records[self.selected].trials-1)
        return records[self.selected]

    def submit(self,kind):
        if self.future or not self.archive:return
        record=self.current()
        if record is None:return
        self.error=''
        self.job=kind
        trial=self.trial
        if kind=='load':
            def load():
                adapter=self.archive.replay(record,trial,self.population,self.stop)
                adapter.catalog_record=record
                self.analyze(adapter)
                return adapter,record,trial
            self.future=self.executor.submit(load)
        else:
            self.future=self.executor.submit(self.archive.compare,record.duration_s,record.trials,record.round,trial,self.population,self.stop)

    @staticmethod
    def analyze(adapter):
        import numpy as np
        data=adapter.data
        counts=data.flywire_id.value_counts()
        ids=counts.head(16).index.tolist()
        sample=data[data.flywire_id.isin(ids)]
        if len(sample)>5000:sample=sample.iloc[::int(np.ceil(len(sample)/5000))]
        rows={int(n):i for i,n in enumerate(ids)}
        adapter.raster=(sample.time_ms.to_numpy(),np.array([rows[int(n)] for n in sample.flywire_id]),ids)
        adapter.neural_summary={'spikes':len(data),'active':len(counts),
            'sugar_spikes':int(data.flywire_id.isin(get_experiment('sugar')['neu_exc']).sum()),
            'p9_spikes':int(data.flywire_id.isin(get_experiment('p9')['neu_exc']).sum())}

    def poll(self):
        if not self.future or not self.future.done():return None
        future,self.future=self.future,None
        try:
            result=future.result()
            if self.job=='compare':
                self.report=result
                path=self.archive.cache/f'comparison_r{result["round"]}_t{result["duration_s"]}_n{result["n_trials_in_file"]}_trial{result["selected_trial"]}.json'
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8')
                self.report['saved_path']=str(path)
            return self.job,result
        except Exception as exc:
            self.error=str(exc)
            return 'error',self.error

    def handle(self,event):
        if event.type==pygame.KEYDOWN:
            key=event.key
            if key in (pygame.K_ESCAPE,pygame.K_o):self.opened=False
            elif key==pygame.K_UP:self.selected=max(0,self.selected-1);self.trial=0
            elif key==pygame.K_DOWN:self.selected+=1;self.trial=0
            elif key==pygame.K_PAGEUP:self.selected=max(0,self.selected-7);self.trial=0
            elif key==pygame.K_PAGEDOWN:self.selected+=7;self.trial=0
            elif key==pygame.K_LEFT:self.trial=max(0,self.trial-1)
            elif key==pygame.K_RIGHT:
                record=self.current()
                if record:self.trial=min(record.trials-1,self.trial+1)
            elif key==pygame.K_TAB:self.action('backend')
            elif key==pygame.K_l:self.action('length')
            elif key==pygame.K_n:self.action('trials')
            elif key==pygame.K_RETURN:self.submit('load')
            elif key==pygame.K_F8:self.submit('compare')
        elif event.type==pygame.MOUSEWHEEL:
            self.selected=max(0,self.selected-event.y)
            self.trial=0
        elif event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            for name,rect in self.buttons.items():
                if rect.collidepoint(event.pos):
                    self.action(name)
                    return
            for index,rect in self.row_rects:
                if rect.collidepoint(event.pos):self.selected=index;self.trial=0
        self.current()

    def action(self,name):
        if name=='close':self.opened=False
        elif name=='backend':
            values=[None,*BACKENDS]
            self.backend=values[(values.index(self.backend)+1)%len(values)]
            self.selected=self.trial=0
        elif name=='length':self.short_only=not self.short_only;self.selected=self.trial=0
        elif name=='trials':self.single_trial=not self.single_trial;self.selected=self.trial=0
        elif name=='load':self.submit('load')
        elif name=='compare':self.submit('compare')
        elif name=='report':self.report=None
        elif name=='trial_prev':self.trial=max(0,self.trial-1)
        elif name=='trial_next':
            record=self.current()
            if record:self.trial=min(record.trials-1,self.trial+1)

    def draw(self,dashboard):
        if not self.opened:return
        screen=dashboard.screen
        width,height=screen.get_size()
        veil=pygame.Surface((width,height),pygame.SRCALPHA)
        veil.fill((5,14,12,190));screen.blit(veil,(0,0))
        rect=pygame.Rect(55,65,width-110,height-125)
        pygame.draw.rect(screen,(24,42,37),rect,border_radius=16)
        pygame.draw.rect(screen,(127,160,111),rect,1,border_radius=16)
        x,y=rect.x+25,rect.y+22
        dashboard.text('Biblioteca neural · registros reais', (x,y),(185,218,137),dashboard.title)
        self.buttons={}
        self.row_rects=[]
        def button(name,label,bounds):
            self.buttons[name]=pygame.Rect(bounds)
            pygame.draw.rect(screen,(55,80,63),self.buttons[name],border_radius=7)
            dashboard.text(label,(bounds[0]+10,bounds[1]+8),font=dashboard.small)
        button('close','Fechar / Esc',(rect.right-140,y,110,34))
        if not self.archive:
            dashboard.text('Nenhum pacote registrado. Inicie com --archive caminho/nature_2026_07.zip.',(x,y+90))
            return
        experiments=', '.join(sorted({r.experiment for r in self.archive.records}))
        dashboard.text(f'{len(self.archive.records)} gravações · {experiments} · sem resposta ao cenário atual',(x,y+45),font=dashboard.small)
        if self.report is not None:
            report=self.report
            dashboard.text(f'Comparação: {report["duration_s"]:g}s · rodada {report["round"]} · trial {report["selected_trial"]}',(x,y+95))
            dashboard.text('Backend                 Spikes    Ativos    Jaccard CPU    Correlação de taxas',(x,y+135),font=dashboard.small)
            for i,row in enumerate(report['rows']):
                yy=y+170+i*48
                correlation=row['rate_correlation_cpu']
                value=f'{correlation:.4f}' if correlation is not None else 'N/D'
                dashboard.text(f'{BACKENDS[row["backend"]]:20} {row["spikes"]:9} {row["active"]:9}     {row["active_jaccard_cpu"]:.4f}              {value}',(x,yy),font=dashboard.small)
                pygame.draw.rect(screen,(139,188,123),(x+640,yy+3,220*row['active_jaccard_cpu'],10),border_radius=3)
            dashboard.text('Mesma condição e trial. Similaridade estatística não comprova equivalência temporal/biológica.',(x,y+490),font=dashboard.small)
            dashboard.text('Relatório JSON salvo no cache da biblioteca.',(x,y+515),font=dashboard.small)
            button('report','Voltar ao catálogo',(x,rect.bottom-65,200,38))
        else:
            button('backend','Backend: '+BACKENDS.get(self.backend,'todos')+' / Tab',(x,y+80,270,34))
            button('length','Duração: '+('até 1s / L' if self.short_only else 'todas / L'),(x+280,y+80,220,34))
            button('trials','Trials: '+('arquivos n=1 / N' if self.single_trial else 'todos / N'),(x+510,y+80,250,34))
            records=self.records();record=self.current()
            page=self.selected//7
            dashboard.text(f'{len(records)} resultados · página {page+1} · setas/roda para selecionar',(x,y+130),font=dashboard.small)
            dashboard.text('BACKEND / CONDIÇÃO                                    SPIKES TOTAIS     TAMANHO',(x,y+160),font=dashboard.small)
            for index in range(page*7,min(len(records),(page+1)*7)):
                row=records[index]
                bounds=pygame.Rect(x,y+188+(index-page*7)*43,rect.width-50,39)
                self.row_rects.append((index,bounds))
                pygame.draw.rect(screen,(66,94,69) if index==self.selected else (30,51,43),bounds,border_radius=6)
                dashboard.text(row.label,(bounds.x+12,bounds.y+10),font=dashboard.small)
                dashboard.text(f'{row.spikes:12,}       {row.size_bytes/1024**2:6.2f} MB',(bounds.x+565,bounds.y+10),font=dashboard.small)
            bottom=rect.bottom-135
            if record:
                dashboard.text(f'Trial escolhido: {self.trial} de 0..{record.trials-1} · duração exata {record.duration_s*1000:g} ms',(x,bottom),font=dashboard.small)
            button('trial_prev','Trial <',(x+600,bottom-8,90,30));button('trial_next','Trial >',(x+700,bottom-8,90,30))
            button('load','Reproduzir / Enter',(x,bottom+35,220,38))
            button('compare','Comparar 6 backends / F8',(x+235,bottom+35,280,38))
            dashboard.text('SHA-256 verificado por arquivo. Importação seletiva; o ZIP completo não é extraído.',(x,bottom+85),font=dashboard.small)
        if self.future:
            dashboard.text('Importando e verificando...' if self.job=='load' else 'Comparando arquivos verificados...',(x,rect.bottom-15),(238,191,110),dashboard.small)
        elif self.error:
            dashboard.text(self.error[:145],(x,rect.bottom-15),(242,158,110),dashboard.small)

    def close(self):
        if self.closed:return
        self.closed=True
        self.stop.set()
        self.executor.shutdown(wait=True,cancel_futures=True)
