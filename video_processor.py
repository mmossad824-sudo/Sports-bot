"""
video_processor.py — محرك معالجة وتجهيز فيديوهات الريلز والـ Shorts والتيك توك
يقوم بـ:
1. تحويل الفيديو من 16:9 إلى 9:16 (1080x1920) مناسب لـ Reels / Shorts / TikTok.
2. تطبيق خلفية مشوشة (Blurred canvas) من نفس الفيديو مع تكبير وتركيز اللقطة في المنتصف.
3. تسريع بسيط (1.03x) وتعديل التردد الصوتي (Pitch Shift) لتجاوز بصمة حقوق النشر (Copyright Content ID Bypass).
4. إضافة شريط هويّة بصريّة علوي وسفلي ينوه عن اسم قناتك ورابط موقعك.
"""

import os
import sys
import subprocess
import logging

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

FONT_PATH = os.path.join(os.path.dirname(__file__), "Cairo-Bold.ttf")

def process_video_for_shorts(input_path: str, output_path: str, title: str = "يلا شوت - أهداف المباراة", max_duration_sec: int = 58) -> bool:
    """
    Process input video file into a 9:16 vertical video optimized for YouTube Shorts, Facebook Reels, and TikTok.
    Applies copyright bypass filters and branding overlays.
    """
    if not os.path.exists(input_path):
        logger.error(f"Input video file not found: {input_path}")
        return False

    logger.info(f"Processing video for Shorts/Reels: {input_path} -> {output_path}")

    # FFmpeg Filter Complex:
    # 1. Split input stream into two: background layer and main foreground layer
    # 2. Background: Crop/scale to 1080x1920, apply boxblur=30:5 to create smooth gradient backdrop
    # 3. Main video: Scale to 1080 width, maintaining aspect ratio (1080x608)
    # 4. Overlay main video on top of blurred background at vertical center
    # 5. Speed up video & audio slightly (1.03x) to break automated video hash matching
    # 6. Add top and bottom text overlay banner for branding

    clean_title = title.replace(":", " ").replace("'", "").replace('"', '')

    filter_complex = (
        "[0:v]split=2[bg][fg];"
        "[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=50:5,eq=brightness=-0.1,setpts=PTS/1.09[bg_blurred];"
        # Nuclear evasion: flip, extreme color, add moving noise (static), shrink frame significantly
        "[fg]hflip,eq=contrast=1.3:brightness=0.04:saturation=1.5,noise=alls=10:allf=t+u,scale=950:-2,setpts=PTS/1.09[fg_scaled];"
        "[bg_blurred][fg_scaled]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2[base];"
        "[base]drawbox=y=0:color=black@0.9:width=iw:height=220:t=fill,"
        "drawbox=y=ih-220:color=black@0.9:width=iw:height=220:t=fill[v_boxed];"
        f"[v_boxed]drawtext=fontfile='{FONT_PATH}':text='YALLA SHOOT TODAY':fontsize=50:fontcolor=white:x=(w-text_w)/2:y=80,"
        f"drawtext=fontfile='{FONT_PATH}':text='yalla-shoot-today.vercel.app':fontsize=38:fontcolor=yellow:x=(w-text_w)/2:y=h-150[v_final]"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-filter_complex", filter_complex,
        "-map", "[v_final]",
        "-map", "0:a?",
        # Extreme audio evasion: pitch shift +12% and tempo adjustment for net speed ~1.06x
        "-af", "asetrate=44100*1.12,atempo=0.95,volume=1.5",
        "-t", str(max_duration_sec),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        output_path
    ]

    try:
        logger.info("Running FFmpeg video transformation command...")
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=300)
        if res.returncode == 0 and os.path.exists(output_path):
            logger.info(f"✅ Video successfully processed into 9:16 Shorts format: {output_path}")
            return True
        else:
            logger.error(f"FFmpeg failed with return code {res.returncode}: {res.stderr[:500]}")
            return _process_video_fallback(input_path, output_path, max_duration_sec)
    except Exception as e:
        logger.error(f"Exception during video processing: {e}")
        return _process_video_fallback(input_path, output_path, max_duration_sec)

def _process_video_fallback(input_path: str, output_path: str, max_duration_sec: int) -> bool:
    """Fallback FFmpeg processing without drawtext if font isn't loaded."""
    logger.info("Executing fallback FFmpeg transformation...")
    filter_complex = (
        "[0:v]split=2[bg][fg];"
        "[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=40:5,setpts=PTS/1.05[bg_blurred];"
        "[fg]hflip,eq=contrast=1.15:brightness=0.02:saturation=1.2,scale=1150:-1,crop=1080:608,setpts=PTS/1.05[fg_scaled];"
        "[bg_blurred][fg_scaled]overlay=0:(H-h)/2[v_final]"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-filter_complex", filter_complex,
        "-map", "[v_final]",
        "-map", "0:a?",
        "-af", "atempo=1.03",
        "-t", str(max_duration_sec),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "24",
        "-c:a", "aac",
        "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        output_path
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=300)
        return res.returncode == 0 and os.path.exists(output_path)
    except Exception as e:
        logger.error(f"Fallback processing error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python video_processor.py <input_video> <output_shorts_mp4> [title]")
        sys.exit(1)
    inp = sys.argv[1]
    out = sys.argv[2]
    ttl = sys.argv[3] if len(sys.argv) > 3 else "يلا شوت"
    success = process_video_for_shorts(inp, out, title=ttl)
    print("Success" if success else "Failed")
