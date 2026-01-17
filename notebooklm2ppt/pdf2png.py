import fitz  # PyMuPDF
import os
from pathlib import Path
from .utils.image_inpainter import inpaint_image

def pdf_to_png(pdf_path, output_dir=None, dpi=150,inpaint=False):
    """
    Convert a PDF file to multiple PNG images
    
    Args:
        pdf_path: Path to the PDF file
        output_dir: Output directory, defaults to pdf_name_pngs folder in the same directory as the PDF
        dpi: Resolution, default 150
    """
    # Open the PDF file
    pdf_doc = fitz.open(pdf_path)
    
    # Determine output directory
    if output_dir is None:
        pdf_name = Path(pdf_path).stem  # Get PDF filename without extension
        output_dir = Path(pdf_path).parent / f"{pdf_name}_pngs"
    else:
        output_dir = Path(output_dir)
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Conversion factor: DPI / 72 (default screen DPI)
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    
    # Iterate through each page
    page_count = len(pdf_doc)  # Get page count before closing the document
    for page_num, page in enumerate(pdf_doc, 1):
        # Render page as image
        pix = page.get_pixmap(matrix=mat, alpha=False)
        
        # Save as PNG
        output_path = output_dir / f"page_{page_num:04d}.png"

        if os.path.exists(output_path):
            print(f"Skipping existing file: {output_path}")
            continue
        pix.save(output_path)
        print(f"✓ Saved: {output_path}")
        if inpaint:
            inpaint_image(str(output_path), str(output_path))
            print(f"✓ Inpainted: {output_path}")
            
    pdf_doc.close()
    print(f"\nDone! Converted {page_count} pages, output directory: {output_dir}")

if __name__ == "__main__":
    # Usage example
    pdf_file = "Hackathon_Architect_Playbook.pdf"  # Change to your PDF file path
    
    if os.path.exists(pdf_file):
        pdf_to_png(pdf_file, dpi=150)
    else:
        print(f"Error: File {pdf_file} does not exist")
