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
RAIN_OVERLAY_PATH = os.path.join(os.path.dirname(__file__), "rain_overlay.mp4")

def process_video_for_shorts(input_path: str, output_path: str, title: str = "يلا شوت - أهداف المباراة", max_duration_sec: int = 58, platform: str = "facebook", layout: str = "vertical") -> bool:
    """
    Process input video file into a 9:16 vertical video optimized for YouTube Shorts, Facebook Reels, and TikTok.
    Applies copyright bypass filters and branding overlays based on platform.
    """
    if not os.path.exists(input_path):
        logger.error(f"Input video file not found: {input_path}")
        return False

    logger.info(f"Processing video for {platform}: {input_path} -> {output_path}")

    clean_title = title.replace(":", " ").replace("'", "").replace('"', '')

    audio_filter = "atempo=1.18,asetrate=44100*1.08,aresample=44100,volume=1.5"
    
    if layout == "horizontal":
        # 16:9 Full screen evasion (no blurred background, just rain and slight zoom/speedup)
        # We scale rain to match the input video size
        filter_complex = (
            "[0:v]scale=1280:720,setpts=PTS/1.18[base];"
            "[1:v]format=yuva420p,colorkey=black:0.1:0.0,colorchannelmixer=aa=0.15,scale=1280:720[rain_alpha];"
            "[base][rain_alpha]overlay=shortest=1[v_boxed];"
            f"[v_boxed]drawtext=fontfile='{FONT_PATH}':text='{clean_title}':fontsize=40:fontcolor=yellow:x=(w-text_w)/2:y=30,"
            f"drawtext=fontfile='{FONT_PATH}':text='yalla-shoot-today.vercel.app':fontsize=30:fontcolor=white:x=(w-text_w)/2:y=h-50[v_final]"
        )
    else:
        # Vertical 9:16 layout
        if platform == "youtube":
            filter_complex = (
                "[0:v]split=2[bg][fg];"
                "[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=50:5,setpts=PTS/1.18[bg_blurred];"
                "[fg]fps=20,scale=1050:-2,crop=1000:ih,setpts=PTS/1.18[fg_scaled];"
                "[bg_blurred][fg_scaled]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2[base];"
                "[1:v]format=yuva420p,colorkey=black:0.1:0.0,colorchannelmixer=aa=0.15[rain_alpha];"
                "[base][rain_alpha]overlay=shortest=1[v_boxed_pre];"
                "[v_boxed_pre]drawbox=y=0:color=black@0.9:width=iw:height=220:t=fill,"
                "drawbox=y=ih-220:color=black@0.9:width=iw:height=220:t=fill[v_boxed];"
                f"[v_boxed]drawtext=fontfile='{FONT_PATH}':text='{clean_title}':fontsize=50:fontcolor=white:x=(w-text_w)/2:y=80,"
                f"drawtext=fontfile='{FONT_PATH}':text='yalla-shoot-today.vercel.app':fontsize=38:fontcolor=yellow:x=(w-text_w)/2:y=h-150[v_final]"
            )
        else:
            filter_complex = (
                "[0:v]split=2[bg][fg];"
                "[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=50:5,setpts=PTS/1.18[bg_blurred];"
                "[fg]scale=1050:-2,crop=1000:ih,setpts=PTS/1.18[fg_scaled];"
                "[bg_blurred][fg_scaled]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2[base];"
                "[1:v]format=yuva420p,colorkey=black:0.1:0.0,colorchannelmixer=aa=0.15[rain_alpha];"
                "[base][rain_alpha]overlay=shortest=1[v_boxed_pre];"
                "[v_boxed_pre]drawbox=y=0:color=black@0.95:width=iw:height=220:t=fill,"
                "drawbox=y=ih-220:color=black@0.95:width=iw:height=220:t=fill[v_boxed];"
                f"[v_boxed]drawtext=fontfile='{FONT_PATH}':text='{clean_title}':fontsize=48:fontcolor=yellow:x=(w-text_w)/2:y=80,"
                f"drawtext=fontfile='{FONT_PATH}':text='شاهد البث المباشر على موقعنا مجاناً':fontsize=40:fontcolor=white:x=(w-text_w)/2:y=h-150[v_final]"
            )

    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-stream_loop", "-1",
        "-i", RAIN_OVERLAY_PATH,
        "-filter_complex", filter_complex,
        "-map", "[v_final]",
        "-map", "0:a?",
        "-af", audio_filter,
        "-t", str(max_duration_sec),
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "28",
        "-maxrate", "2M",
        "-bufsize", "4M",
        "-c:a", "aac",
        "-b:a", "96k",
        "-pix_fmt", "yuv420p",
        output_path
    ]

    try:
        logger.info("Running FFmpeg video transformation command...")
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=1800)
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
