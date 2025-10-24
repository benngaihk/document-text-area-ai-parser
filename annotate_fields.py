#!/usr/bin/env python3
"""
Script to extract PDF form fields with coordinates and annotate them on the first page image.
"""

import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import fitz  # PyMuPDF

def extract_field_coordinates(pdf_path):
    """Extract form field names and their coordinates from PDF."""
    doc = fitz.open(pdf_path)
    page = doc[0]  # First page

    fields = {}

    # Get form fields (widgets)
    for widget in page.widgets():
        field_name = widget.field_name
        rect = widget.rect  # fitz.Rect object (x0, y0, x1, y1)
        field_type = widget.field_type_string

        fields[field_name] = {
            'rect': [rect.x0, rect.y0, rect.x1, rect.y1],
            'type': field_type
        }

    # Get page dimensions
    page_rect = page.rect
    page_width = page_rect.width
    page_height = page_rect.height

    doc.close()
    return fields, page_width, page_height

def annotate_image(image_path, fields, page_width, page_height, output_path):
    """Annotate the image with field names at their positions."""
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)

    # Calculate scale factor from PDF coordinates to image pixels
    img_width, img_height = img.size
    scale_x = img_width / page_width
    scale_y = img_height / page_height

    # Try to load a font, fall back to default if not available
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 30)
    except:
        font = ImageFont.load_default()

    # Draw field names
    for field_name, field_info in fields.items():
        rect = field_info['rect']
        # PyMuPDF coordinates: origin at top-left (same as PIL Image)
        # rect format: [x0, y0, x1, y1]
        x1 = rect[0] * scale_x
        y1 = rect[1] * scale_y
        x2 = rect[2] * scale_x
        y2 = rect[3] * scale_y

        # Draw rectangle
        draw.rectangle([x1, y1, x2, y2], outline='red', width=2)

        # Draw field name
        text_position = (x1 + 2, y1 + 2)
        # Draw text background for better visibility
        text_bbox = draw.textbbox(text_position, field_name, font=font)
        draw.rectangle(text_bbox, fill='yellow')
        draw.text(text_position, field_name, fill='red', font=font)

    img.save(output_path)
    print(f"Annotated image saved to: {output_path}")
    return output_path

def main():
    # File paths
    pdf_path = "/Users/admin/Desktop/kexian/google-doc-ai/NNC1_fillable.pdf"
    output_dir = Path("/Users/admin/Desktop/kexian/google-doc-ai/result")
    output_dir.mkdir(exist_ok=True)

    print("Converting PDF first page to image...")
    doc = fitz.open(pdf_path)
    page = doc[0]

    # Convert to image at 200 DPI
    zoom = 200 / 72  # 72 is default DPI
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)

    temp_image_path = output_dir / "NNC1_page1_temp.png"
    pix.save(temp_image_path)
    doc.close()
    print(f"Image saved to: {temp_image_path}")

    print("\nExtracting form field coordinates from PDF...")
    fields, page_width, page_height = extract_field_coordinates(pdf_path)

    print(f"Found {len(fields)} form fields")

    # Save field coordinates to JSON
    fields_json_path = output_dir / "NNC1_fields_with_coordinates.json"
    with open(fields_json_path, 'w', encoding='utf-8') as f:
        json.dump(fields, f, indent=2, ensure_ascii=False)
    print(f"Field coordinates saved to: {fields_json_path}")

    print("\nAnnotating image with field names...")
    annotated_image_path = output_dir / "NNC1_page1_annotated.png"
    annotate_image(temp_image_path, fields, page_width, page_height, annotated_image_path)

    print("\nDone! Check the annotated image.")

if __name__ == "__main__":
    main()
