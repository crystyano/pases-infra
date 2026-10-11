import bpy, glob, math, mathutils, sys
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=glob.glob("/scratch/texugo_3d/fbx/*.fbx")[0])
arm=[o for o in bpy.data.objects if o.type=="ARMATURE"][0]; mesh=[o for o in bpy.data.objects if o.type=="MESH"][0]
# materiais e texturas
for s in mesh.material_slots:
    m=s.material; imgs=[n.image.name for n in m.node_tree.nodes if n.type=="TEX_IMAGE" and n.image] if m and m.use_nodes else []
    print("MATERIAL", m.name if m else None, "texturas:", imgs)
acoes={a.name:a for a in bpy.data.actions}
def pose(nome, frame):
    arm.animation_data_create(); arm.animation_data.action=acoes[nome]; bpy.context.scene.frame_set(frame)
# cena
sc=bpy.context.scene; sc.render.engine="CYCLES"; sc.cycles.device="GPU"; sc.cycles.samples=48; sc.cycles.use_denoising=True
sc.render.resolution_x=720; sc.render.resolution_y=1280
prefs=bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type="OPTIX"; prefs.get_devices()
for d in prefs.devices: d.use = ("5060" in d.name)
print("GPUs usadas:", [d.name for d in prefs.devices if d.use])
w=bpy.data.worlds.new("w"); sc.world=w; w.use_nodes=True; bg=w.node_tree.nodes["Background"]; bg.inputs[0].default_value=(0.45,0.65,0.95,1); bg.inputs[1].default_value=1.0
bpy.ops.mesh.primitive_plane_add(size=40, location=(0,0,0)); ch=bpy.context.object
mat=bpy.data.materials.new("chao"); mat.use_nodes=True; mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=(0.72,0.52,0.30,1); mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value=0.95; ch.data.materials.append(mat)
sun=bpy.data.lights.new("sol","SUN"); sun.energy=4.0; so=bpy.data.objects.new("sol",sun); sc.collection.objects.link(so); so.rotation_euler=(math.radians(50),0,math.radians(35))
cam=bpy.data.cameras.new("cam"); cam.lens=45; co=bpy.data.objects.new("cam",cam); sc.collection.objects.link(co); sc.camera=co
def render(saida, nome_acao, frame, cam_pos):
    pose(nome_acao, frame)
    co.location=cam_pos; d=mathutils.Vector((0,0,0.38))-mathutils.Vector(cam_pos); co.rotation_euler=d.to_track_quat("-Z","Y").to_euler()
    sc.render.filepath=saida; bpy.ops.render.render(write_still=True)
render("/scratch/texugo_3d/teste_angry_frente.png","Armature|angry_01",40,(0,-2.4,0.55))
render("/scratch/texugo_3d/teste_angry_costas.png","Armature|angry_01",40,(0,2.4,0.55))
render("/scratch/texugo_3d/teste_run.png","Armature|run",8,(2.2,-1.6,0.55))
