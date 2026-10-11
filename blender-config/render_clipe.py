import bpy, glob, math, mathutils
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=glob.glob("/scratch/texugo_3d/fbx/*.fbx")[0])
arm=[o for o in bpy.data.objects if o.type=="ARMATURE"][0]
acao=[a for a in bpy.data.actions if a.name=="Armature|angry_01"][0]; arm.animation_data_create(); arm.animation_data.action=acao
sc=bpy.context.scene; sc.render.engine="CYCLES"; sc.cycles.device="GPU"; sc.cycles.samples=32; sc.cycles.use_denoising=True
sc.render.resolution_x=720; sc.render.resolution_y=1280; sc.render.fps=24
prefs=bpy.context.preferences.addons["cycles"].preferences; prefs.compute_device_type="OPTIX"; prefs.get_devices()
for d in prefs.devices: d.use=("5060" in d.name)
w=bpy.data.worlds.new("w"); sc.world=w; w.use_nodes=True; bg=w.node_tree.nodes["Background"]; bg.inputs[0].default_value=(0.45,0.65,0.95,1); bg.inputs[1].default_value=1.0
bpy.ops.mesh.primitive_plane_add(size=40, location=(0,0,0)); ch=bpy.context.object
mat=bpy.data.materials.new("chao"); mat.use_nodes=True; mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=(0.72,0.52,0.30,1); mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value=0.95; ch.data.materials.append(mat)
sun=bpy.data.lights.new("sol","SUN"); sun.energy=4.0; so=bpy.data.objects.new("sol",sun); sc.collection.objects.link(so); so.rotation_euler=(math.radians(50),0,math.radians(35))
cam=bpy.data.cameras.new("cam"); cam.lens=45; co=bpy.data.objects.new("cam",cam); sc.collection.objects.link(co); sc.camera=co
co.location=(0,-2.4,0.55); d=mathutils.Vector((0,0,0.38))-mathutils.Vector(co.location); co.rotation_euler=d.to_track_quat("-Z","Y").to_euler()
f0,f1=int(acao.frame_range[0]),int(acao.frame_range[1]); print("FRAMES",f0,f1,"fps original FBX:",bpy.context.scene.render.fps_base)
sc.frame_start=f0; sc.frame_end=f1; sc.render.image_settings.file_format="PNG"; sc.render.filepath="/scratch/texugo_3d/frames_angry/f_"
bpy.ops.render.render(animation=True)
