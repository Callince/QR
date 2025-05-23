from PIL import Image, ImageDraw, ImageFont, ImageOps
from io import BytesIO
import qrcode
import base64
import json
import uuid
import os
import math

def generate_custom_qr(qr_data, options):
    """
    Generate a customized QR code based on provided options
    
    Parameters:
    qr_data (str): The data to encode in the QR code
    options (dict): Customization options including:
        - color: Fill color (hex)
        - background_color: Background color (hex)
        - shape: Shape type (square, rounded, circle)
        - frame_type: Frame style (None, square, rounded, circle, scan_me)
        - logo_path: Path to logo image (optional)
        - export_type: Output format (png, svg, gif, gradient)
    
    Returns:
    str: Base64 encoded image data
    """
    # Create QR code with error correction
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    # Create basic image with custom colors
    fill_color = options.get('color', '#000000')
    bg_color = options.get('background_color', '#FFFFFF')
    
    # Handle special export types
    export_type = options.get('export_type', 'png')
    if export_type == 'svg':
        return generate_svg_qr(qr, fill_color, bg_color, options)
    elif export_type == 'gif':
        return generate_animated_qr(qr, options)
    elif export_type == 'gradient':
        return generate_gradient_qr(qr, options)
    
    # Create standard image
    qr_img = qr.make_image(fill_color=fill_color, back_color=bg_color).convert('RGBA')
    
    # Apply shape customization
    shape = options.get('shape', 'square')
    if shape != 'square':
        qr_img = apply_shape(qr_img, shape)
    
    # Apply logo if provided
    logo_path = options.get('logo_path')
    if logo_path and os.path.exists(logo_path):
        qr_img = apply_logo(qr_img, logo_path)
    
    # Apply frame if specified
    frame_type = options.get('frame_type')
    if frame_type:
        qr_img = apply_frame(qr_img, frame_type, options)
    
    # Convert to base64
    buffered = BytesIO()
    qr_img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return f"data:image/png;base64,{img_str}"

def apply_shape(qr_img, shape):
    """Apply custom shape to QR code"""
    width, height = qr_img.size
    
    # Create mask based on shape
    mask = Image.new('L', (width, height), 0)
    draw = ImageDraw.Draw(mask)
    
    if shape == 'rounded':
        # Rounded corners
        radius = width // 10  # Adjust radius as needed
        draw.rectangle([radius, radius, width - radius, height - radius], fill=255)
        draw.rectangle([0, radius, width, height - radius], fill=255)
        draw.rectangle([radius, 0, width - radius, height], fill=255)
        draw.pieslice([0, 0, radius * 2, radius * 2], 180, 270, fill=255)
        draw.pieslice([width - radius * 2, 0, width, radius * 2], 270, 0, fill=255)
        draw.pieslice([0, height - radius * 2, radius * 2, height], 90, 180, fill=255)
        draw.pieslice([width - radius * 2, height - radius * 2, width, height], 0, 90, fill=255)
    elif shape == 'circle':
        # Circular mask
        draw.ellipse([0, 0, width, height], fill=255)
    
    # Apply mask to image
    result = Image.new('RGBA', (width, height))
    result.paste(qr_img, (0, 0), mask)
    
    return result

