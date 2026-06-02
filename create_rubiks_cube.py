"""
Rubik's Cube Generator for Blender
==================================
Creates a standard 3x3x3 Rubik's Cube with:
- 27 independent cubes, white plastic body + colored sticker faces
- PBR materials, three-point studio lighting, 45-degree camera
- Animation groundwork: 6 rotation axis empties, 24fps, frame 1

Usage:
    blender --background --python create_rubiks_cube.py
    Or run inside Blender Scripting workspace.

Output: Rubik's Cube.blend
"""

import bpy
import os
from math import radians

# ============================================================
# CONFIGURATION
# ============================================================

CUBE_SIZE = 0.92        # Cube body size (units)
SPACING = 1.0           # Center-to-center spacing
GAP = SPACING - CUBE_SIZE  # 0.08 total gap between cubes
OUTPUT_FILENAME = "Rubik's Cube.blend"
FPS = 24

# Rubik's Cube sticker colors — matched to reference video
# Video-detected values (Robust median of sampled pixels):
#   Red:    RGB(255,144, 74)  Blue:   RGB(  0,125,254)
#   Yellow: RGB(231,233, 42)  Green:  RGB( 21,218, 99)
#   White:  neutralized from cool-tinted video white
#   Orange: not visible in sampled frames — interpolated from scheme
COLORS = {
    "Red":    (1.000, 0.004, 0.004),   # #FF0101 — pure red
    "Orange": (1.000, 0.350, 0.020),   # vivid orange
    "Green":  (0.082, 0.855, 0.388),   # vivid green from video
    "Blue":   (0.000, 0.490, 0.996),   # electric blue from video
    "White":  (0.960, 0.960, 0.970),   # neutral cool white
    "Yellow": (0.906, 0.914, 0.165),   # lemon yellow from video
}

# Blender cube polygon indices → normal direction → Rubik's face
# Verified with Blender 5.1 cube normals:
#   Face 0: -X, Face 1: +Y, Face 2: +X, Face 3: -Y, Face 4: -Z, Face 5: +Z
FACE_MAP = [
    (0,  0, -1, "Orange"),   # -X → Left → Orange
    (1,  1,  1, "Green"),    # +Y → Front → Green
    (2,  0,  1, "Red"),      # +X → Right → Red
    (3,  1, -1, "Blue"),     # -Y → Back → Blue
    (4,  2, -1, "Yellow"),   # -Z → Bottom → Yellow
    (5,  2,  1, "White"),    # +Z → Top → White
]

CAMERA_POS = (5.0, 5.0, 5.0)  # Far enough that entire cube is always in frame

# ============================================================
# SCENE CLEANUP
# ============================================================

def clear_scene():
    """Remove all default objects, collections, and data blocks."""
    # Delete objects
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    # Delete collections except master
    for coll in list(bpy.data.collections):
        if coll.name not in ("Master Collection",):
            bpy.data.collections.remove(coll)
    # Delete data blocks
    for m in list(bpy.data.meshes):    bpy.data.meshes.remove(m)
    for m in list(bpy.data.materials): bpy.data.materials.remove(m)
    for l in list(bpy.data.lights):    bpy.data.lights.remove(l)
    for c in list(bpy.data.cameras):   bpy.data.cameras.remove(c)


# ============================================================
# MATERIALS
# ============================================================

