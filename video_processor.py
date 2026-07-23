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

def process_video_for_shorts(input_path: str, output_path: str, title: str = "يلا شوت - أهداف المباراة", max_duration_sec: int = 58, platform: str = "facebook") -> bool:
    """
    Process input video file into a 9:16 vertical video optimized for YouTube Shorts, Facebook Reels, and TikTok.
    Applies copyright bypass filters and branding overlays based on platform.
    """
    if not os.path.exists(input_path):
        logger.error(f"Input video file not found: {input_path}")
        return False

    logger.info(f"Processing video for {platform}: {input_path} -> {output_path}")

    clean_title = title.replace(":", " ").replace("'", "").replace('"', '')

    if platform == "youtube":
        # YouTube PiP (Picture-in-Picture) evasion: heavy blur bg, tiny scaled foreground placed in the top right corner
        fg_filter = "[fg]fps=20,hflip,eq=contrast=1.2:brightness=0.05,scale=400:-2,setpts=PTS/1.12[fg_scaled]"
        overlay_cmd = "[bg_blurred][fg_scaled]overlay=main_w-overlay_w-30:250[base]"
        audio_filter = "atempo=1.12,asetrate=44100*1.15,aresample=44100,chorus=0.5:0.9:50|60:0.4|0.32:0.25|0.4:2|2.3,volume=1.5"
    else:
        # Facebook Nuclear evasion: slight flip, extreme color, static noise, centered large shrink
        fg_filter = "[fg]hflip,eq=contrast=1.3:brightness=0.04:saturation=1.5,noise=alls=10:allf=t+u,scale=950:-2,setpts=PTS/1.09[fg_scaled]"
        overlay_cmd = "[bg_blurred][fg_scaled]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2[base]"
        audio_filter = "atempo=1.09,asetrate=44100*1.12,aresample=44100,volume=1.3"

    filter_complex = (
        "[0:v]split=2[bg][fg];"
        "[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=50:5,eq=brightness=-0.1,setpts=PTS/1.09[bg_blurred];"
        f"{fg_filter};"
        f"{overlay_cmd};"
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
        "-af", audio_filter,
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
            logger.info(f"✅ Video successfully processed into 9:16 format: {output_path}")
            return True
        else:
            logger.error(f"FFmpeg failed with return code {res.returncode}: {res.stderr[:500]}")
            return False
    except Exception as e:
        logger.error(f"Exception during video processing: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python video_processor.py <input_video> <output_shorts_mp4> [title] [platform]")
        sys.exit(1)
    inp = sys.argv[1]
    out = sys.argv[2]
    ttl = sys.argv[3] if len(sys.argv) > 3 else "يلا شوت"
    plat = sys.argv[4] if len(sys.argv) > 4 else "facebook"
    success = process_video_for_shorts(inp, out, title=ttl, platform=plat)
    print("Success" if success else "Failed")
