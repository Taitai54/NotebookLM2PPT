import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import sys
import os
try:
    import windnd
except ImportError:
    print("windnd module not installed, drag-and-drop functionality will not be available.")
    windnd = None
from pathlib import Path
from .cli import process_pdf_to_ppt
from .ppt_combiner import combine_ppt
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
        self.root.geometry("800x600")
        
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
                print(f"File selected via drag-and-drop: {file_path}")
            else:
                messagebox.showwarning("Warning", "Only PDF files are supported")

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

        # File Selection
        file_frame = ttk.LabelFrame(main_frame, text="File Settings (Drag-and-drop PDF files supported)", padding="10")
        file_frame.pack(fill=tk.X, pady=5)

        ttk.Label(file_frame, text="PDF File:").grid(row=0, column=0, sticky=tk.W)
        self.pdf_path_var = tk.StringVar()
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

        # Options
        opt_frame = ttk.LabelFrame(main_frame, text="Conversion Options", padding="10")
        opt_frame.pack(fill=tk.X, pady=5)

        ttk.Label(opt_frame, text="DPI:").grid(row=0, column=0, sticky=tk.W)
        self.dpi_var = tk.IntVar(value=150)
        dpi_entry = ttk.Entry(opt_frame, textvariable=self.dpi_var, width=10)
        dpi_entry.grid(row=0, column=1, sticky=tk.W, padx=5)
        self.add_context_menu(dpi_entry)

        ttk.Label(opt_frame, text="Delay (sec):").grid(row=0, column=2, sticky=tk.W, padx=10)
        self.delay_var = tk.IntVar(value=2)
        delay_entry = ttk.Entry(opt_frame, textvariable=self.delay_var, width=10)
        delay_entry.grid(row=0, column=3, sticky=tk.W, padx=5)
        self.add_context_menu(delay_entry)

        ttk.Label(opt_frame, text="Timeout (sec):").grid(row=0, column=4, sticky=tk.W, padx=10)
        self.timeout_var = tk.IntVar(value=50)
        timeout_entry = ttk.Entry(opt_frame, textvariable=self.timeout_var, width=10)
        timeout_entry.grid(row=0, column=5, sticky=tk.W, padx=5)
        self.add_context_menu(timeout_entry)

        ttk.Label(opt_frame, text="Display Ratio:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.ratio_var = tk.DoubleVar(value=0.8)
        ratio_entry = ttk.Entry(opt_frame, textvariable=self.ratio_var, width=10)
        ratio_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        self.add_context_menu(ratio_entry)

        self.inpaint_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt_frame, text="Enable Image Inpainting (Remove Watermark)", variable=self.inpaint_var).grid(row=1, column=2, columnspan=2, sticky=tk.W, padx=10)

        ttk.Label(opt_frame, text="PC Manager Version:").grid(row=1, column=4, sticky=tk.W, padx=10)
        self.pc_mgr_version_var = tk.StringVar(value="3.19")
        pc_mgr_entry = ttk.Entry(opt_frame, textvariable=self.pc_mgr_version_var, width=10)
        pc_mgr_entry.grid(row=1, column=5, sticky=tk.W, padx=5)
        self.add_context_menu(pc_mgr_entry)

        ttk.Label(opt_frame, text="Done Button Offset:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.done_offset_var = tk.StringVar(value="")
        done_offset_entry = ttk.Entry(opt_frame, textvariable=self.done_offset_var, width=10)
        done_offset_entry.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        self.add_context_menu(done_offset_entry)
        ttk.Label(opt_frame, text="Leave empty for auto, or enter a number to fine-tune if the Done button is not being clicked").grid(row=2, column=2, columnspan=4, sticky=tk.W)

        # Control
        ctrl_frame = ttk.Frame(main_frame, padding="10")
        ctrl_frame.pack(fill=tk.X)

        self.start_btn = ttk.Button(ctrl_frame, text="Start Conversion", command=self.start_conversion)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        # Log Area
        log_frame = ttk.LabelFrame(main_frame, text="Log Output", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log_area = scrolledtext.ScrolledText(log_frame, state='disabled', height=15)
        self.log_area.pack(fill=tk.BOTH, expand=True)
        self.log_area.tag_config("stderr", foreground="red")

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
        threading.Thread(target=self.run_conversion, daemon=True).start()

    def run_conversion(self):
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
            # Open the file
            os.startfile(out_ppt_file)
            messagebox.showinfo("Success", f"Conversion complete!\nFile saved to: {out_ppt_file}")
        except Exception as e:
            print(f"\nError occurred: {str(e)}")
            messagebox.showerror("Error", f"An error occurred during conversion: {str(e)}")
        finally:
            self.start_btn.config(state=tk.NORMAL)

def launch_gui():
    root = tk.Tk()
    app = AppGUI(root)
    root.mainloop()

if __name__ == "__main__":
    launch_gui()
