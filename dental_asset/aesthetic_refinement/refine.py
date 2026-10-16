"""Refine the supplied GLB. Run with Blender Python: refine.py [before|after]."""
import bpy, math, sys, json, hashlib
from pathlib import Path
from mathutils import Vector, Matrix
ROOT=Path(__file__).resolve().parent
CONFIG = {'horizontal_scale': 1.12}
MODE=sys.argv[-1] if sys.argv[-1] in ('before','after') else 'after'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'oral-cavity-main.glb'))
s=bpy.context.scene
cube=bpy.data.objects.get('Cube')
if cube:bpy.data.objects.remove(cube,do_unlink=True)
meshes=[o for o in s.objects if o.type=='MESH']
teeth=[o for o in meshes if o.name not in ('U_gum','L_gum','U_base','L_base')]
def digest(o):return hashlib.sha256(repr([(tuple(v.co)) for v in o.data.vertices]).encode()).hexdigest()
before={o.name:digest(o) for o in teeth}
def linear(x):return x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4
def mat(name,color,rough,coat,trans=0,sss=0):
 m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=tuple(linear(c) for c in color)+(1,)
 p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=m.diffuse_color
 for k,v in {'Roughness':rough,'Coat Weight':coat,'Coat Roughness':.15,'Transmission Weight':trans,'Subsurface Weight':sss,'Subsurface Scale':.055,'IOR':1.46}.items():p.inputs[k].default_value=v
 return m
if MODE=='after':
 enamel=mat('Warm pearlescent enamel',(.96,.935,.88),.19,.45,.035,.10)
 gum=mat('Soft rose gingiva',(.80,.39,.46),.29,.22,0,.14)
 base=mat('Satin lavender porcelain',(.67,.62,.83),.34,.25,0,.035)
 accents={'U_R_1_central':('coral',(.95,.66,.71)), 'U_R_6_molar1':('sky_blue',(.54,.79,.9)), 'L_R_2_lateral':('mint',(.62,.84,.73)), 'L_L_1_central':('amber',(.96,.78,.43))}
 for o in meshes:
  if o.name.endswith('_gum') or o.name.endswith('_base'):
   # Compact only rootward tissue; collars and all crown coordinates stay fixed.
   sign=1 if o.name.startswith('U') else -1;anchor=1.46 if sign==1 else .99
   inv=o.matrix_world.inverted()
   for v in o.data.vertices:
    p=o.matrix_world@v.co;h=sign*p.z-anchor
    if h>0:p.z=sign*(anchor+h*.64)
    v.co=inv@p
   material=gum if o.name.endswith('_gum') else base
  else:
   material=enamel
   o['tooth']=True
   if o.name in accents:
    label,c=accents[o.name];material=mat('Pastel '+label,c,.24,.42,.13,.08);o['specialty']=label
  o.data.materials.clear();o.data.materials.append(material)
  for f in o.data.polygons:f.use_smooth=True
 # Low-amplitude procedural microtexture in Blender. GLB keeps portable PBR values.
 for m in (gum,enamel):
  nodes=m.node_tree.nodes;links=m.node_tree.links
  noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=145;noise.inputs['Detail'].default_value=2
  bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.12;bump.inputs['Distance'].default_value=.008 if m==gum else .003
  links.new(noise.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],nodes.get('Principled BSDF').inputs['Normal'])
# Apply one common lateral stretch so tooth contacts and gum alignment stay together.
if MODE=='after':
 stretch=Matrix.Diagonal((CONFIG['horizontal_scale'],1.0,1.0,1.0))
 for o in meshes:
  o.data.transform(o.matrix_world.inverted() @ stretch @ o.matrix_world)
  o.data.update()
def aim(o,pt):o.rotation_euler=(Vector(pt)-o.location).to_track_quat('-Z','Y').to_euler()
target=Vector((0,-1.9,.20))
bpy.ops.object.camera_add(location=target+Vector((-10.7,-19.0,2.6))*.90)
cam=bpy.context.object;cam.name='Aesthetic presentation 85mm';cam.data.lens=65;aim(cam,target);s.camera=cam
# 85 mm lens with proportionate pullback retains framing.
cam.location=target+(cam.location-target)*(85/65);cam.data.lens=85
for name,pos,power,size,color in [('Key softbox',(-6,-10,9),1500,4.5,(1,.91,.84)),('Cool edge',(6,1,7),1800,5,(.78,.84,1)),('Front fill',(4,-10,1),650,6,(1,.90,.95))]:
 bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;o.name=name;o.data.energy=power;o.data.shape='DISK';o.data.size=size;o.data.color=color;aim(o,target)
s.world=bpy.data.worlds.new('Soft studio');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs[0].default_value=(.23,.26,.34,1);s.world.node_tree.nodes['Background'].inputs[1].default_value=.4
s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=True;s.render.threads_mode='FIXED';s.render.threads=5
s.render.resolution_x=960;s.render.resolution_y=720;s.render.resolution_percentage=100;s.render.film_transparent=True
s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast';s.view_settings.exposure=.6
s.render.image_settings.file_format='PNG';s.render.filepath=str(ROOT/(MODE+'.png'))
if MODE=='after':
 bpy.ops.object.select_all(action='DESELECT')
 for o in meshes:o.select_set(True)
 bpy.ops.export_scene.gltf(filepath=str(ROOT/'oral-cavity-aesthetic.glb'),export_format='GLB',use_selection=True,export_extras=True,export_apply=True)
 s.cycles.samples=64;s.render.resolution_x=1600;s.render.resolution_y=1200
 bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'oral-cavity-aesthetic.blend'))
 s.cycles.samples=24;s.render.resolution_x=960;s.render.resolution_y=720
 triangles=0
 for o in meshes:o.data.calc_loop_triangles();triangles+=len(o.data.loop_triangles)
 (ROOT/'validation.json').write_text(json.dumps({'tooth_count':len(teeth),'mesh_count':len(meshes),'triangles':triangles,'horizontal_scale':CONFIG['horizontal_scale'],'tooth_change':'Common lateral stretch; no independent tooth reshaping or repositioning','accents':accents,'removed_unrelated_default_cube':True,'scope':'Aesthetic refinement; prior hidden socket intersections were not repaired.'},indent=2))
bpy.ops.render.render(write_still=True)
