import bpy, glob, mathutils
bpy.ops.wm.read_factory_settings(use_empty=True)
f = glob.glob("/scratch/texugo_3d/fbx/*.fbx")[0]
bpy.ops.import_scene.fbx(filepath=f)
print("=== OBJETOS")
for o in bpy.data.objects:
    print(o.type, o.name, "| pais:", o.parent.name if o.parent else None, "| escala", tuple(round(x,3) for x in o.scale), "| dim", tuple(round(x,3) for x in o.dimensions))
arms=[o for o in bpy.data.objects if o.type=="ARMATURE"]
print("=== ARMATURES:", len(arms))
for a in arms:
    bones=a.data.bones
    print(a.name, "ossos:", len(bones))
    print("  nomes:", [b.name for b in bones][:80])
meshes=[o for o in bpy.data.objects if o.type=="MESH"]
for m in meshes:
    me=m.data
    print("MALHA", m.name, "verts", len(me.vertices), "faces", len(me.polygons), "grupos de vertices:", len(m.vertex_groups), "| modificadores:", [x.type for x in m.modifiers], "| shape keys:", len(me.shape_keys.key_blocks) if me.shape_keys else 0, "| materiais:", [s.material.name if s.material else None for s in m.material_slots])
print("=== ANIMACOES:", [(a.name, [round(x) for x in a.frame_range]) for a in bpy.data.actions])
