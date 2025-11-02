from PIL import Image, ImageEnhance, ImageFilter

def enhance_photo(image_path: str, enhancement_type: str) -> str:
    """
    Applies a specified enhancement to an image.

    Args:
        image_path: Path to the input image.
        enhancement_type: The type of enhancement to apply ('sharpen', 'contrast').

    Returns:
        Path to the enhanced image.
    """
    img = Image.open(image_path)

    if enhancement_type == 'sharpen':
        enhancer = ImageEnhance.Sharpness(img)
        enhanced_img = enhancer.enhance(2.0)
    elif enhancement_type == 'contrast':
        enhancer = ImageEnhance.Contrast(img)
        enhanced_img = enhancer.enhance(1.5)
    else:
        # Return original if no valid enhancement is selected
        enhanced_img = img

    # Save the enhanced image to a new file
    output_path = f"enhanced_{enhancement_type}_{image_path.split('/')[-1]}"
    enhanced_img.save(output_path)
    return output_path
