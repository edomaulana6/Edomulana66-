from PIL import Image, ImageEnhance
import os

def enhance_photo(input_path: str, enhancement_type: str) -> str:
    img = Image.open(input_path)

    if enhancement_type == "sharpen":
        enhancer = ImageEnhance.Sharpness(img)
        enhanced_img = enhancer.enhance(2.0)
    elif enhancement_type == "contrast":
        enhancer = ImageEnhance.Contrast(img)
        enhanced_img = enhancer.enhance(1.5)
    else:
        return input_path

    base, ext = os.path.splitext(input_path)
    output_path = f"{base}_enhanced_{enhancement_type}{ext}"
    enhanced_img.save(output_path)
    return output_path
