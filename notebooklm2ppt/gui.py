import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import sys
import os
import cv2
try:
    import windnd
except ImportError:
    print("windnd module not installed, drag-and-drop functionality will not be available.")
    windnd = None
from pathlib import Path
from .cli import process_pdf_to_ppt
from .ppt_combiner import combine_ppt
from .pdf2png import pdf_to_png
from .utils.screenshot_automation import screen_width, screen_height

class TextRedirector:
    def __init__(self, widget, tag="stdout"):
        self.widget = widget
        self.tag = tag

    def write(self, str):
        self.widget.configure(state='normal')
        self.widget.insert(tk.END, str, (self.tag,))
        self.widget.see(tk.END)
        self.widget.configure(state='disabled')

    def flush(self):
        pass

class AppGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF to PPT Converter")
        self.root.geometry("850x700")
        
        self.setup_ui()
        
        # Save original stdout/stderr
        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr
        
        # Redirect stdout and stderr
        sys.stdout = TextRedirector(self.log_area, "stdout")
        sys.stderr = TextRedirector(self.log_area, "stderr")
        
        if windnd:
            windnd.hook_dropfiles(self.root, func=self.on_drop_files)
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_drop_files(self, files):
        if files:
            # Get the first file dropped
            file_path = files[0].decode('gbk') if isinstance(files[0], bytes) else files[0]
            if file_path.lower().endswith('.pdf'):
                self.pdf_path_var.set(file_path)
                self._update_drop_zone_success()
                print(f"File selected via drag-and-drop: {file_path}")
            else:
                messagebox.showwarning("Warning", "Only PDF files are supported")
    
    def _update_drop_zone_success(self):
        """Update drop zone to show file is loaded"""
        self.drop_zone_label.config(
            text="✅ PDF Loaded! Drag another to replace.",
            foreground="#28a745"
        )
    
    def _update_drop_zone_default(self):
        """Reset drop zone to default state"""
        self.drop_zone_label.config(
            text="📄 Drag & Drop PDF Here\n(or use Browse button below)",
            foreground="#666666"
        )

    def on_closing(self):
        # Restore stdout/stderr
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr
        self.root.destroy()

    def add_context_menu(self, widget):
        """Add right-click context menu to input fields (Cut, Copy, Paste, Select All)"""
        menu = tk.Menu(widget, tearoff=0)
        menu.add_command(label="Cut", command=lambda: widget.event_generate("<<Cut>>"))
        menu.add_command(label="Copy", command=lambda: widget.event_generate("<<Copy>>"))
        menu.add_command(label="Paste", command=lambda: widget.event_generate("<<Paste>>"))
        menu.add_separator()
        menu.add_command(label="Select All", command=lambda: widget.select_range(0, tk.END))
        
        def show_menu(event):
            menu.post(event.x_root, event.y_root)
        
        widget.bind("<Button-3>", show_menu)

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ============ DRAG AND DROP ZONE ============
        drop_frame = ttk.LabelFrame(main_frame, text="📁 Drop Zone", padding="10")
        drop_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Create a canvas-based drop zone with dashed border effect
        self.drop_zone = tk.Frame(drop_frame, bg="#f8f9fa", relief="groove", bd=2, height=80)
        self.drop_zone.pack(fill=tk.X, padx=5, pady=5)
        self.drop_zone.pack_propagate(False)  # Maintain fixed height
        
        self.drop_zone_label = tk.Label(
            self.drop_zone,
            text="📄 Drag & Drop PDF Here\n(or use Browse button below)",
            font=("Segoe UI", 11),
            bg="#f8f9fa",
            fg="#666666",
            cursor="hand2"
        )
        self.drop_zone_label.pack(expand=True)
        
        # Make the drop zone clickable to browse
        self.drop_zone.bind("<Button-1>", lambda e: self.browse_pdf())
        self.drop_zone_label.bind("<Button-1>", lambda e: self.browse_pdf())

        # ============ FILE SETTINGS ============
        file_frame = ttk.LabelFrame(main_frame, text="File Settings", padding="10")
        file_frame.pack(fill=tk.X, pady=5)

        ttk.Label(file_frame, text="PDF File:").grid(row=0, column=0, sticky=tk.W)
        self.pdf_path_var = tk.StringVar()
        self.pdf_path_var.trace_add("write", self._on_pdf_path_changed)
        pdf_entry = ttk.Entry(file_frame, textvariable=self.pdf_path_var, width=60)
        pdf_entry.grid(row=0, column=1, padx=5)
        self.add_context_menu(pdf_entry)
        ttk.Button(file_frame, text="Browse", command=self.browse_pdf).grid(row=0, column=2)

        ttk.Label(file_frame, text="Output Directory:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.output_dir_var = tk.StringVar(value="workspace")
        output_entry = ttk.Entry(file_frame, textvariable=self.output_dir_var, width=60)
        output_entry.grid(row=1, column=1, padx=5, pady=5)
        self.add_context_menu(output_entry)
        ttk.Button(file_frame, text="Browse", command=self.browse_output).grid(row=1, column=2, pady=5)

        # ============ CONVERSION MODE ============
        mode_frame = ttk.LabelFrame(main_frame, text="⚡ Conversion Mode", padding="10")
        mode_frame.pack(fill=tk.X, pady=5)
        
        self.ocr_mode_var = tk.BooleanVar(value=True)  # Default to background mode
        
        # Background Mode (OCR) - Recommended
        bg_mode_frame = ttk.Frame(mode_frame)
        bg_mode_frame.pack(fill=tk.X)
        
        self.bg_mode_radio = ttk.Radiobutton(
            bg_mode_frame, 
            text="🟢 Background Mode (Recommended)", 
            variable=self.ocr_mode_var, 
            value=True,
            command=self._on_mode_changed
        )
        self.bg_mode_radio.pack(side=tk.LEFT)
        
        ttk.Label(
            bg_mode_frame, 
            text="— Runs in background, you can keep using your computer",
            foreground="#666666"
        ).pack(side=tk.LEFT, padx=(10, 0))
        
        # Screenshot Mode
        ss_mode_frame = ttk.Frame(mode_frame)
        ss_mode_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.ss_mode_radio = ttk.Radiobutton(
            ss_mode_frame, 
            text="🔴 Screenshot Mode (Legacy)", 
            variable=self.ocr_mode_var, 
            value=False,
            command=self._on_mode_changed
        )
        self.ss_mode_radio.pack(side=tk.LEFT)
        
        ttk.Label(
            ss_mode_frame, 
            text="— Uses PC Manager automation, takes control of mouse/keyboard",
            foreground="#666666"
        ).pack(side=tk.LEFT, padx=(10, 0))

        # ============ OPTIONS ============
        opt_frame = ttk.LabelFrame(main_frame, text="Conversion Options", padding="10")
        opt_frame.pack(fill=tk.X, pady=5)

        # Row 0: DPI and Inpainting
        ttk.Label(opt_frame, text="DPI:").grid(row=0, column=0, sticky=tk.W)
        self.dpi_var = tk.IntVar(value=150)
        dpi_entry = ttk.Entry(opt_frame, textvariable=self.dpi_var, width=10)
        dpi_entry.grid(row=0, column=1, sticky=tk.W, padx=5)
        self.add_context_menu(dpi_entry)

        self.inpaint_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt_frame, text="Remove Watermark", variable=self.inpaint_var).grid(row=0, column=2, columnspan=2, sticky=tk.W, padx=10)

        # Screenshot mode options (hidden by default)
        self.screenshot_options_frame = ttk.Frame(opt_frame)
        self.screenshot_options_frame.grid(row=1, column=0, columnspan=6, sticky=tk.W, pady=5)
        
        ttk.Label(self.screenshot_options_frame, text="Delay (sec):").pack(side=tk.LEFT)
        self.delay_var = tk.IntVar(value=2)
        delay_entry = ttk.Entry(self.screenshot_options_frame, textvariable=self.delay_var, width=8)
        delay_entry.pack(side=tk.LEFT, padx=(5, 15))

        ttk.Label(self.screenshot_options_frame, text="Timeout (sec):").pack(side=tk.LEFT)
        self.timeout_var = tk.IntVar(value=50)
        timeout_entry = ttk.Entry(self.screenshot_options_frame, textvariable=self.timeout_var, width=8)
        timeout_entry.pack(side=tk.LEFT, padx=(5, 15))

        ttk.Label(self.screenshot_options_frame, text="Display Ratio:").pack(side=tk.LEFT)
        self.ratio_var = tk.DoubleVar(value=0.8)
        ratio_entry = ttk.Entry(self.screenshot_options_frame, textvariable=self.ratio_var, width=8)
        ratio_entry.pack(side=tk.LEFT, padx=(5, 15))
        
        ttk.Label(self.screenshot_options_frame, text="PC Mgr Ver:").pack(side=tk.LEFT)
        self.pc_mgr_version_var = tk.StringVar(value="3.19")
        pc_mgr_entry = ttk.Entry(self.screenshot_options_frame, textvariable=self.pc_mgr_version_var, width=8)
        pc_mgr_entry.pack(side=tk.LEFT, padx=5)
        
        # Done offset row (screenshot mode only)
        self.done_offset_frame = ttk.Frame(opt_frame)
        self.done_offset_frame.grid(row=2, column=0, columnspan=6, sticky=tk.W, pady=5)
        
        ttk.Label(self.done_offset_frame, text="Done Button Offset:").pack(side=tk.LEFT)
        self.done_offset_var = tk.StringVar(value="")
        done_offset_entry = ttk.Entry(self.done_offset_frame, textvariable=self.done_offset_var, width=10)
        done_offset_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(self.done_offset_frame, text="(Leave empty for auto)", foreground="#666666").pack(side=tk.LEFT)
        
        # Initially hide screenshot-specific options
        self._on_mode_changed()

        # ============ CONTROL ============
        ctrl_frame = ttk.Frame(main_frame, padding="10")
        ctrl_frame.pack(fill=tk.X)

        self.start_btn = ttk.Button(ctrl_frame, text="🚀 Start Conversion", command=self.start_conversion)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        # Status label
        self.status_label = ttk.Label(ctrl_frame, text="Ready", foreground="#666666")
        self.status_label.pack(side=tk.LEFT, padx=20)

        # ============ LOG AREA ============
        log_frame = ttk.LabelFrame(main_frame, text="Log Output", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log_area = scrolledtext.ScrolledText(log_frame, state='disabled', height=12)
        self.log_area.pack(fill=tk.BOTH, expand=True)
        self.log_area.tag_config("stderr", foreground="red")
    
    def _on_pdf_path_changed(self, *args):
        """Update drop zone when PDF path changes"""
        path = self.pdf_path_var.get().strip()
        if path and os.path.exists(path) and path.lower().endswith('.pdf'):
            self._update_drop_zone_success()
        else:
            self._update_drop_zone_default()
    
    def _on_mode_changed(self):
        """Show/hide options based on selected mode"""
        if self.ocr_mode_var.get():
            # Background mode - hide screenshot-specific options
            self.screenshot_options_frame.grid_remove()
            self.done_offset_frame.grid_remove()
        else:
            # Screenshot mode - show all options
            self.screenshot_options_frame.grid()
            self.done_offset_frame.grid()

    def browse_pdf(self):
        # Clean up quotes and spaces in the path, convenient for users pasting paths with quotes
        current_path = self.pdf_path_var.get().strip().strip('"')
        initial_dir = os.path.dirname(current_path) if current_path and os.path.exists(os.path.dirname(current_path)) else None
        
        filename = filedialog.askopenfilename(
            parent=self.root,
            title="Select PDF File",
            initialdir=initial_dir,
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if filename:
            self.pdf_path_var.set(filename)

    def browse_output(self):
        # Clean up quotes and spaces in the path
        current_dir = self.output_dir_var.get().strip().strip('"')
        initial_dir = current_dir if current_dir and os.path.exists(current_dir) else None
        
        directory = filedialog.askdirectory(
            parent=self.root,
            title="Select Output Directory",
            initialdir=initial_dir
        )
        if directory:
            self.output_dir_var.set(directory)

    def start_conversion(self):
        pdf_path = self.pdf_path_var.get().strip().strip('"')
        output_dir = self.output_dir_var.get().strip().strip('"')
        
        # Update variables with sanitized paths
        self.pdf_path_var.set(pdf_path)
        self.output_dir_var.set(output_dir)

        if not pdf_path or not os.path.exists(pdf_path):
            messagebox.showerror("Error", "Please select a valid PDF file")
            return

        self.start_btn.config(state=tk.DISABLED)
        self.status_label.config(text="Converting...", foreground="#007bff")
        
        if self.ocr_mode_var.get():
            threading.Thread(target=self.run_ocr_conversion, daemon=True).start()
        else:
            threading.Thread(target=self.run_screenshot_conversion, daemon=True).start()

    def run_ocr_conversion(self):
        """Run OCR/Direct extraction mode (background processing)"""
        try:
            from .direct_extractor import DirectSlideExtractor
            from .ppt_generator import PPTCreator
            import re
            
            pdf_file = self.pdf_path_var.get()
            pdf_name = Path(pdf_file).stem
            workspace_dir = Path(self.output_dir_var.get())
            png_dir = workspace_dir / f"{pdf_name}_pngs"
            out_ppt_file = workspace_dir / f"{pdf_name}.pptx"
            
            workspace_dir.mkdir(exist_ok=True, parents=True)
            
            print("=" * 60)
            print("NotebookLM2PPT - Background Mode (OCR/Direct Extraction)")
            print("=" * 60)
            print(f"PDF File: {pdf_file}")
            print(f"Output: {out_ppt_file}")
            print("You can continue using your computer while this runs!")
            print()
            
            # 1. Convert PDF to PNGs
            print("Step 1: Converting PDF to PNG images...")
            pdf_to_png(pdf_file, png_dir, dpi=self.dpi_var.get(), inpaint=False)
            
            # 2. Process with Direct PDF Extraction
            print("\nStep 2: Extracting text and images from PDF...")
            extractor = DirectSlideExtractor()
            ppt_creator = PPTCreator()
            
            all_pngs = sorted(png_dir.glob("page_*.png"))
            png_files = [p for p in all_pngs if re.match(r"page_\d{4}\.png", p.name)]
            
            print(f"\nProcessing {len(png_files)} pages...")
            
            for idx, png_file in enumerate(png_files):
                print(f"[{idx+1}/{len(png_files)}] Processing {png_file.name}...")
                
                try:
                    slide_data = extractor.process_page(
                        pdf_path=pdf_file,
                        image_path=str(png_file),
                        output_dir=png_dir,
                        page_num=idx
                    )
                    
                    # Save clean background
                    clean_bg_path = png_dir / f"{png_file.stem}_clean.jpg"
                    cv2.imwrite(str(clean_bg_path), slide_data["clean_image"])
                    
                    # Add to PPT
                    img_h, img_w = slide_data["clean_image"].shape[:2]
                    ppt_creator.add_slide(
                        str(clean_bg_path),
                        slide_data["text_blocks"],
                        slide_data["image_objects"],
                        (img_w, img_h)
                    )
                except Exception as e:
                    print(f"Error processing page {idx}: {e}")
                    import traceback
                    traceback.print_exc()
            
            ppt_creator.save(out_ppt_file)
            
            print("\n" + "=" * 60)
            print(f"Done! PPT saved to: {out_ppt_file}")
            print("=" * 60)
            
            out_ppt_file = os.path.abspath(out_ppt_file)
            os.startfile(out_ppt_file)
            
            self.root.after(0, lambda: self.status_label.config(text="✅ Complete!", foreground="#28a745"))
            messagebox.showinfo("Success", f"Conversion complete!\nFile saved to: {out_ppt_file}")
            
        except Exception as e:
            print(f"\nError occurred: {str(e)}")
            self.root.after(0, lambda: self.status_label.config(text="❌ Error", foreground="#dc3545"))
            messagebox.showerror("Error", f"An error occurred during conversion: {str(e)}")
        finally:
            self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))

    def run_screenshot_conversion(self):
        """Run screenshot mode (legacy, takes control of computer)"""
        try:
            pdf_file = self.pdf_path_var.get()
            pdf_name = Path(pdf_file).stem
            workspace_dir = Path(self.output_dir_var.get())
            png_dir = workspace_dir / f"{pdf_name}_pngs"
            ppt_dir = workspace_dir / f"{pdf_name}_ppt"
            out_ppt_file = workspace_dir / f"{pdf_name}.pptx"
            
            workspace_dir.mkdir(exist_ok=True, parents=True)

            offset_raw = self.done_offset_var.get().strip()
            done_offset = None
            if offset_raw:
                try:
                    done_offset = int(offset_raw)
                except ValueError:
                    raise ValueError("Done button offset must be an integer or left empty")

            ratio = min(screen_width/16, screen_height/9)
            max_display_width = int(16 * ratio)
            max_display_height = int(9 * ratio)

            display_width = int(max_display_width * self.ratio_var.get())
            display_height = int(max_display_height * self.ratio_var.get())

            print(f"Starting to process: {pdf_file}")
            print(f"Done button offset: {done_offset if done_offset is not None else 'auto by version'}")
            print("⚠️ WARNING: Screenshot mode will take control of your mouse/keyboard!")
            print("Do not touch your computer until conversion is complete.")
            print()
            
            process_pdf_to_ppt(
                pdf_path=pdf_file,
                png_dir=png_dir,
                ppt_dir=ppt_dir,
                delay_between_images=self.delay_var.get(),
                inpaint=self.inpaint_var.get(),
                dpi=self.dpi_var.get(),
                timeout=self.timeout_var.get(),
                display_height=display_height,
                display_width=display_width,
                pc_manager_version=self.pc_mgr_version_var.get(),
                done_button_offset=done_offset
            )

            combine_ppt(ppt_dir, out_ppt_file)
            out_ppt_file = os.path.abspath(out_ppt_file)
            print(f"\nConversion complete! Final file: {out_ppt_file}")
            os.startfile(out_ppt_file)
            
            self.root.after(0, lambda: self.status_label.config(text="✅ Complete!", foreground="#28a745"))
            messagebox.showinfo("Success", f"Conversion complete!\nFile saved to: {out_ppt_file}")
        except Exception as e:
            print(f"\nError occurred: {str(e)}")
            self.root.after(0, lambda: self.status_label.config(text="❌ Error", foreground="#dc3545"))
            messagebox.showerror("Error", f"An error occurred during conversion: {str(e)}")
        finally:
            self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))

def launch_gui():
    root = tk.Tk()
    app = AppGUI(root)
    root.mainloop()

if __name__ == "__main__":
    launch_gui()
