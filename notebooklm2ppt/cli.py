"""CLI: Convert PDF to editable PowerPoint presentations"""

import os
import time
import threading
import cv2
import shutil
import argparse
import sys
from pathlib import Path
from .pdf2png import pdf_to_png
from .utils.image_viewer import show_image_fullscreen
from .utils.screenshot_automation import take_fullscreen_snip, mouse, screen_height, screen_width
from .ppt_combiner import combine_ppt


def process_pdf_to_ppt(pdf_path, png_dir, ppt_dir, delay_between_images=2, inpaint=True, dpi=150, timeout=50, display_height=None, display_width=None, pc_manager_version=None, done_button_offset=None):
    """
    Convert PDF to PNG images, then process each image with screenshot capture.
    
    Args:
        pdf_path: Path to the PDF file
        png_dir: Output directory for PNG images
        ppt_dir: Output directory for PPT files
        delay_between_images: Delay between processing each image (seconds), default 2
        inpaint: Enable image inpainting (watermark removal), default True
        dpi: PNG output resolution, default 150
        timeout: PPT window detection timeout (seconds), default 50
        display_height: Display window height (pixels), default None uses screen height
        display_width: Display window width (pixels), default None uses screen width
        pc_manager_version: PC Manager version; 3.19+ uses 190, below 3.19 uses 210
        done_button_offset: Done button right offset; takes priority if specified
    """
    # 1. Convert PDF to PNG images
    print("=" * 60)
    print("Step 1: Converting PDF to PNG images")
    print("=" * 60)
    
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file {pdf_path} does not exist")
        return
    
    pdf_to_png(pdf_path, png_dir, dpi=dpi, inpaint=inpaint)
    
    # Create PPT output directory
    ppt_dir.mkdir(exist_ok=True, parents=True)
    print(f"PPT output directory: {ppt_dir}")
    
    # Get user's Downloads folder path
    downloads_folder = Path.home() / "Downloads"
    print(f"Downloads folder: {downloads_folder}")
    
    # 2. Get all PNG image files and sort them
    png_files = sorted(png_dir.glob("page_*.png"))
    
    if not png_files:
        print(f"Error: No PNG images found in {png_dir}")
        return
    
    print("\n" + "=" * 60)
    print(f"Step 2: Processing {len(png_files)} PNG images")
    print("=" * 60)
    
    # Set display window size (use screen size if not specified)
    if display_height is None:
        display_height = screen_height
    if display_width is None:
        display_width = screen_width
    
    print(f"Display window size: {display_width} x {display_height}")

    
    # 3. Process each image with screenshot capture
    for idx, png_file in enumerate(png_files, 1):
        print(f"\n[{idx}/{len(png_files)}] Processing image: {png_file.name}")
        
        stop_event = threading.Event()
        
        def _viewer():
            """Display image in thread"""
            show_image_fullscreen(str(png_file), display_height=display_height)
            # Maintain OpenCV event loop
            while not stop_event.is_set():
                cv2.waitKey(50)
            # Close window
            try:
                cv2.destroyAllWindows()
            except Exception:
                pass
        
        # Start image display thread
        viewer_thread = threading.Thread(
            target=_viewer, 
            name=f"opencv_viewer_{idx}", 
            daemon=True
        )
        viewer_thread.start()
        
        # Wait for window to stabilize
        time.sleep(3)
        
        try:
            # Take fullscreen screenshot and detect PPT window
            success, ppt_filename = take_fullscreen_snip(
                check_ppt_window=True,
                ppt_check_timeout=timeout,
                width=display_width,
                height=display_height,
                pc_manager_version=pc_manager_version,
                done_button_right_offset=done_button_offset,
            )
            if success and ppt_filename:
                print(f"OK - Image {png_file.name} processed, PPT window created: {ppt_filename}")
                
                # Find and copy PPT file from Downloads folder
                if " - PowerPoint" in ppt_filename:
                    base_filename = ppt_filename.replace(" - PowerPoint", "").strip()
                else:
                    base_filename = ppt_filename.strip()
                
                if not base_filename.endswith(".pptx"):
                    search_filename = base_filename + ".pptx"
                else:
                    search_filename = base_filename
                
                ppt_source_path = downloads_folder / search_filename
                
                if not ppt_source_path.exists():
                    print(f"  Not found: {ppt_source_path}, searching for recent .pptx files...")
                    pptx_files = list(downloads_folder.glob("*.pptx"))
                    if pptx_files:
                        pptx_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                        ppt_source_path = pptx_files[0]
                        print(f"  Found recent PPT file: {ppt_source_path.name}")
                
                if ppt_source_path.exists():
                    target_filename = png_file.stem + ".pptx"
                    target_path = ppt_dir / target_filename
                    
                    shutil.copy2(ppt_source_path, target_path)
                    print(f"  OK - PPT file copied: {target_path}")
                    
                    try:
                        ppt_source_path.unlink()
                        print(f"  OK - Deleted source file: {ppt_source_path}")
                    except Exception as e:
                        print(f"  WARNING - Failed to delete source file: {e}")
                else:
                    print(f"  WARNING - PPT file not found in Downloads folder")
            elif success:
                print(f"OK - Image {png_file.name} processed, but PPT filename not retrieved")
            else:
                print(f"WARNING - Image {png_file.name} captured, but no new PPT window detected")
                close_button = (display_width - 35, display_height + 35)
                mouse.click(button='left', coords=close_button)
        except Exception as e:
            print(f"ERROR - Failed to process image {png_file.name}: {e}")
        finally:
            stop_event.set()
            viewer_thread.join(timeout=2)
        
        if idx < len(png_files):
            print(f"Waiting {delay_between_images} seconds before processing next image...")
            time.sleep(delay_between_images)
    
    print("\n" + "=" * 60)
    print(f"Done! Processed {len(png_files)} images")
    print("=" * 60)