def create_material(name, base_color, roughness, specular=0.0):
    """Create a PBR Principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    bsdf.inputs['Base Color'].default_value = (*base_color, 1.0)
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['Specular IOR Level'].default_value = specular

    output = nodes.new(type='ShaderNodeOutputMaterial')
    output.location = (300, 0)
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    return mat


def create_all_materials():
    """Create 7 materials: 1 white plastic body + 6 matte sticker colors."""
    mats = {}

    # Black plastic cube body — like real Rubik's cubes (hides interior faces)
    mats["M_Plastic"] = create_material(
        "M_Plastic", base_color=(0.080, 0.078, 0.075),
        roughness=0.35, specular=0.05,
    )

    # Sticker materials — fully matte
    for color_name in ("Red", "Orange", "Green", "Blue", "White", "Yellow"):
        mats[f"M_Sticker_{color_name}"] = create_material(
            f"M_Sticker_{color_name}", base_color=COLORS[color_name],
            roughness=0.60, specular=0.00,
        )

    return mats


# ============================================================
# CUBE CREATION (Sticker-based)
# ============================================================

def create_single_cube(i, j, k, materials):
    """
    Create one small cube at grid position (i, j, k).
    White plastic on all faces; exterior faces get a colored sticker material.
    """
    x, y, z = i * SPACING, j * SPACING, k * SPACING

    bpy.ops.mesh.primitive_cube_add(size=CUBE_SIZE, location=(x, y, z))
    obj = bpy.context.object
    obj.name = f"Cube_{i}_{j}_{k}"

    # Determine which faces are exterior
    grid_pos = [i, j, k]
    exterior_faces = {}  # face_idx → sticker_material_name

    for face_idx, axis, boundary_val, color_name in FACE_MAP:
        if grid_pos[axis] == boundary_val:
            exterior_faces[face_idx] = f"M_Sticker_{color_name}"

    # Build ordered material slot list
    slot_names = ["M_Plastic"]  # slot 0 = white plastic body
    sticker_to_slot = {}
    for face_idx in sorted(exterior_faces.keys()):
        mn = exterior_faces[face_idx]
        if mn not in sticker_to_slot:
            sticker_to_slot[mn] = len(slot_names)
            slot_names.append(mn)

    for sn in slot_names:
        obj.data.materials.append(materials[sn])

    # Assign material index per polygon (face)
    for face_idx in range(6):
        poly = obj.data.polygons[face_idx]
        if face_idx in exterior_faces:
            poly.material_index = sticker_to_slot[exterior_faces[face_idx]]
        else:
            poly.material_index = 0  # white plastic

    # Sharp edges (no smooth shading)
    for poly in obj.data.polygons:
        poly.use_smooth = False

    return obj


# ============================================================
# ANIMATION GROUNDWORK — Rotation Axis Empties
# ============================================================

def create_rotation_empties(coll):
    """
    Create 6 empty axes at origin for Rubik's cube rotation layers.
    These serve as animation pivots for R, L, U, D, F, B rotations.
    """
    axes = {}
    configs = [
        # (name, rotation for visual alignment, which axis)
        ("Empty_R", (0, 0, 0), "X"),    # Right  face: +X
        ("Empty_L", (0, 0, 0), "X"),    # Left   face: -X
        ("Empty_U", (0, 0, 0), "Z"),    # Up     face: +Z
        ("Empty_D", (0, 0, 0), "Z"),    # Down   face: -Z
        ("Empty_F", (0, 0, 0), "Y"),    # Front  face: +Y
        ("Empty_B", (0, 0, 0), "Y"),    # Back   face: -Y
    ]

    for name, rot, axis in configs:
        bpy.ops.object.empty_add(type='ARROWS', location=(0, 0, 0))
        empty = bpy.context.object
        empty.name = name
        empty.rotation_euler = rot
        empty.empty_display_size = 1.8
        empty.hide_viewport = True   # hidden by default, visible when animating
        empty.hide_render = True

        # Store axis info as custom property for animation reference
        empty["rotation_axis"] = axis

        # Move to collection
        for c in list(empty.users_collection):
            c.objects.unlink(empty)
        coll.objects.link(empty)

        axes[name] = empty

    return axes


# ============================================================
# LIGHTING
# ============================================================

def create_lighting(coll):
    """Create three-point studio area lights."""
    configs = [
        {
            "name": "Light_Key", "location": (-2, -4, 6),
            "rotation": (radians(60), radians(5), radians(-45)),
            "energy": 250, "size": 3.0,
            "color": (1.0, 0.973, 0.906),  # warm
        },
        {
            "name": "Light_Fill", "location": (4, 2, 3),
            "rotation": (radians(35), radians(10), radians(60)),
            "energy": 120, "size": 2.5,
            "color": (0.910, 0.941, 1.0),  # cool
        },
        {
            "name": "Light_Rim", "location": (0, 4, 5),
            "rotation": (radians(75), 0, radians(180)),
            "energy": 180, "size": 2.0,
            "color": (1.0, 1.0, 1.0),  # neutral
        },
    ]

    lights = []
    for cfg in configs:
        bpy.ops.object.light_add(type='AREA', location=cfg["location"])
        light = bpy.context.object
        light.name = cfg["name"]
        light.data.energy = cfg["energy"]
        light.data.size = cfg["size"]
        light.data.color = cfg["color"]
        light.rotation_euler = cfg["rotation"]

        for c in list(light.users_collection):
            c.objects.unlink(light)
        coll.objects.link(light)
        lights.append(light)

    return lights


# ============================================================
# STUDIO FLOOR
# ============================================================

def create_studio_floor(coll):
    """Create a large floor plane as studio backdrop."""
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, -2.2))
    floor = bpy.context.object
    floor.name = "Studio_Floor"

    mat = create_material("M_Floor", base_color=(0.40, 0.40, 0.42),
                          roughness=0.85, specular=0.00)
    floor.data.materials.append(mat)

    for c in list(floor.users_collection):
        c.objects.unlink(floor)
    coll.objects.link(floor)

    return floor


# ============================================================
# CAMERA
# ============================================================

def setup_camera(coll):
    """Create camera at ~45°, tracking the cube center."""
    bpy.ops.object.camera_add(location=CAMERA_POS)
    cam = bpy.context.object
    cam.name = "Camera_Main"
    cam.data.lens = 50

    track = cam.constraints.new(type='TRACK_TO')
    track.target = bpy.data.objects.get("Rubiks_Cube_Root")
    track.track_axis = 'TRACK_NEGATIVE_Z'
    track.up_axis = 'UP_Y'

    bpy.context.scene.camera = cam

    for c in list(cam.users_collection):
        c.objects.unlink(cam)
    coll.objects.link(cam)

    return cam


# ============================================================
# WORLD / BACKGROUND
# ============================================================

def setup_world():
    """Studio background with medium gray for contrast."""
    world = bpy.context.scene.world
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()

    bg = nodes.new(type='ShaderNodeBackground')
    bg.location = (0, 0)
    bg.inputs['Color'].default_value = (0.45, 0.45, 0.48, 1.0)
    bg.inputs['Strength'].default_value = 0.8

    output = nodes.new(type='ShaderNodeOutputWorld')
    output.location = (300, 0)
    links.new(bg.outputs['Background'], output.inputs['Surface'])


# ============================================================
# RENDER & ANIMATION SETTINGS
# ============================================================

def setup_scene_settings():
    """Configure render, frame rate, and animation settings."""
    scene = bpy.context.scene

    # Frame rate
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = 480   # 20 seconds × 24 fps

    # Render engine
    scene.render.engine = 'CYCLES'
    try:
        scene.cycles.device = 'GPU'
    except Exception:
        scene.cycles.device = 'CPU'

    scene.cycles.samples = 256
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = 'OPENIMAGEDENOISE'

    # Resolution
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1920
    scene.render.resolution_percentage = 100

    # Color management
    scene.view_settings.view_transform = 'Filmic'
    scene.view_settings.look = 'Medium High Contrast'

    # Output
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("  Rubik's Cube Generator — Sticker Model + Animation Prep")
    print("=" * 60)

    # 1. Clean slate
    print("\n[1/9] Clearing scene...")
    clear_scene()

    # 2. Materials
    print("[2/9] Creating PBR materials (1 plastic + 6 stickers)...")
    materials = create_all_materials()

    # 3. Collection
    print("[3/9] Creating collection...")
    coll = bpy.data.collections.new("Rubiks_Cube")
    bpy.context.scene.collection.children.link(coll)

    # Root empty
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, 0, 0))
    root = bpy.context.object
    root.name = "Rubiks_Cube_Root"
    for c in list(root.users_collection):
        c.objects.unlink(root)
    coll.objects.link(root)

    # 4. 27 cubes
    print("[4/9] Creating 27 sticker-based cubes...")
    cubes = []
    for i in (-1, 0, 1):
        for j in (-1, 0, 1):
            for k in (-1, 0, 1):
                cube = create_single_cube(i, j, k, materials)
                for c in list(cube.users_collection):
                    c.objects.unlink(cube)
                coll.objects.link(cube)
                cube.parent = root
                cubes.append(cube)
            pct = len(cubes) / 27 * 100
            print(f"  ... {len(cubes)}/27 ({pct:.0f}%)")

    # 5. Animation rotation empties
    print("[5/9] Creating 6 rotation axis empties...")
    axes = create_rotation_empties(coll)

    # 6. Lighting
    print("[6/9] Creating three-point lighting...")
    create_lighting(coll)

    # 7. Floor
    print("[7/9] Creating studio floor...")
    create_studio_floor(coll)

    # 8. Camera
    print("[8/9] Setting up camera (45°, tracking cube)...")
    setup_camera(coll)

    # 9. Scene settings
    print("[9/9] Configuring render + animation settings...")
    setup_world()
    setup_scene_settings()

    # Save
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, OUTPUT_FILENAME)
    bpy.ops.wm.save_as_mainfile(filepath=output_path)

    print(f"\n{'=' * 60}")
    print(f"  ✓ Saved: {output_path}")
    print(f"  ✓ {len(cubes)} sticker-based cubes (plastic body + colored faces)")
    print(f"  ✓ 6 rotation axis empties (R/L/U/D/F/B) for animation")
    print(f"  ✓ {FPS} fps | frame 1–480 | Cycles 256 samples")
    print(f"  ✓ 7 materials | 3 lights | 1 camera")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
