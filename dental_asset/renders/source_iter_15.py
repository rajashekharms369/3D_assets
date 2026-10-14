"""Procedural 28-tooth dental study. Run with Python 3.11 + bpy 4.3.

Coordinates are centimetre-like Blender units; anterior is -Y, upper is +Z.
All previews and final deliverables come from this same mesh/lighting pipeline.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from PIL import Image

from gum_mesh import build_gum

ROOT = Path(__file__).resolve().parent
KINDS = ['central', 'lateral', 'canine', 'premolar1', 'premolar2', 'molar1', 'molar2']


def smoothstep(x):
    x = max(0., min(1., x))
    return x*x*(3-2*x)


def profile(t, points):
    for i, ((x0,y0),(x1,y1)) in enumerate(zip(points, points[1:])):
        if t <= x1:
            f = max(0.,min(1.,(t-x0)/(x1-x0)))
            a=points[max(0,i-1)];b=points[min(len(points)-1,i+2)]
            m0=(y1-a[1])/(x1-a[0]);m1=(b[1]-y0)/(b[0]-x0)
            return (2*f**3-3*f**2+1)*y0+(f**3-2*f*f+f)*(x1-x0)*m0+(-2*f**3+3*f*f)*y1+(f**3-f*f)*(x1-x0)*m1
    return points[-1][1]


class Arch:
    def __init__(self, rx, ry, yoff=0):
        self.rx, self.ry, self.yoff = rx, ry, yoff
        self.ts = np.linspace(0, 2.2, 5001)
        speed = np.sqrt((rx*np.cos(self.ts))**2 + (ry*np.sin(self.ts))**2)
        self.ss = np.r_[0, np.cumsum((speed[1:]+speed[:-1])*.5*np.diff(self.ts))]
        self.max_s = 6.2

    def frame(self, s):
        theta = np.interp(abs(s), self.ss, self.ts) * (1 if s>=0 else -1)
        x,y = self.rx*math.sin(theta), -self.ry*math.cos(theta)+self.yoff
        t = Vector((self.rx*math.cos(theta), self.ry*math.sin(theta)))
        t.normalize()
        return (x,y), (t.x,t.y), (t.y,-t.x)


def texture_files():
    dest = ROOT/'textures'
    dest.mkdir(exist_ok=True)
    rng = np.random.default_rng(2871)
    n=512
    yy,xx=np.mgrid[0:n,0:n]/n
    height=np.zeros((n,n))
    for frequency, amplitude in [(17, .25),(39,.18),(81,.12),(137,.07)]:
        for _ in range(6):
            angle=rng.uniform(0,math.tau)
            kx=round(frequency*math.cos(angle)); ky=round(frequency*math.sin(angle))
            height+=amplitude*np.sin(math.tau*(kx*xx+ky*yy)+rng.uniform(0,math.tau))
    for name,strength in [('enamel_normal',.07),('gum_normal',.15)]:
        dx=(np.roll(height,-1,1)-np.roll(height,1,1))*strength
        dy=(np.roll(height,-1,0)-np.roll(height,1,0))*strength
        normal=np.stack([-dx,-dy,np.ones_like(dx)],-1)
        normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
        Image.fromarray(np.uint8(np.clip((normal*.5+.5)*255,0,255))).save(dest/f'{name}.png')
    v=np.linspace(1,0,n)[:,None]
    mix=np.clip((v-.58)/.26,0,1)
    mix=mix*mix*(3-2*mix)
    ends=np.minimum(xx,1-xx)
    end_mix=np.clip((.07-ends)/.07,0,1)**2
    mix=np.maximum(mix,end_mix*(.12+.78*np.clip(v/.8,0,1)))
    # Images are encoded in sRGB. Tissue colour varies gently along the arch.
    pink=np.array([.97,.52,.60]); lavender=np.array([.72,.65,.96])
    color=pink[None,None,:]*(1-mix[:,:,None])+lavender[None,None,:]*mix[:,:,None]
    color=np.broadcast_to(color,(n,n,3)).copy()
    variation=.001*height[:,:,None]
    color+=variation
    Image.fromarray(np.uint8(np.clip(color,0,1)*255)).save(dest/'gingiva_color.png')
    rough=np.broadcast_to(.14+.21*mix,(n,n))
    Image.fromarray(np.uint8(rough*255)).save(dest/'gingiva_roughness.png')
    q=np.linspace(1,0,n)[:,None]
    ivory=np.array([.985,.958,.87])[None,None,:]
    pearl=np.array([.97,.978,.994])[None,None,:]
    edge=np.clip((q-.60)/.36,0,1)**1.5
    enamel=ivory*(1-edge[:,:,None])+pearl*edge[:,:,None]
    neck=np.clip((.20-q)/.20,0,1)
    enamel=enamel*(1-neck[:,:,None]*.08)
    enamel=np.broadcast_to(enamel,(n,n,3)).copy()+height[:,:,None]*.004
    Image.fromarray(np.uint8(np.clip(enamel,0,1)*255)).save(dest/'enamel_color.png')


def image_node(nodes, name, noncolor=False):
    tex=nodes.new('ShaderNodeTexImage')
    tex.image=bpy.data.images.load(str(ROOT/'textures'/name),check_existing=True)
    tex.extension='EXTEND' if 'normal' not in name else 'REPEAT'
    if noncolor: tex.image.colorspace_settings.name='Non-Color'
    return tex


def material(name, color, rough=.19, sss=.10, transmission=.07, gum=False, normal_strength=.5):
    m=bpy.data.materials.new(name); m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF'); links=m.node_tree.links; nodes=m.node_tree.nodes
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=rough
    p.inputs['IOR'].default_value=1.62 if not gum else 1.40
    p.inputs['Specular IOR Level'].default_value=.80 if not gum else .65
    p.inputs['Subsurface Weight'].default_value=sss
    p.inputs['Subsurface Radius'].default_value=(1,.47,.28)
    p.inputs['Subsurface Scale'].default_value=.10 if not gum else .16
    p.inputs['Transmission Weight'].default_value=transmission
    p.inputs['Coat Weight'].default_value=.85 if not gum else .42
    p.inputs['Coat Roughness'].default_value=.055 if not gum else .08
    if gum:
        color_tex=image_node(nodes,'gingiva_color.png')
        links.new(color_tex.outputs['Color'],p.inputs['Base Color'])
        rough_tex=image_node(nodes,'gingiva_roughness.png',True)
        links.new(rough_tex.outputs['Color'],p.inputs['Roughness'])
    elif name.startswith('Pearly'):
        color_tex=image_node(nodes,'enamel_color.png')
        links.new(color_tex.outputs['Color'],p.inputs['Base Color'])
    normal_tex=image_node(nodes,'gum_normal.png' if gum else 'enamel_normal.png',True)
    coords=nodes.new('ShaderNodeTexCoord')
    mapping=nodes.new('ShaderNodeMapping')
    mapping.inputs['Scale'].default_value=(14,2,1) if gum else (2,1,1)
    links.new(coords.outputs['UV'],mapping.inputs['Vector'])
    links.new(mapping.outputs['Vector'],normal_tex.inputs['Vector'])
    normal=nodes.new('ShaderNodeNormalMap'); normal.inputs['Strength'].default_value=normal_strength
    links.new(normal_tex.outputs['Color'],normal.inputs['Color']); links.new(normal.outputs['Normal'],p.inputs['Normal'])
    # A smooth wet coat lies over the fine enamel/tissue detail rather than
    # inheriting the exaggerated micro-normal slopes of the substrate.
    geom=nodes.new('ShaderNodeNewGeometry')
    links.new(geom.outputs['Normal'],p.inputs['Coat Normal'])
    m.diffuse_color=(*color,1)
    return m


def crown_mesh(tooth, mat, cfg):
    """Anatomical loft, asymmetric facial/lingual cross-section and shaped bite cap."""
    w,d,h=tooth['w'],tooth['d'],tooth['h']; kind=tooth['index']; sign=tooth['sign_z']
    cerv=tooth['cerv']; bite=cerv-sign*h
    N=48; rings=24; cap_rings=8
    verts=[]; faces=[]; uv=[]
    exponent=cfg.get('crown_exponent',3.25) if kind<3 else 2.85
    def xy(phi,q):
        ca,sa=math.cos(phi),math.sin(phi)
        if kind<2:
            wf=profile(q,[(0,.55 if sign<0 else .65),(.18,.73),(.55,.94),(.82,1.),(1,.93)])
            df=profile(q,[(0,.67),(.25,.88),(.57,1),(.82,.67),(1,.24)])
        elif kind==2:
            wf=profile(q,[(0,.63),(.20,.82),(.5,1),(.8,.96),(1,.79)])
            df=profile(q,[(0,.65),(.35,.98),(.58,1),(.85,.76),(1,.40)])
        else:
            wf=profile(q,[(0,.70),(.2,.93),(.5,1),(.8,.99),(1,.81)])
            df=profile(q,[(0,.72),(.25,.96),(.6,1),(1,.88)])
        x=math.copysign(abs(ca)**(2/exponent),ca)*w*.5*wf
        y=math.copysign(abs(sa)**(2/exponent),sa)*d*.5*df
        # Facially convex in elevation, flatter in section; lingual is slightly narrower.
        if sa<0: y*=.88
        if kind<2:y+=.22*q**1.8
        elif kind==2:y+=.11*q**1.8
        facial=max(0,sa)**3
        ridge=.013*math.cos(x/(w*.5)*math.pi*2.0)*math.sin(math.pi*q)**1.2
        if kind>=3:
            nx=x/(w*.5)
            ridge+=.030*(math.exp(-((nx-.40)/.30)**2)+math.exp(-((nx+.38)/.30)**2))*math.sin(math.pi*q)
        y+=facial*(ridge + .018*math.sin(math.pi*q))
        x+=.015*w*math.sin(q*math.pi)*tooth['variation']
        return x,y
    def bite_relief(x,y):
        nx=x/(w*.5); ny=y/(d*.5)
        if kind<2:
            # Rounded incisal corners and very shallow mamelons, not a round end.
            return -.075*abs(nx)**7 + .009*math.cos(nx*math.pi*3)*(1-abs(nx))
        if kind==2:
            return .035-.20*abs(nx-.05)**1.22-.035*abs(ny)
        # Two / four cusps on a broad occlusal table, with a central valley.
        cusp=.0
        peaks=[(0,.50,.14),(0,-.47,.11)] if kind<5 else [(-.46,.47,.13),(.46,.47,.145),(-.43,-.43,.11),(.44,-.43,.12)]
        for px,py,a in peaks:
            cusp+=a*math.exp(-((nx-px)**2/.105+(ny-py)**2/.14))
        return cusp*.44+.014-.14*abs(nx)**4
    for j in range(rings+1):
        q=j/rings
        for k in range(N):
            phi=math.tau*k/N
            x,y=xy(phi,q)
            relief=bite_relief(x,y)
            z=cerv-sign*h*q-sign*relief*q**7
            # Very restrained facial vertical developmental ridges are geometric.
            verts.append((x,y,z)); uv.append((k/N,q*.83))
    for j in range(rings):
        for k in range(N):
            a=j*N+k; b=j*N+(k+1)%N
            faces.append((a,b,b+N,a+N))
    # Radial, crown-specific occlusal surface; no cone-shaped molar caps.
    previous=rings*N
    for j in range(1,cap_rings+1):
        radius=1-j/(cap_rings+1)
        current=len(verts)
        for k in range(N):
            phi=math.tau*k/N; x,y=xy(phi,1)
            shift=.22 if kind<2 else .11 if kind==2 else 0.
            x*=radius; y=(y-shift)*radius+shift
            z=bite-sign*bite_relief(x,y)
            verts.append((x,y,z));uv.append((k/N,.83+.16*(1-radius)))
        for k in range(N): faces.append((previous+k,previous+(k+1)%N,current+(k+1)%N,current+k))
        previous=current
    shift=.22 if kind<2 else .11 if kind==2 else 0.
    end=len(verts); verts.append((0,shift,bite-sign*bite_relief(0,shift)));uv.append((.5,1))
    for k in range(N): faces.append((previous+k,previous+(k+1)%N,end))
    root=len(verts); verts.append((0,0,cerv+sign*.04));uv.append((.5,0))
    for k in range(N): faces.append((k,root,(k+1)%N))
    mesh=bpy.data.meshes.new(tooth['name']+'_mesh');mesh.from_pydata(verts,[],faces);mesh.update()
    obj=bpy.data.objects.new(tooth['name'],mesh);bpy.context.collection.objects.link(obj)
    # Geometry is rotated as one crown, preserving a separate named object.
    tx,ty=tooth['tangent']; nx,ny=tooth['normal']; cx,cy=tooth['center']
    tilt=tooth['variation']*cfg.get('tooth_tilt',.012)
    for v in mesh.vertices:
        x,y,z=v.co
        y+=tilt*(z-cerv)
        yaw=tooth['variation']*.012
        x,y=x*math.cos(yaw)-y*math.sin(yaw),x*math.sin(yaw)+y*math.cos(yaw)
        v.co=(cx+x*tx+y*nx,cy+x*ty+y*ny,z)
    mesh.materials.append(mat)
    uvl=mesh.uv_layers.new(name='CrownUV')
    for poly in mesh.polygons:
        poly.use_smooth=True
        for li in poly.loop_indices: uvl.data[li].uv=uv[mesh.loops[li].vertex_index]
    import bmesh
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
    obj['tooth']=True;obj['arch']='upper' if sign>0 else 'lower';obj['quadrant']=tooth['side'];obj['tooth_number']=kind+1;obj['crown_type']=KINDS[kind]
    if tooth.get('specialty'): obj['specialty']=tooth['specialty']
    return obj


def point_at(obj, point):
    obj.rotation_euler=(Vector(point)-obj.location).to_track_quat('-Z','Y').to_euler()


def area(name,location,power,color,size,target=(0,-1,0), shape='DISK', size_y=None):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.color=color;data.shape=shape;data.size=size
    if size_y is not None:data.size_y=size_y
    ob=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(ob);ob.location=location;point_at(ob,target)
    return ob


def build(cfg):
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    texture_files()
    enamel=material('Pearly enamel • microtexture',cfg.get('enamel_color',[.90,.86,.76]),rough=cfg.get('enamel_roughness',.19),normal_strength=cfg.get('enamel_normal',.45))
    accents={
        'coral':material('Translucent coral',(.96,.48,.59),.12,.13,.22),
        'sky_blue':material('Translucent sky blue',(.30,.72,.88),.12,.13,.22),
        'mint':material('Translucent mint',(.39,.80,.59),.12,.13,.22),
        'amber':material('Translucent amber',(.98,.59,.16),.12,.13,.22),
    }
    gingiva=material('Gingiva to satin lavender • continuous',(.94,.40,.48),gum=True,normal_strength=cfg.get('gum_normal',.8))
    all_teeth=[]
    for jaw in ['U','L']:
        upper=jaw=='U'; sign=1 if upper else -1
        arch=Arch(*(cfg.get('upper_arch',[2.72,3.80,0]) if upper else cfg.get('lower_arch',[2.54,3.55,.02])))
        widths=cfg.get('upper_widths',[.86,.70,.78,.72,.76,1.00,.96]) if upper else cfg.get('lower_widths',[.55,.60,.70,.73,.78,1.03,1.00])
        depths=[.65,.64,.76,.86,.91,1.02,1.01] if upper else [.56,.60,.71,.81,.87,1.00,.99]
        heights=cfg.get('upper_heights',[1.25,1.13,1.24,1.02,.97,.88,.84]) if upper else cfg.get('lower_heights',[1.07,1.08,1.12,.95,.93,.85,.81])
        teeth=[]
        for side in ['R','L']:
            cursor=.018
            for i,(w,d,h) in enumerate(zip(widths,depths,heights)):
                variation=math.sin((i+1)*7.29+(0 if side=='R' else 2.2))
                w*=1+.012*variation
                h*=1+.009*variation
                h*=cfg.get('crown_height_scale',1.0)
                s=(cursor+w*.5)*(1 if side=='L' else -1)
                cursor+=w+(cfg.get('molar_gap',.065) if i>=5 else cfg.get('tooth_gap',.035))
                c,t,n=arch.frame(s)
                # Anterior overbite is paired with anterior upper overjet.
                bite=(.07 if i<2 else .13 if i==2 else .13) if upper else (.145 if i<2 else .035 if i==2 else .0)
                bite+=cfg.get('upper_bite_shift',0) if upper else cfg.get('lower_bite_shift',0)
                cerv=bite+sign*h
                name=f'{jaw}_{side}_{i+1}_{KINDS[i]}'
                tooth=dict(name=name,index=i,w=w,d=d,h=h,s=s,sign_z=sign,cerv=cerv,center=c,tangent=t,normal=n,variation=variation,side=side)
                specialty={('U','R',0):'coral',('U','R',5):'sky_blue',('L','R',1):'mint',('L','L',0):'amber'}.get((jaw,side,i))
                if specialty:tooth['specialty']=specialty
                crown_mesh(tooth,accents[specialty] if specialty else enamel,cfg)
                teeth.append(tooth)
            arch.max_s=cursor+.16
        teeth.sort(key=lambda t:t['s'])
        gum_cfg=dict(cfg)
        gum_cfg['base_height']=cfg.get('upper_base_height',2.5) if upper else cfg.get('lower_base_height',2.3)
        gum_cfg['gum_height']=cfg.get('upper_gum_height',2.0) if upper else cfg.get('lower_gum_height',1.7)
        if not upper:gum_cfg['gum_collar_ratio']=cfg.get('lower_collar_ratio',.54)
        gum=build_gum(jaw,teeth,arch,gingiva,gum_cfg)
        if cfg.get('smooth_gum',False):
            bpy.context.view_layer.objects.active=gum
            mod=gum.modifiers.new('Smooth anatomical tissue','SUBSURF');mod.levels=1
            bpy.ops.object.modifier_apply(modifier=mod.name)
        gum['tissue']='continuous gingiva and jaw base'
        all_teeth+=teeth
    # Fit a closed bite while retaining a small real clearance. Opposing
    # cusps interdigitate instead of keeping the entire lower arch separated.
    bite_lift=cfg.get('occlusion_lift',0.0)
    if bite_lift:
        from mathutils.bvhtree import BVHTree
        upper_vertices=[];upper_triangles=[]
        for obj in bpy.context.scene.objects:
            if obj.get('tooth') and obj.get('arch')=='upper':
                offset=len(upper_vertices)
                upper_vertices.extend(v.co.copy() for v in obj.data.vertices)
                obj.data.calc_loop_triangles()
                upper_triangles.extend(tuple(offset+i for i in t.vertices) for t in obj.data.loop_triangles)
        opposing=BVHTree.FromPolygons(upper_vertices,upper_triangles,all_triangles=True)
        for obj in bpy.context.scene.objects:
            if obj.type!='MESH' or not obj.name.startswith('L_'):continue
            for v in obj.data.vertices:
                v.co.z+=bite_lift
                if obj.get('tooth') and v.co.z>-.15:
                    hit,_,_,_=opposing.ray_cast(Vector((v.co.x,v.co.y,-.4)),Vector((0,0,1)),3.0)
                    if hit is not None:v.co.z=min(v.co.z,hit.z-cfg.get('occlusion_clearance',.018))
            obj.data.update()
            if obj.get('tooth'):
                # Fit triangle interiors too: vertices outside the opposing
                # footprint can otherwise leave bridging faces intersecting.
                fitted=set()
                for fit_pass in range(48):
                    obj.data.calc_loop_triangles()
                    tris=[tuple(t.vertices) for t in obj.data.loop_triangles]
                    lower_tree=BVHTree.FromPolygons([v.co.copy() for v in obj.data.vertices],tris,all_triangles=True)
                    overlaps=lower_tree.overlap(opposing)
                    if not overlaps:break
                    affected={i for tri,_ in overlaps for i in tris[tri]}
                    for i in affected:obj.data.vertices[i].co.z-=.006
                    fitted.update(affected)
                    obj.data.update()
                else:raise RuntimeError('Occlusion fitting did not converge for '+obj.name)
                obj['occlusal_fitting_passes']=fit_pass
                obj['occlusal_fitted_vertices']=len(fitted)
    for obj in bpy.context.scene.objects:
        if obj.type=='MESH':
            for v in obj.data.vertices:
                v.co.x*=cfg.get('horizontal_scale',1.0);v.co.y*=cfg.get('horizontal_scale',1.0)
            if obj.get('tooth'):
                origin=sum((v.co for v in obj.data.vertices),Vector())/len(obj.data.vertices)
                for v in obj.data.vertices:v.co-=origin
                obj.location=origin
    scene=bpy.context.scene
    data=bpy.data.cameras.new('Reference camera 85mm');data.lens=85;data.sensor_width=36
    camera=bpy.data.objects.new('Reference camera 85mm',data);bpy.context.collection.objects.link(camera)
    target=Vector(cfg.get('camera_target',[0,-.9,0]))
    yaw=math.radians(cfg.get('camera_yaw',33)); pitch=math.radians(cfg.get('camera_pitch',5.0));distance=cfg.get('camera_distance',23.5)
    camera.location=target+distance*Vector((-math.sin(yaw)*math.cos(pitch),-math.cos(yaw)*math.cos(pitch),math.sin(pitch)))
    point_at(camera,target);scene.camera=camera
    area('Key • upper left softbox',cfg.get('key_location',[-5,-7,8]),cfg.get('key_power',1150),(1.0,.90,.86),cfg.get('key_size',3.0),shape='RECTANGLE',size_y=5)
    area('Cool rim • right',cfg.get('rim_location',[6,1,5]),cfg.get('rim_power',1500),(.72,.83,1.0),cfg.get('rim_size',4.0))
    area('Lavender fill',cfg.get('fill_location',[-3,-5,-2]),cfg.get('fill_power',650),(.91,.85,1.0),cfg.get('fill_size',5.0))
    scene.world.color=(.18,.18,.18)
    scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.65,.68,.8,1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=cfg.get('world_strength',.30)
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=24;scene.cycles.use_denoising=True
    scene.cycles.max_bounces=8;scene.cycles.transmission_bounces=6
    scene.render.threads_mode='FIXED';scene.render.threads=5
    scene.render.resolution_x=960;scene.render.resolution_y=540;scene.render.resolution_percentage=100
    scene.render.film_transparent=True
    scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.image_settings.color_depth='8'
    scene.view_settings.view_transform=cfg.get('view_transform','AgX');scene.view_settings.look=cfg.get('view_look','AgX - Medium High Contrast')
    scene.view_settings.exposure=cfg.get('exposure',.25)
    scene.render.use_file_extension=True
    scene['asset_description']='28 individually addressable crowns; continuous scalloped gums; lavender horseshoe bases'
    scene['accent_teeth']=', '.join(t['name']+':'+t['specialty'] for t in all_teeth if t.get('specialty'))
    scene['model_units']='1 Blender unit = 1 cm'
    scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.01
    return scene


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--iteration',type=int,default=1)
    parser.add_argument('--final',action='store_true')
    args=parser.parse_args()
    cfg=json.loads(args.config.read_text())
    scene=build(cfg)
    if args.final:
        scene.cycles.samples=cfg.get('final_samples',128)
        scene.cycles.use_adaptive_sampling=True
        scene.cycles.adaptive_threshold=.015
        scene.cycles.adaptive_min_samples=24
        scene.render.resolution_x=1920;scene.render.resolution_y=1080
        scene.render.filepath='//dental_arch.png'
        for image in bpy.data.images:
            if image.source=='FILE':image.pack()
        bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'dental_arch.blend'))
        bpy.ops.object.select_all(action='DESELECT')
        for obj in scene.objects:
            if obj.type=='MESH':obj.select_set(True)
        bpy.ops.export_scene.gltf(filepath=str(ROOT/'dental_arch.glb'),export_format='GLB',use_selection=True,export_apply=True,export_extras=True,export_cameras=False,export_lights=False,export_yup=True)
    else:
        scene.render.filepath=str(ROOT/'renders'/f'iter_{args.iteration:02d}.png')
        bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'working.blend'))
    bpy.ops.render.render(write_still=True)
    print('RENDER_COMPLETE',scene.render.filepath,flush=True)


if __name__=='__main__':main()
