from PIL import Image, ImageEnhance, ImageFilter
import os

def enhance_photo(input_path: str, enhancement_type: str) -> str:
    """
    Applies a specified enhancement to an image.

    Args:
        input_path: Path to the input image file.
        enhancement_type: The type of enhancement ("sharpen" or "contrast").

    Returns:
        Path to the enhanced image file.
    """
    img = Image.open(input_path)

    if enhancement_type == "sharpen":
        enhancer = ImageEnhance.Sharpness(img)
        enhanced_img = enhancer.enhance(2.0) # Increase sharpness
    elif enhancement_type == "contrast":
        enhancer = ImageEnhance.Contrast(img)
        enhanced_img = enhancer.enhance(1.5) # Increase contrast
    else:
        # Return original path if enhancement type is unknown
        return input_path

    output_path = f"enhanced_{enhancement_type}_{os.path.basename(input_path)}"
    enhanced_img.save(output_path)
    return output_path
