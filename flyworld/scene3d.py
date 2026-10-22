"""Perspective 3D meshes rendered on CPU; biological dynamics stay in adapters.

The scene uses XYZ geometry, a pinhole camera, depth-sorted faces, directional
lighting and ground-plane ray picking. Walking remains a planar simulation.
"""
from functools import lru_cache
import math
import numpy as np
import pygame

@lru_cache(maxsize=8)
def sphere_mesh(rings=8, segments=14):
    vertices = np.array([(math.sin(math.pi*i/rings)*math.cos(math.tau*j/segments),
                          math.sin(math.pi*i/rings)*math.sin(math.tau*j/segments),
                          math.cos(math.pi*i/rings))
                         for i in range(rings+1) for j in range(segments)])
    faces = []
    for i in range(rings):
        for j in range(segments):
            a, b = i*segments+j, i*segments+(j+1)%segments
            c, d = a+segments, b+segments
            faces.extend([(a,c,b),(b,c,d)])
    return vertices, np.array(faces)

class Camera3D:
    def __init__(self):
        self.yaw = .88
        self.elevation = .61
        self.distance = 440.
        self.follow = True
        self.focus = None
        self.world_size=(1200,800)
        self.target = np.array([600.,400.,12.])
        self.rect = pygame.Rect(0,0,1,1)
        self.focal = 700.
        self.refresh()

    def refresh(self):
        offset = np.array([math.cos(self.yaw)*math.cos(self.elevation),
                           math.sin(self.yaw)*math.cos(self.elevation),math.sin(self.elevation)])
        self.eye = self.target+offset*self.distance
        self.forward = -offset
        self.right = np.cross(self.forward,[0.,0.,1.])
        self.right /= np.linalg.norm(self.right)
        self.up = np.cross(self.right,self.forward)

    def configure(self, rect, body):
        self.rect = pygame.Rect(rect)
        self.target = np.array([body.x,body.y,14.]) if self.follow else np.array([*(self.focus or (self.world_size[0]/2,self.world_size[1]/2)),0.])
        self.focal = min(rect.width*.93,rect.height*1.3)
        self.refresh()

    def project(self, points):
        points = np.atleast_2d(points).astype(float)
        relative = points-self.eye
        depth = np.einsum('ij,j->i',relative,self.forward)
        safe = np.maximum(depth,1.)
        screen = np.column_stack((self.rect.centerx+(np.einsum('ij,j->i',relative,self.right))*self.focal/safe,
                                  self.rect.centery-(np.einsum('ij,j->i',relative,self.up))*self.focal/safe))
        return screen,depth

    def pick_ground(self, point):
        if not self.rect.collidepoint(point):
            return None
        ray = self.forward+self.right*((point[0]-self.rect.centerx)/self.focal)-self.up*((point[1]-self.rect.centery)/self.focal)
        if ray[2] >= -1e-8:
            return None
        t = -self.eye[2]/ray[2]
        hit = self.eye+ray*t
        return float(hit[0]),float(hit[1])

