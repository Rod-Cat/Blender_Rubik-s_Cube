"""
Rubik's Cube Animation Generator
=================================
30s @ 24fps (720 frames):
  Stage 1 ( 0-5s,  f1-120):   Solved, camera orbit 120°
  Stage 2 ( 6-15s, f121-360):  Scramble 24 moves × 0.4s (10f)
  Pause   (16-17s, f361-408):  Solved pause, camera orbit 48°
  Stage 3 (18-27s, f409-648):  Solve 24 moves × 0.4s (10f)
  Stage 4 (28-30s, f649-720):  Solved, camera orbit 72°

Quaternion rotation + continuous camera orbit.
"""

import bpy, os, random, math
from mathutils import Matrix, Quaternion, Vector
from math import radians

# ============================================================
# CONFIG
# ============================================================

FPS = 24
MOVE_DURATION = 10        # 0.4s per move (10 frames)
SCRAMBLE_MOVES = 24

STAGE1_END  = 120         # 0-5s
STAGE2_END  = 360         # 6-15s (120 + 24×10)
PAUSE_END   = 408         # 16-17s (360 + 48)
STAGE3_END  = 648         # 18-27s (408 + 24×10)
STAGE4_END  = 720         # 28-30s (648 + 72)

OUTPUT_FILENAME = "Rubik's Cube.blend"

AXIS_X = Vector((1, 0, 0)); AXIS_Y = Vector((0, 1, 0)); AXIS_Z = Vector((0, 0, 1))

MOVE_DEFS = {
    'R':  (AXIS_X,  radians(90),  0, 1),   "R'": (AXIS_X,  radians(-90), 0, 1),
    'R2': (AXIS_X,  radians(180), 0, 1),
    'L':  (AXIS_X,  radians(-90), 0, -1),  "L'": (AXIS_X,  radians(90),  0, -1),
    'L2': (AXIS_X,  radians(180), 0, -1),
    'U':  (AXIS_Z,  radians(90),  2, 1),   "U'": (AXIS_Z,  radians(-90), 2, 1),
    'U2': (AXIS_Z,  radians(180), 2, 1),
    'D':  (AXIS_Z,  radians(-90), 2, -1),  "D'": (AXIS_Z,  radians(90),  2, -1),
    'D2': (AXIS_Z,  radians(180), 2, -1),
    'F':  (AXIS_Y,  radians(90),  1, 1),   "F'": (AXIS_Y,  radians(-90), 1, 1),
    'F2': (AXIS_Y,  radians(180), 1, 1),
    'B':  (AXIS_Y,  radians(-90), 1, -1),  "B'": (AXIS_Y,  radians(90),  1, -1),
    'B2': (AXIS_Y,  radians(180), 1, -1),
}


# ============================================================
# HELPERS
# ============================================================

def get_cubes():
    return sorted([o for o in bpy.data.objects if o.name.startswith('Cube_')],
                  key=lambda o: o.name)


def get_layer(axis_idx, sign):
    t = 0.4
    return [o for o in get_cubes()
            if (sign > 0 and o.location[axis_idx] > t) or
               (sign < 0 and o.location[axis_idx] < -t)]


def rotate_point(point, axis, angle):
    return Matrix.Rotation(angle, 4, axis) @ point


def quat_rotate(quat, axis, angle):
    return Quaternion(axis, angle) @ quat


def reverse_move(move):
    if move.endswith("'"):  return move[:-1]
    elif move.endswith('2'): return move
    else:                    return move + "'"


# ============================================================
# ANIMATION
# ============================================================

def animate_move(move_name, start_frame, duration):
    if move_name not in MOVE_DEFS: return start_frame + duration
    axis_vec, angle, axis_idx, sign = MOVE_DEFS[move_name]
    end_frame = start_frame + duration
    layer = get_layer(axis_idx, sign)
    if not layer: return end_frame

    for cube in layer:
        ol, oq = cube.location.copy(), cube.rotation_quaternion.copy()
        cube.keyframe_insert(data_path='location', frame=start_frame)
        cube.keyframe_insert(data_path='rotation_quaternion', frame=start_frame)
        cube.location = rotate_point(ol, axis_vec, angle)
        cube.rotation_quaternion = quat_rotate(oq, axis_vec, angle)
        cube.keyframe_insert(data_path='location', frame=end_frame)
        cube.keyframe_insert(data_path='rotation_quaternion', frame=end_frame)
    return end_frame