def apply_logo(qr_img, logo_path):
    """Apply logo to center of QR code"""
    # Open logo image
    logo = Image.open(logo_path).convert('RGBA')
    
    # Calculate logo size (25% of QR code)
    qr_width, qr_height = qr_img.size
    logo_max_size = min(qr_width, qr_height) // 4
    
    # Resize logo maintaining aspect ratio
    logo_width, logo_height = logo.size
    scale_factor = min(logo_max_size / logo_width, logo_max_size / logo_height)
    new_logo_width = int(logo_width * scale_factor)
    new_logo_height = int(logo_height * scale_factor)
    logo = logo.resize((new_logo_width, new_logo_height), Image.LANCZOS)
    
    # Create white background for logo
    logo_bg_size = int(logo_max_size * 1.2)  # Slightly larger than logo
    logo_bg = Image.new('RGBA', (logo_bg_size, logo_bg_size), (255, 255, 255, 255))
    
    # Calculate positions
    logo_pos = ((logo_bg_size - new_logo_width) // 2, (logo_bg_size - new_logo_height) // 2)
    qr_pos = ((qr_width - logo_bg_size) // 2, (qr_height - logo_bg_size) // 2)
    
    # Paste logo onto white background
    logo_bg.paste(logo, logo_pos, logo)
    
    # Paste logo with background onto QR code
    result = qr_img.copy()
    result.paste(logo_bg, qr_pos, logo_bg)
    
    return result

def apply_frame(qr_img, frame_type, options):
    """Apply frame around QR code"""
    qr_width, qr_height = qr_img.size
    
    # Determine frame size
    frame_padding = qr_width // 10
    frame_width = qr_width + (frame_padding * 2)
    
    # Additional height for "Scan Me" text
    text_height = 0
    if frame_type == 'scan_me':
        text_height = frame_padding * 2
    
    frame_height = qr_height + (frame_padding * 2) + text_height
    
    # Create frame image
    frame_img = Image.new('RGBA', (frame_width, frame_height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(frame_img)
    
    # Define frame color
    frame_color = options.get('frame_color', options.get('color', '#000000'))
    frame_color_rgb = tuple(int(frame_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + (255,)
    
    # Draw frame based on type
    if frame_type == 'square':
        draw.rectangle([0, 0, frame_width, frame_height], outline=frame_color_rgb, width=frame_padding // 2)
    elif frame_type == 'rounded':
        radius = frame_padding
        draw.rounded_rectangle([0, 0, frame_width, frame_height], radius=radius, outline=frame_color_rgb, width=frame_padding // 2)
    elif frame_type == 'circle':
        # For circle, we need to make the frame a perfect circle
        perfect_size = max(frame_width, frame_height)
        circle_img = Image.new('RGBA', (perfect_size, perfect_size), (255, 255, 255, 0))
        circle_draw = ImageDraw.Draw(circle_img)
        circle_draw.ellipse([0, 0, perfect_size, perfect_size], outline=frame_color_rgb, width=frame_padding // 2)
        frame_img = circle_img
        frame_width, frame_height = perfect_size, perfect_size
    elif frame_type == 'scan_me':
        # Draw rectangle frame
        draw.rectangle([0, text_height, frame_width, frame_height], outline=frame_color_rgb, width=frame_padding // 2)
        
        # Add "Scan Me" text
        try:
            font = ImageFont.truetype("arial.ttf", frame_padding)
        except IOError:
            # Fallback to default font
            font = ImageFont.load_default()
        
        text = "SCAN ME"
        text_width = draw.textlength(text, font=font)
        text_position = ((frame_width - text_width) // 2, frame_padding // 2)
        draw.text(text_position, text, fill=frame_color_rgb, font=font)
    
    # Paste QR code onto frame
    qr_position = ((frame_width - qr_width) // 2, (frame_height - qr_height) // 2)
    if frame_type == 'scan_me':
        qr_position = ((frame_width - qr_width) // 2, text_height + frame_padding)
    
    frame_img.paste(qr_img, qr_position)
    
    return frame_img

def generate_svg_qr(qr, fill_color, bg_color, options):
    """Generate SVG version of QR code"""
    qr_matrix = qr.get_matrix()
    shape = options.get('shape', 'square')
    
    # Convert color to RGB
    fill_rgb = tuple(int(fill_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    fill_color_str = f"rgb({fill_rgb[0]},{fill_rgb[1]},{fill_rgb[2]})"
    
    # Calculate dimensions
    module_count = len(qr_matrix)
    box_size = 10
    border = 4
    size = module_count * box_size + border * 2 * box_size
    
    # Start SVG
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" height="{size}">',
        f'<rect width="{size}" height="{size}" fill="{bg_color}"/>',
    ]
    
    # Draw modules
    for r, row in enumerate(qr_matrix):
        for c, val in enumerate(row):
            if val:
                x, y = c * box_size + border * box_size, r * box_size + border * box_size
                
                if shape == 'square':
                    svg.append(f'<rect x="{x}" y="{y}" width="{box_size}" height="{box_size}" fill="{fill_color_str}"/>')
                elif shape == 'rounded':
                    radius = box_size / 4
                    svg.append(f'<rect x="{x}" y="{y}" width="{box_size}" height="{box_size}" rx="{radius}" ry="{radius}" fill="{fill_color_str}"/>')
                elif shape == 'circle':
                    cx, cy = x + box_size / 2, y + box_size / 2
                    radius = box_size / 2
                    svg.append(f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="{fill_color_str}"/>')
    
    # Add logo if provided
    logo_path = options.get('logo_path')
    if logo_path and os.path.exists(logo_path):
        # This is a placeholder - for actual implementation, 
        # we'd need to embed the logo as base64 or include it as an SVG
        # For now, we'll just add a placeholder rectangle
        logo_size = size // 4
        logo_x = (size - logo_size) // 2
        logo_y = (size - logo_size) // 2
        svg.append(f'<rect x="{logo_x}" y="{logo_y}" width="{logo_size}" height="{logo_size}" fill="white"/>')
    
    # Close SVG
    svg.append('</svg>')
    
    svg_str = ''.join(svg)
    return f"data:image/svg+xml;base64,{base64.b64encode(svg_str.encode()).decode()}"

def generate_animated_qr(qr, options):
    """Generate animated GIF QR code"""
    # For simplicity, we'll create a sequence of frames with different colors
    frames = []
    base_color = options.get('color', '#000000')
    base_rgb = tuple(int(base_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    
    # Create 12 frames with color variations
    for i in range(12):
        # Create a color variation
        hue_shift = (i / 12) * 360  # Shift hue around the color wheel
        
        # Simple color shift algorithm (this is a simplified version)
        r = (base_rgb[0] + int(hue_shift) % 256)
        g = (base_rgb[1] + int(hue_shift) % 256)
        b = (base_rgb[2] + int(hue_shift) % 256)
        
        # Normalize to 0-255
        r = min(max(r, 0), 255)
        g = min(max(g, 0), 255)
        b = min(max(b, 0), 255)
        
        # Create frame with this color
        frame_color = f"#{r:02x}{g:02x}{b:02x}"
        qr_img = qr.make_image(fill_color=frame_color, back_color=options.get('background_color', '#FFFFFF'))
        
        # Apply shape if needed
        shape = options.get('shape', 'square')
        if shape != 'square':
            qr_img = apply_shape(qr_img.convert('RGBA'), shape)
        
        frames.append(qr_img)
    
    # Save frames as GIF
    buffered = BytesIO()
    frames[0].save(
        buffered, 
        format='GIF',
        append_images=frames[1:],
        save_all=True,
        duration=100,  # 100ms per frame
        loop=0  # Loop forever
    )
    
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/gif;base64,{img_str}"

def generate_gradient_qr(qr, options):
    """Generate QR code with gradient fill"""
    qr_matrix = qr.get_matrix()
    module_count = len(qr_matrix)
    
    # Get gradient colors
    start_color = options.get('gradient_start', options.get('color', '#000000'))
    end_color = options.get('gradient_end', '#0000FF')  # Default to blue if not specified
    bg_color = options.get('background_color', '#FFFFFF')
    
    # Parse colors
    start_rgb = tuple(int(start_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    end_rgb = tuple(int(end_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    
    # Create base image
    box_size = 10
    border = 4
    size = module_count * box_size + border * 2 * box_size
    img = Image.new('RGB', (size, size), bg_color)
    draw = ImageDraw.Draw(img)
    
    # Draw modules with gradient
    for r, row in enumerate(qr_matrix):
        for c, val in enumerate(row):
            if val:
                x, y = c * box_size + border * box_size, r * box_size + border * box_size
                
                # Calculate gradient position (0 to 1)
                # We'll use distance from top-left to bottom-right
                gradient_pos = (r + c) / (2 * module_count - 2)
                
                # Interpolate color
                color = (
                    int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * gradient_pos),
                    int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * gradient_pos),
                    int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * gradient_pos)
                )
                
                # Draw module
                draw.rectangle([x, y, x + box_size, y + box_size], fill=color)
    
    # Apply shape if needed
    shape = options.get('shape', 'square')
    if shape != 'square':
        img = apply_shape(img.convert('RGBA'), shape)
    
    # Convert to base64
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return f"data:image/png;base64,{img_str}"