def main():
    # If no arguments or first argument is --gui, launch GUI
    if len(sys.argv) == 1 or (len(sys.argv) > 1 and sys.argv[1] == "--gui"):
        from .gui import launch_gui
        launch_gui()
        return

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='NotebookLM2PPT - Convert PDF to editable PowerPoint presentations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  notebooklm2ppt examples/demo.pdf                  # Convert specified PDF
  notebooklm2ppt examples/demo.pdf --no-inpaint     # Disable image inpainting (watermark removal)
  notebooklm2ppt examples/demo.pdf -d 3 -t 60       # Set delay and timeout
  notebooklm2ppt -s 0.9 examples/demo.pdf           # Set display size ratio
        """
    )
    
    parser.add_argument(
        'pdf_file',
        help='Path to PDF file'
    )
    
    parser.add_argument(
        '-d', '--delay',
        type=float,
        default=2,
        metavar='SECONDS',
        help='Delay between processing each image in seconds (default: 2)'
    )
    
    parser.add_argument(
        '-t', '--timeout',
        type=float,
        default=50,
        metavar='SECONDS',
        help='PPT window detection timeout in seconds (default: 50)'
    )
    
    parser.add_argument(
        '--inpaint-notebooklm',
        dest='inpaint',
        action='store_true',
        help='Enable image inpainting (watermark removal), only removes NotebookLM watermarks'
    )
    
    parser.add_argument(
        '--no-inpaint',
        dest='inpaint',
        action='store_false',
        help='Disable image inpainting'
    )

    parser.add_argument(
        '--dpi',
        type=int,
        default=150,
        metavar='DPI',
        help='PNG output resolution, must be 150 to enable inpainting (default: 150)'
    )
    
    parser.set_defaults(inpaint=True)
    
    parser.add_argument(
        '-s', '--size-ratio',
        type=float,
        default=0.8,
        metavar='RATIO',
        help='Display size ratio, 1.0 fills the screen (default: 0.8). Try reducing if conversion fails'
    )
    
    parser.add_argument(
        '-o', '--output',
        metavar='DIR',
        help='Output directory (default: workspace)'
    )

    parser.add_argument(
        '--pcmgr-version',
        dest='pc_manager_version',
        type=str,
        default="3.19",
        help='PC Manager version for button position calculation; 3.19+ uses 190, below uses 210'
    )

    parser.add_argument(
        '--done-offset',
        dest='done_button_offset',
        type=int,
        default=None,
        help='Done button right offset (pixels). Takes priority when set, otherwise inferred from PC Manager version'
    )
    
    parser.add_argument(
        '--ocr',
        action='store_true',
        help='Use OCR mode: Reconstructs slides by lifting text into editable boxes and cleaning the background (Best for flattened PDFs)'
    )
    
    parser.add_argument(
        '--api-key',
        dest='api_key',
        type=str,
        default=None,
        help='Google Gemini API key for Vision-based text extraction (improves accuracy). Can also be set via GEMINI_API_KEY env var'
    )
    
    args = parser.parse_args()
    
    # Configure parameters
    pdf_file = args.pdf_file
    pdf_name = Path(pdf_file).stem
    
    # Define directories
    workspace_dir = Path(args.output) if args.output else Path("workspace")
    png_dir = workspace_dir / f"{pdf_name}_pngs"
    ppt_dir = workspace_dir / f"{pdf_name}_ppt"
    out_ppt_file = workspace_dir / f"{pdf_name}.pptx"
    workspace_dir.mkdir(exist_ok=True, parents=True)

    if args.ocr:
        # OCR Mode
        print("=" * 60)
        print("NotebookLM2PPT - OCR Mode")
        print("=" * 60)
        print(f"PDF File: {pdf_file}")
        print(f"Output: {out_ppt_file}")
        
        # 1. Convert PDF to PNGs
        print(f"Converting PDF to PNGs (Restoring 'Golden' Standard Res)...")
        pdf_to_png(pdf_file, png_dir, dpi=args.dpi, inpaint=False)
        
        # 2. Process with OCR and Reconstruct
        from .ocr_converter import SlideReconstructor
        from .ppt_generator import PPTCreator
        
        # Use Gemini Vision API if key is provided
        api_key = args.api_key
        if api_key:
            print(f"Using Gemini Vision API for text extraction")
        else:
            import os
            if os.environ.get('GEMINI_API_KEY'):
                print(f"Using Gemini Vision API (from GEMINI_API_KEY env var)")
            else:
                print(f"Note: For better text extraction, provide --api-key for Gemini Vision API")
        
        reconstructor = SlideReconstructor(api_key=api_key)
        ppt_creator = PPTCreator()
        
        import re
        all_pngs = sorted(png_dir.glob("page_*.png"))
        # Filter to only keep original pages "page_XXXX.png" matching 4 digits
        # This prevents processing the extracted clips like "page_0001_img_01.png"
        png_files = [p for p in all_pngs if re.match(r"page_\d{4}\.png", p.name)]
        
        print(f"\nProcessing {len(png_files)} pages with OCR...")
        
        for idx, png_file in enumerate(png_files, 1):
            print(f"[{idx}/{len(png_files)}] Processing {png_file.name}...")
            
            # Run OCR and Inpainting
            # We pass png_dir so it can save extracted images there
            result = reconstructor.process_image(png_file, output_dir=png_dir)
            
            # Save clean background (optional, for debug or cache)
            # We can use a temporary path or keep it in memory. 
            # PPTX needs a file path usually.
            clean_bg_path = png_dir / f"{png_file.stem}_clean.jpg"
            cv2.imwrite(str(clean_bg_path), result["clean_image"])
            
            # Add to PPT
            img_h, img_w = result["clean_image"].shape[:2]
            ppt_creator.add_slide(
                str(clean_bg_path), 
                result["text_blocks"], 
                result["image_objects"],
                (img_w, img_h)
            )
            
        ppt_creator.save(out_ppt_file)
        
        print("\n" + "=" * 60)
        print(f"Done! PPT saved to: {out_ppt_file}")
        print("=" * 60)
        
        out_ppt_file = os.path.abspath(out_ppt_file)
        os.startfile(out_ppt_file)
        return

    # Default Logic (Screenshot based)
    ratio = min(screen_width/16, screen_height/9)
    max_display_width = int(16 * ratio)
    max_display_height = int(9 * ratio)

    display_width = int(max_display_width * args.size_ratio)
    display_height = int(max_display_height * args.size_ratio)
    
    print("=" * 60)
    print("NotebookLM2PPT - Screenshot Mode (Legacy)")
    print("=" * 60)
    print(f"PDF file: {pdf_file}")
    print(f"Output directory: {workspace_dir}")
    print(f"Image inpainting (watermark removal): {'Enabled' if args.inpaint else 'Disabled'}")
    print(f"DPI: {args.dpi}")
    print(f"Delay: {args.delay} seconds")
    print(f"Timeout: {args.timeout} seconds")
    print(f"Display size: {display_width}x{display_height} (ratio: {args.size_ratio})")
    print(f"PC Manager version: {args.pc_manager_version or 'Not specified (using default offset)'}")
    print(f"Done button offset: {args.done_button_offset if args.done_button_offset is not None else 'Auto-inferred from version'}")
    print("=" * 60)
    print()

    process_pdf_to_ppt(
        pdf_path=pdf_file,
        png_dir=png_dir,
        ppt_dir=ppt_dir,
        delay_between_images=args.delay,
        inpaint=args.inpaint,
        dpi=args.dpi,
        timeout=args.timeout,
        display_height=display_height,
        display_width=display_width,
        pc_manager_version=args.pc_manager_version,
        done_button_offset=args.done_button_offset,
    )

    combine_ppt(ppt_dir, out_ppt_file)
    out_ppt_file = os.path.abspath(out_ppt_file)
    os.startfile(out_ppt_file)
    print(f"\nFinal merged PPT file: {out_ppt_file}")


if __name__ == "__main__":
    main()
