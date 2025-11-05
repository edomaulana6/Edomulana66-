import subprocess
import os

def convert_video_resolution(input_path: str, target_resolution: str) -> str:
    """
    Converts a video to a target resolution using ffmpeg.

    Args:
        input_path: Path to the input video file.
        target_resolution: The target resolution (e.g., "720p", "480p").

    Returns:
        Path to the converted video file.

    Raises:
        RuntimeError: If ffmpeg command fails.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Pastikan file output selalu punya ekstensi .mp4
    base_filename, _ = os.path.splitext(os.path.basename(input_path))
    output_filename = f"converted_{target_resolution}_{base_filename}.mp4"
    # Tempatkan file output di direktori yang sama dengan input
    output_path = os.path.join(os.path.dirname(input_path), output_filename)

    # Map friendly names to ffmpeg scale parameters
    # -2 ensures the width is divisible by 2, which is required by many codecs.
    resolution_map = {
        "4k": "scale=-2:2160",
        "2k": "scale=-2:1440",
        "1080p": "scale=-2:1080",
        "720p": "scale=-2:720",
        "480p": "scale=-2:480",
        "360p": "scale=-2:360",
    }

    scale_param = resolution_map.get(target_resolution)
    if not scale_param:
        raise ValueError(f"Invalid target resolution: {target_resolution}")

    # Build and execute the ffmpeg command
    command = [
        'ffmpeg',
        '-i', input_path,
        '-vf', scale_param,
        '-c:v', 'libx264', # Specify the video codec
        '-crf', '28',      # Apply Constant Rate Factor for compression
        '-c:a', 'copy',    # Copy audio stream without re-encoding
        '-y',              # Overwrite output file if it exists
        output_path
    ]

    try:
        # Using subprocess.run for better error handling
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        # It's good practice to have a logger instance, but for a standalone file,
        # we can use a simple print or import logging if it becomes complex.
        print(f"ffmpeg output: {result.stdout}")
    except subprocess.CalledProcessError as e:
        # Log the error from ffmpeg and raise an exception
        error_message = f"FFmpeg failed with exit code {e.returncode}.\nStderr: {e.stderr}"
        print(error_message) # Or use logger.error(error_message)
        raise RuntimeError(error_message)

    return output_path