def animate_move_sequence(moves, start_frame, duration, label=""):
    cf = start_frame
    for i, move in enumerate(moves):
        cf = animate_move(move, cf, duration)
        if (i + 1) % 8 == 0:
            print(f"  ... {i+1}/{len(moves)} (frame {cf})")
    return cf


def orbit_camera(start_frame, end_frame, angle):
    """Orbit camera around Z axis."""
    cam = bpy.data.objects.get('Camera_Main')
    if not cam: return
    sl = cam.location.copy()
    el = Matrix.Rotation(radians(angle), 4, 'Z') @ sl
    cam.location = sl
    cam.keyframe_insert(data_path='location', frame=start_frame)
    cam.location = el
    cam.keyframe_insert(data_path='location', frame=end_frame)


# ============================================================
# SETUP
# ============================================================

def setup():
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, STAGE4_END
    scene.render.fps = FPS
    for obj in bpy.data.objects:
        if obj.animation_data: obj.animation_data_clear()
    for obj in get_cubes():
        obj.rotation_mode = 'QUATERNION'
    print(f"Setup: {FPS}fps, {STAGE4_END}f ({STAGE4_END/FPS:.0f}s)")


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("  Rubik's Cube — 30s Animation")
    print("=" * 60)
    setup()

    # Scramble
    random.seed(42)
    faces = ['R', 'L', 'U', 'D', 'F', 'B']
    modifiers = ['', "'"]
    scramble, last = [], None
    for _ in range(SCRAMBLE_MOVES):
        f = random.choice([x for x in faces if x != last])
        scramble.append(f + random.choice(modifiers))
        last = f
    solve = [reverse_move(m) for m in reversed(scramble)]

    print(f"\nScramble: {' → '.join(scramble)}")
    print(f"Solve:    {' → '.join(solve)}")
    print(f"\nTimeline: 1-{STAGE1_END} | {STAGE1_END+1}-{STAGE2_END} | "
          f"{STAGE2_END+1}-{PAUSE_END} | {PAUSE_END+1}-{STAGE3_END} | "
          f"{STAGE3_END+1}-{STAGE4_END}")

    # Stage 1 (0-5s): Solved, orbit 120°
    print("\n--- Stage 1: Solved + Orbit 120° (0-5s) ---")
    orbit_camera(1, STAGE1_END, angle=120)

    # Stage 2 (6-15s): Scramble 24×10f
    print(f"\n--- Stage 2: Scramble 24×{MOVE_DURATION}f (6-15s) ---")
    cf = animate_move_sequence(scramble, STAGE1_END, MOVE_DURATION)
    orbit_camera(STAGE1_END, STAGE2_END, angle=48)

    # Pause (16-17s): Solved pause, orbit 48°
    print(f"\n--- Pause: Solved + Orbit 48° (16-17s) ---")
    orbit_camera(STAGE2_END, PAUSE_END, angle=48)

    # Stage 3 (18-27s): Solve 24×10f
    print(f"\n--- Stage 3: Solve 24×{MOVE_DURATION}f (18-27s) ---")
    cf = animate_move_sequence(solve, PAUSE_END, MOVE_DURATION)
    orbit_camera(PAUSE_END, STAGE3_END, angle=48)

    # Stage 4 (28-30s): Solved, orbit 72°
    print(f"\n--- Stage 4: Solved + Orbit 72° (28-30s) ---")
    orbit_camera(STAGE3_END, STAGE4_END, angle=72)

    bpy.context.scene.frame_set(1)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(script_dir, OUTPUT_FILENAME))

    print(f"\n{'=' * 60}")
    print(f"  ✓ {STAGE4_END}f @ {FPS}fps = {STAGE4_END/FPS:.0f}s")
    print(f"  ✓ {len(scramble)}+{len(solve)} moves | Camera 288° orbit")
    print(f"  ✓ Quaternion | {OUTPUT_FILENAME}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
