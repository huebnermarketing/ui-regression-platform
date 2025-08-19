"""
Create placeholder images for the PathResolver system
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path


def create_placeholder_image(text_lines, filename, color='#f8f9fa', text_color='#6c757d'):
    """Create a placeholder image with text"""
    
    # Create 400x300 placeholder image
    img = Image.new('RGB', (400, 300), color=color)
    draw = ImageDraw.Draw(img)
    
    # Try to use a font, fallback to default
    try:
        font = ImageFont.truetype("arial.ttf", 24)
        small_font = ImageFont.truetype("arial.ttf", 16)
    except:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    # Draw text lines
    y_offset = 100
    for i, line in enumerate(text_lines):
        current_font = font if i < 2 else small_font
        bbox = draw.textbbox((0, 0), line, font=current_font)
        text_width = bbox[2] - bbox[0]
        x = (400 - text_width) // 2
        draw.text((x, y_offset), line, fill=text_color, font=current_font)
        y_offset += 35 if i < 2 else 25
    
    # Save placeholder
    placeholder_dir = Path(__file__).parent
    placeholder_dir.mkdir(exist_ok=True)
    placeholder_path = placeholder_dir / filename
    img.save(placeholder_path, 'PNG')
    print(f"Created {placeholder_path}")


def main():
    """Create all placeholder images"""
    
    placeholders = [
        {
            'filename': 'not_found.png',
            'text_lines': ['Screenshot', 'Not Found', 'This image has not been captured yet'],
            'color': '#f8f9fa',
            'text_color': '#6c757d'
        },
        {
            'filename': 'no_baseline.png', 
            'text_lines': ['No Baseline', 'Available', 'No baseline image for comparison'],
            'color': '#fff3cd',
            'text_color': '#856404'
        },
        {
            'filename': 'processing.png',
            'text_lines': ['Processing...', 'Please Wait', 'Image is being generated'],
            'color': '#d1ecf1',
            'text_color': '#0c5460'
        },
        {
            'filename': 'error.png',
            'text_lines': ['Error', 'Loading Image', 'An error occurred while loading'],
            'color': '#f8d7da',
            'text_color': '#721c24'
        }
    ]
    
    for placeholder in placeholders:
        create_placeholder_image(
            placeholder['text_lines'],
            placeholder['filename'],
            placeholder['color'],
            placeholder['text_color']
        )
    
    print("All placeholder images created successfully!")


if __name__ == '__main__':
    main()