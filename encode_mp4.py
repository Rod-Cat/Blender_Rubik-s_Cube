"""
Encode rendered PNG sequence to MP4 using Blender's VSE + FFMPEG.
Run after render completes:
  blender --background --python encode_mp4.py
"""

import bpy, os, glob

FRAMES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "render_output")
OUTPUT_PATH = os.path.join(FRAMES_DIR, "Rubiks_Cube_Animation.mp4")

# Clear default scene
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = 720
bpy.context.scene.render.fps = 24

# Switch to Video Editing workspace
if not bpy.context.scene.sequence_editor:
    bpy.context.scene.sequence_editor_create()

seq = bpy.context.scene.sequence_editor

# Add image sequence
png_files = sorted(glob.glob(os.path.join(FRAMES_DIR, "frame_*.png")))
if not png_files:
    print("ERROR: No PNG files found!")
    exit(1)

print(f"Found {len(png_files)} PNG frames")

# Add image strip
img_strip = seq.sequences.new_image(
    name="RubiksCube",
    filepath=png_files[0],
    channel=1,
    frame_start=1,
)

# Set the strip to use the image sequence
img_strip.frame_final_duration = len(png_files)

# Output settings
scene = bpy.context.scene
scene.render.resolution_x = 1080
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100

# MP4 output via FFMPEG
scene.render.image_settings.file_format = 'FFMPEG'
scene.render.ffmpeg.format = 'MPEG4'
scene.render.ffmpeg.codec = 'H264'
scene.render.ffmpeg.constant_rate_factor = 'MEDIUM'
scene.render.ffmpeg.ffmpeg_preset = 'GOOD'
scene.render.ffmpeg.audio_codec = 'NONE'

scene.render.filepath = OUTPUT_PATH
scene.frame_start = 1
scene.frame_end = len(png_files)

print(f"Encoding {len(png_files)} frames to MP4...")
print(f"Output: {OUTPUT_PATH}")

bpy.ops.render.render(animation=True, write_still=True)

print("\nENCODE COMPLETE!")
print(f"File: {OUTPUT_PATH}")