class Scene3D:
    def __init__(self):
        self.camera = Camera3D()
        self.show_sensors = False
        self.faces = []
        self.lines = []
        self.light = np.array([-.35,-.45,.82])
        self.light /= np.linalg.norm(self.light)
        self.rng = np.random.default_rng(74)
        self.grass = self.rng.uniform([12,12,0],[1188,788,1],(750,3))
        self.pebbles = self.rng.uniform([20,20,0],[1180,780,1],(36,3))
        self.ground_pass = False
        self.walk_phase = 0.
        self.last_time = 0.

    def polygon(self, points, color, alpha=255, lit=True):
        points = np.asarray(points,dtype=float)
        if lit:
            normal = np.cross(points[1]-points[0],points[2]-points[0])
            length = np.linalg.norm(normal)
            amount = .55+.45*abs(float(normal@self.light)/length) if length else .65
            color = tuple(min(255,int(c*amount)) for c in color)
        if alpha < 255:
            self.transparent.append((points,color,alpha))
            return
        triangles = np.array([[points[0],points[i],points[i+1]] for i in range(1,len(points)-1)])
        count = len(triangles)
        self.meshes.append((triangles,np.tile(color,(count,1)),np.full(count,1000000 if self.ground_pass else 0),np.zeros((count,3))))

    def ellipsoid(self, center, radii, color, rotation=None, detail=0):
        vertices,faces = sphere_mesh(11 if detail else 5,22 if detail else 10)
        vertices = vertices*np.asarray(radii)
        if rotation is not None:
            vertices = vertices@rotation.T
        vertices += np.asarray(center)
        triangles=vertices[faces]
        normals=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
        lengths=np.linalg.norm(normals,axis=1)
        valid=lengths>1e-8
        triangles,normals,lengths=triangles[valid],normals[valid],lengths[valid]
        brightness=.58+.42*np.abs(normals@self.light)/np.maximum(lengths,1e-9)
        colors=np.clip(np.asarray(color)[None,:]*brightness[:,None],0,255).astype(np.uint8)
        self.meshes.append((triangles,colors,np.zeros(len(triangles)),normals))

    def line(self, start,end,color,width=1):
        self.lines.append((np.asarray([start,end],dtype=float),color,width))

    def tube(self,start,end,radius,color,sides=6):
        start,end=np.asarray(start,dtype=float),np.asarray(end,dtype=float)
        direction=end-start
        length=np.linalg.norm(direction)
        if length<1e-6: return
        direction/=length
        tangent=np.cross(direction,[0,0,1] if abs(direction[2])<.9 else [0,1,0])
        tangent/=np.linalg.norm(tangent)
        second=np.cross(direction,tangent)
        angles=np.arange(sides)*math.tau/sides
        ring=radius*(np.cos(angles)[:,None]*tangent+np.sin(angles)[:,None]*second)
        a,b=start+ring,end+ring
        triangles=np.stack((np.stack((a,b,np.roll(b,-1,axis=0)),axis=1),np.stack((a,np.roll(b,-1,axis=0),np.roll(a,-1,axis=0)),axis=1)),axis=1).reshape(-1,3,3)
        normal=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
        brightness=.6+.4*np.abs(normal@self.light)/np.maximum(np.linalg.norm(normal,axis=1),1e-9)
        colors=np.clip(np.array(color)*brightness[:,None],0,255).astype(np.uint8)
        self.meshes.append((triangles,colors,np.zeros(len(triangles)),np.zeros((len(triangles),3))))

    def box(self,x,y,w,h,z,color):
        a,b,c,d=(x,y,0),(x+w,y,0),(x+w,y+h,0),(x,y+h,0)
        A,B,C,D=(x,y,z),(x+w,y,z),(x+w,y+h,z),(x,y+h,z)
        for points in ([a,b,B,A],[b,c,C,B],[c,d,D,C],[d,a,A,D],[A,B,C,D]):
            self.polygon(points,color)

    def leaf(self, origin, length, width, angle, color):
        x,y,z=origin
        direction=np.array([math.cos(angle),math.sin(angle),0])
        side=np.array([-math.sin(angle),math.cos(angle),0])
        base=np.array(origin,dtype=float)
        tip=base+direction*length+np.array([0,0,8])
        middle=base+direction*length*.5+np.array([0,0,12])
        self.polygon([base,middle+side*width,tip,middle],color)
        self.polygon([base,middle,tip,middle-side*width],tuple(int(c*.83) for c in color))
        self.line(base+np.array([0,0,.3]),tip+np.array([0,0,.3]),(121,158,83),1)

    def ground_shape(self,points,color,layer):
        self.polygon(points,color,lit=False)
        triangles,colors,layers,normals=self.meshes[-1]
        self.meshes[-1]=(triangles,colors,np.full(len(layers),layer),normals)

    def environment(self,app):
        world=app.world
        width,height=world.width,world.height
        overview=not self.camera.follow and self.camera.focus is None
        if overview:
            xmin,ymin,xmax,ymax=0,0,width,height
        else:
            center=self.camera.focus if not self.camera.follow and self.camera.focus else (app.body.x,app.body.y)
            cellx,celly=round(center[0]/500)*500,round(center[1]/500)*500
            xmin,ymin=max(0,cellx-750),max(0,celly-750)
            xmax,ymax=min(width,cellx+1000),min(height,celly+1000)
        self.scene_bounds=(xmin,ymin,xmax,ymax)
        self.scene_overview=overview
        def nearby(x,y,pad=0):
            return xmin-pad<=x<=xmax+pad and ymin-pad<=y<=ymax+pad
        step=250 if overview else 125
        self.ground_pass=True
        for x in range(int(xmin),int(xmax),step):
            for y in range(int(ymin),int(ymax),step):
                tone=math.sin(x*.017+y*.013)*3+math.cos(y*.031)*2
                color=(int(109+tone),int(145+tone),int(74+tone))
                self.ground_shape([(x,y,.05),(min(x+step,width),y,.05),
                    (min(x+step,width),min(y+step,height),.05),(x,min(y+step,height),.05)],color,1000000)
        # A winding sandy path links the meadows without affecting locomotion.
        for x in range(max(0,int(xmin)-100),min(int(width),int(xmax)+100),80):
            y=height*.5+math.sin(x*.0018)*260
            yy=height*.5+math.sin((x+80)*.0018)*260
            self.ground_shape([(x,y-24,.15),(x+80,yy-24,.15),(x+80,yy+24,.15),(x,y+24,.15)],(184,172,117),990000)
        for px,py,rx,ry in world.ponds:
            if not nearby(px,py,max(rx,ry)):
                continue
            for scale,z,color,layer in [(1.13,.2,(172,178,111),985000),(1.,.4,(51,135,139),980000),(.84,.5,(64,157,164),979000)]:
                self.ground_shape([(px+math.cos(a*math.tau/48)*rx*scale,
                    py+math.sin(a*math.tau/48)*ry*scale,z) for a in range(48)],color,layer)
            if not overview:
                for i in range(9):
                    a=i*2.4
                    lx,ly=px+math.cos(a)*rx*.65,py+math.sin(a)*ry*.6
                    self.ground_shape([(lx+math.cos(j*math.tau/10)*9,ly+math.sin(j*math.tau/10)*7,1) for j in range(10)],(72,130,77),978000)
                    if i%3==0:
                        self.ellipsoid((lx,ly,3),(3,3,3),(236,177,186))
                for i in range(7):
                    a=i*.7
                    x,y=px+math.cos(a)*rx*1.08,py+math.sin(a)*ry*1.08
                    self.polygon([(x-2,y,1),(x+2,y,1),(x+4,y,33+i%4*4)],(83,117,59))
        self.ground_pass=False
        # Procedural decorations cover the larger map but only nearby detail is built.
        if getattr(self,'decoration_size',None)!=(width,height):
            rng=np.random.default_rng(74)
            self.grass=rng.uniform([15,15,0],[width-15,height-15,1],(14000,3))
            self.pebbles=rng.uniform([25,25,0],[width-25,height-25,1],(220,3))
            self.flowers=rng.uniform([25,25,0],[width-25,height-25,1],(850,3))
            self.decoration_size=(width,height)
        if not overview:
            for index,(x,y,_) in enumerate(self.grass):
                if not nearby(x,y) or world.blocked(x,y,5):
                    continue
                size=7+index%11
                self.polygon([(x-3,y,0),(x+2,y,size),(x+3,y,0)],(90+index%30,143+index%35,61))
                self.polygon([(x,y-3,0),(x-3,y+1,size*.8),(x,y+3,0)],(106,160,69))
            for i,(x,y,_) in enumerate(self.pebbles):
                if nearby(x,y) and not world.blocked(x,y,5):
                    self.ellipsoid((x,y,2),(4+i%5,3+i%3,2+i%2),(161,166,137))
            for i,(x,y,_) in enumerate(self.flowers):
                if not nearby(x,y) or world.blocked(x,y,8):
                    continue
                z=13+i%9
                self.line((x,y,0),(x,y,z),(60,112,58),2)
                color=[(248,205,104),(231,164,186),(195,177,228),(243,236,202)][i%4]
                for j in range(5):
                    angle=j*math.tau/5
                    dx,dy=math.cos(angle),math.sin(angle)
                    self.polygon([(x,y,z),(x+dx*7-dy*3,y+dy*7+dx*3,z+2),
                        (x+dx*9,y+dy*9,z+3),(x+dx*7+dy*3,y+dy*7-dx*3,z+2)],color)
                self.polygon([(x-2,y-2,z+2),(x+2,y-2,z+2),(x+2,y+2,z+2),(x-2,y+2,z+2)],(246,193,73),lit=False)
        for obstacle in world.obstacles:
            x,y=obstacle.x,obstacle.y
            if not nearby(x,y,180):
                continue
            if obstacle.kind=='tree':
                cx,cy=x+obstacle.width/2,y+obstacle.height/2
                self.tube((cx,cy,0),(cx-7,cy,120),10,(128,95,63),7)
                for dx,dy,z,scale in [(-23,0,140,58),(25,13,158,65),(-8,-20,190,59)]:
                    self.tube((cx-5,cy,85),(cx+dx,cy+dy,z),4,(128,95,63))
                    self.ellipsoid((cx+dx,cy+dy,z),(scale,scale*.85,scale*.72),(80+int(z)%23,137+int(z)%18,75),detail=0)
                continue
            self.ellipsoid((x+obstacle.width/2,y+obstacle.height/2,15),
                (obstacle.width*.65,obstacle.height*.65,26),(143,156,115))
            mx,my=x+obstacle.width*.55,y+obstacle.height*.48
            self.tube((mx,my,18),(mx,my,62),5,(232,217,170),8)
            self.ellipsoid((mx,my,66),(27,25,13),(205,106,74),detail=1)
            for a in range(5):
                theta=a*math.tau/5
                self.ellipsoid((mx+math.cos(theta)*15,my+math.sin(theta)*15,76),(3.5,3.5,1.2),(253,232,190))
    def food_geometry(self,app):
        world=app.world
        xmin,ymin,xmax,ymax=self.scene_bounds
        overview=self.scene_overview
        def nearby(x,y,pad=0):
            return xmin-pad<=x<=xmax+pad and ymin-pad<=y<=ymax+pad
        for x,y in world.foods:
            if not nearby(x,y,30):
                continue
            self.ellipsoid((x,y,4),(22,22,6),(89,149,57))
            self.ellipsoid((x,y,8),(19,19,3.5),(184,216,96))
            if not overview:
                for i in range(7):
                    angle=i*math.tau/7
                    sx,sy=x+math.cos(angle)*11,y+math.sin(angle)*11
                    self.polygon([(sx-1.5,sy-1,11.6),(sx+1.5,sy-1,11.6),(sx,sy+2,11.6)],(83,82,41),lit=False)
                self.leaf((x+4,y,10),25,8,.6,(106,166,72))

    def fly(self,body,t,interaction=None):
        # Anatomical shapes are illustrative. Animation never creates spikes.
        angle=body.angle
        rotation=np.array([[math.cos(angle),-math.sin(angle),0],[math.sin(angle),math.cos(angle),0],[0,0,1]])
        origin=np.array([body.x,body.y,0.])
        def local(point):
            return np.asarray(point)@rotation.T+origin
        def ell(center,radii,color,detail=0):
            self.ellipsoid(local(center),radii,color,rotation,detail)
        self.walk_phase += max(0,t-self.last_time)*body.speed*.10
        self.last_time=t
        phase=self.walk_phase
        grooming=interaction is not None and interaction.action=='pet' and t<interaction.until
        # Soft layered contact shadows, projected onto the ground.
        self.ground_pass = True
        for radius,shade in [(39,(61,78,55)),(30,(54,67,47)),(20,(46,56,40))]:
            self.polygon([local((math.cos(i*math.tau/28)*radius,math.sin(i*math.tau/28)*radius*.58,.3)) for i in range(28)],shade,lit=False)
            triangles,colors,layers,normals=self.meshes[-1]
            self.meshes[-1]=(triangles,colors,layers-100000,normals)
        self.ground_pass = False
        for side in (-1,1):
            for i,root_x in enumerate((-11,0,11)):
                cycle=phase+(i%2)*math.pi+(0 if side==1 else math.pi)
                swing=math.sin(cycle)*5 if body.speed>0 else 0
                lift=max(0,math.cos(cycle))*5 if body.speed>0 else 0
                if grooming and i==2:
                    lift=17+math.sin(t*14)*4
                    swing=18
                hip=(root_x,side*7,17)
                knee=(root_x-5+swing,side*(23+abs(i-1)*2),13+lift)
                ankle=(root_x-13+swing,side*(34+abs(i-1)*3),2+lift)
                for a,b,r in [(hip,knee,1.6),(knee,ankle,1.1),(ankle,(ankle[0]+6,ankle[1]+side*3,1+lift),.65)]:
                    self.tube(local(a),local(b),r,(98,66,39))
                ell(knee,(2,2,2),(151,108,58))
        ell((-17,0,17),(23,11,10),(195,139,62),1)
        # Dark transverse abdominal bands are curved surface strips.
        for xx in (-30,-22,-14,-6):
            ring=[]
            for i in range(21):
                a=math.tau*i/20
                factor=math.sqrt(max(0,1-((xx+17)/23)**2))
                ring.append(local((xx,math.cos(a)*11.05*factor,17+math.sin(a)*10.05*factor)))
            for a,b in zip(ring,ring[1:]):
                self.line(a,b,(65,49,30),2)
        ell((2,0,21),(15,12,12),(184,136,66),1)
        ell((3,0,29),(10,8,5),(196,157,83),1)
        # Tiny thoracic bristles.
        for x,y in [(-4,-7),(3,-8),(10,-6),(-4,7),(3,8),(10,6)]:
            self.line(local((x,y,29)),local((x-3,y*1.3,35)),(60,49,28),1)
        ell((20,0,23),(11,10,9),(177,131,62),1)
        for side in (-1,1):
            ell((24,side*7.8,25),(7,5.5,7.5),(210,57,43),1)
            ell((27,side*9,28),(2.1,1.3,2.5),(245,142,103))
            ell((27.7,side*9.2,29),(1.1,.8,1.2),(255,226,182))
            self.tube(local((29,side*3,25)),local((37,side*7,31)),.8,(96,66,37))
            ell((37,side*7,31),(2,1.4,1.5),(185,132,65))
            self.line(local((37,side*7,31)),local((43,side*11,36)),(83,64,37))
        self.tube(local((29,0,18)),local((34,0,13)),1.7,(128,83,43))
        # Two swept translucent wings, depth sorted with the body and legs.
        for side in (-1,1):
            flutter=math.sin(t*10)*.5
            contour=[(4,side*5,31),(-6,side*15,33),(-29,side*30,35+flutter),
                     (-48,side*29,34+flutter),(-55,side*20,33),(-45,side*10,32),(-19,side*6,31)]
            points=[local(p) for p in contour]
            self.polygon(points,(201,230,215),alpha=125,lit=False)
            for i in range(len(points)):
                self.line(points[i],points[(i+1)%len(points)],(185,217,198),1)
            root=local((3,side*6,31.2))
            for target in [(-49,side*20,34.3),(-42,side*27,35.2),(-25,side*27,35.3)]:
                self.line(root,local(target),(149,176,152),1)
            self.line(local((-24,side*13,33)),local((-29,side*27,35)),(149,176,152),1)

    @staticmethod
    def pack(meshes):
        if not meshes:
            return np.empty((0,3,3)),np.empty((0,3)),np.empty(0),np.empty((0,3))
        return tuple(np.concatenate([mesh[index] for mesh in meshes]) for index in range(4))

    def draw(self,surface,rect,app):
        self.camera.world_size=(app.world.width,app.world.height)
        self.camera.configure(rect,app.body)
        surface.set_clip(rect)
        for y in range(rect.top,rect.bottom,3):
            fraction=(y-rect.top)/rect.height
            color=(int(127+fraction*28),int(173+fraction*23),int(179+fraction*16))
            pygame.draw.rect(surface,color,(rect.left,y,rect.width,3))
        signature=(app.world.width,app.world.height,tuple(app.world.ponds),
            tuple((o.x,o.y,o.width,o.height,o.kind) for o in app.world.obstacles),
            self.camera.follow,self.camera.focus,(round(app.body.x/500),round(app.body.y/500)) if self.camera.follow else None)
        if signature != getattr(self,'world_signature',None):
            self.meshes,self.lines,self.transparent=[],[],[]
            self.environment(app)
            self.terrain_mesh=self.pack(self.meshes)
            self.terrain_lines=list(self.lines)
            self.world_signature=signature
            self.food_signature=None
        food_signature=(signature,tuple(app.world.foods))
        if food_signature != self.food_signature:
            self.meshes,self.lines,self.transparent=[],[],[]
            self.food_geometry(app)
            food_mesh=self.pack(self.meshes)
            self.world_mesh=tuple(np.concatenate((a,b)) for a,b in zip(self.terrain_mesh,food_mesh))
            self.world_lines=self.terrain_lines+list(self.lines)
            self.food_signature=food_signature
        self.meshes,self.lines,self.transparent=[],list(self.world_lines),[]
        self.fly(app.body,app.time,getattr(app,'interaction',None))
        dynamic=self.pack(self.meshes)
        triangles,colors,layers,normals=tuple(np.concatenate((a,b)) for a,b in zip(self.world_mesh,dynamic))
        centers=triangles.mean(axis=1)
        relative=centers-self.camera.eye
        zcenter=np.einsum('ij,j->i',relative,self.camera.forward)
        radii=np.linalg.norm(triangles-centers[:,None,:],axis=2).max(axis=1)
        h=rect.width/(2*self.camera.focal)
        v=rect.height/(2*self.camera.focal)
        candidate=(zcenter+radii>2)&(np.abs(np.einsum('ij,j->i',relative,self.camera.right))<zcenter*h+radii*(1+h))&(np.abs(np.einsum('ij,j->i',relative,self.camera.up))<zcenter*v+radii*(1+v))
        triangles,colors,layers,normals,centers=triangles[candidate],colors[candidate],layers[candidate],normals[candidate],centers[candidate]
        screen,depth=self.camera.project(triangles.reshape(-1,3))
        screen=screen.reshape(-1,3,2)
        depth=depth.reshape(-1,3)
        visible=(depth.min(axis=1)>2)&(screen[:,:,0].max(axis=1)>=rect.left)&(screen[:,:,0].min(axis=1)<=rect.right)&(screen[:,:,1].max(axis=1)>=rect.top)&(screen[:,:,1].min(axis=1)<=rect.bottom)
        visible &= np.einsum('ij,ij->i',normals,self.camera.eye-centers)<=0
        haze=np.clip((depth.mean(axis=1)-650)/2100,0,.48)
        colors=np.clip(colors*(1-haze[:,None])+np.array([173,193,159])*haze[:,None],0,255).astype(np.uint8)
        indices=np.flatnonzero(visible)
        distances=depth.mean(axis=1)+layers
        primitives=[(distances[i],0,points,tuple(color),255) for i,points,color in zip(indices,screen[indices].astype(int).tolist(),colors[indices].tolist())]
        for points,color,alpha in self.transparent:
            projected,z=self.camera.project(points)
            if z.min()>2:
                primitives.append((float(z.mean()),0,projected.astype(int).tolist(),color,alpha))
        if self.show_sensors:
            for name,offset in [('left',-.6),('front',0),('right',.6)]:
                distance=app.config.sensor_range*(1-app.body.sensors.get(name,0))
                endpoint=(app.body.x+math.cos(app.body.angle+offset)*distance,app.body.y+math.sin(app.body.angle+offset)*distance,2)
                self.line((app.body.x,app.body.y,3),endpoint,(245,195,106),2)
        if self.lines:
            coords=np.array([line[0] for line in self.lines])
            projected,z=self.camera.project(coords.reshape(-1,3))
            projected=projected.reshape(-1,2,2).astype(int).tolist()
            z=z.reshape(-1,2)
            for i,(points,color,width) in enumerate(self.lines):
                if z[i].min()>2:
                    primitives.append((float(z[i].mean()),1,projected[i],color,width))
        primitives.sort(key=lambda item:item[0],reverse=True)
        for distance,kind,points,color,extra in primitives:
            if kind:
                pygame.draw.line(surface,color,points[0],points[1],extra)
            elif extra==255:
                pygame.draw.polygon(surface,color,points)
            else:
                bounds=pygame.Rect(min(p[0] for p in points),min(p[1] for p in points),
                    max(p[0] for p in points)-min(p[0] for p in points)+1,max(p[1] for p in points)-min(p[1] for p in points)+1).clip(rect)
                if bounds.width and bounds.height:
                    layer=pygame.Surface(bounds.size,pygame.SRCALPHA)
                    pygame.draw.polygon(layer,(*color,extra),[(x-bounds.x,y-bounds.y) for x,y in points])
                    surface.blit(layer,bounds.topleft)
        interaction=getattr(app,'interaction',None)
        if interaction and interaction.target and app.time<interaction.until:
            tx,ty=interaction.target
            if interaction.action=='play':
                tx+=math.cos(app.time*1.4)*45
                ty+=math.sin(app.time*1.4)*45
            point,z=self.camera.project([[tx,ty,22 if interaction.action=='play' else 2]])
            if z[0]>2:
                point=tuple(point[0].astype(int))
                pygame.draw.circle(surface,(254,229,145),point,10,2)
                pygame.draw.circle(surface,(255,246,200),point,4)
        surface.set_clip(None)
