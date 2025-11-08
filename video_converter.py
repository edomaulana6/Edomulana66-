import subprocess
import os
import logging

logger = logging.getLogger(__name__)

def enhance_video_quality(input_path: str) -> str:
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    base_filename, _ = os.path.splitext(os.path.basename(input_path))
    output_filename = f"enhanced_quality_{base_filename}.mp4"
    output_path = os.path.join(os.path.dirname(input_path), output_filename)

    command = [
        'ffmpeg', '-i', input_path,
        '-c:v', 'libx264', '-crf', '18', '-preset', 'slow',
        '-c:a', 'copy', '-y', output_path
    ]

    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        logger.info(f"FFmpeg stdout (enhance): {result.stdout}")
    except subprocess.CalledProcessError as e:
        error_message = f"FFmpeg failed while enhancing quality (exit code {e.returncode}).\nStderr: {e.stderr}"
        logger.error(error_message)
        raise RuntimeError(error_message)

    return output_path

def convert_video_resolution(input_path: str, target_resolution: str) -> str:
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    base_filename, _ = os.path.splitext(os.path.basename(input_path))
    output_filename = f"converted_{target_resolution}_{base_filename}.mp4"
    output_path = os.path.join(os.path.dirname(input_path), output_filename)

    resolution_map = {
        "4k": "scale=-2:2160", "2k": "scale=-2:1440",
        "1080p": "scale=-2:1080", "720p": "scale=-2:720",
        "480p": "scale=-2:480", "360p": "scale=-2:360",
    }

    scale_param = resolution_map.get(target_resolution)
    if not scale_param:
        raise ValueError(f"Invalid target resolution: {target_resolution}")

    command = [
        'ffmpeg', '-i', input_path,
        '-vf', scale_param, '-c:v', 'libx264', '-crf', '28',
        '-c:a', 'copy', '-y', output_path
    ]

    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        logger.info(f"ffmpeg output (convert): {result.stdout}")
    except subprocess.CalledProcessError as e:
        error_message = f"FFmpeg failed while converting resolution (exit code {e.returncode}).\nStderr: {e.stderr}"
        logger.error(error_message)
        raise RuntimeError(error_message)

    return output_path
