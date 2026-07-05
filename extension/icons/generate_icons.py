#!/usr/bin/env python3
"""Generate PNG icons for SEO Inspector extension using Pillow."""

from PIL import Image, ImageDraw
import math

NAVY = (26, 26, 46)
NAVY_LIGHT = (42, 42, 62)
GOLD = (201, 168, 76)
GOLD_LIGHT = (212, 184, 106)

def draw_magnifying_glass(draw, size, cx, cy, r, stroke_width):
    """Draw a magnifying glass: circle + handle line at 45 degrees."""
    # Circle
    for angle in range(360):
        rad = math.radians(angle)
        x = cx + r * math.cos(rad)
        y = cy + r * math.sin(rad)
        # Draw thick circle using small dots pattern
        for sw in range(stroke_width):
            px = int(cx + (r - sw) * math.cos(rad))
            py = int(cy + (r - sw) * math.sin(rad))
            if 0 <= px < size and 0 <= py < size:
                draw.point((px, py), fill=GOLD)

    # Handle line at ~45 degrees from near the circle edge
    handle_start_x = cx + int(r * 0.7)
    handle_start_y = cy + int(r * 0.7)
    handle_end_x = size - int(size * 0.1)
    handle_end_y = size - int(size * 0.1)

    draw.line(
        [(handle_start_x, handle_start_y), (handle_end_x, handle_end_y)],
        fill=GOLD,
        width=stroke_width
    )

def create_icon(size, output_path):
    """Create a rounded-rect icon with magnifying glass."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Rounded rectangle background
    radius = max(3, size // 6)
    # Draw rounded rect manually
    draw.rounded_rectangle([(0, 0), (size - 1, size - 1)], radius=radius, fill=NAVY)

    # Magnifying glass parameters
    margin = int(size * 0.18)
    available = size - 2 * margin
    r = int(available * 0.38)
    cx = int(size * 0.38)
    cy = int(size * 0.36)
    stroke_width = max(1, size // 16)

    draw_magnifying_glass(draw, size, cx, cy, r, stroke_width)

    img.save(output_path, 'PNG')
    print(f"Created {output_path} ({size}x{size})")

if __name__ == '__main__':
    icons_dir = '/home/ubuntu/seo-tools/extension/icons'
    create_icon(16, f'{icons_dir}/icon-16.png')
    create_icon(48, f'{icons_dir}/icon-48.png')
    create_icon(128, f'{icons_dir}/icon-128.png')
    print("All icons generated.")
