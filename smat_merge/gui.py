import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import numpy as np
import skrf as rf
from .reconstruct_nport import reconstruct_from_networks

class SMatMergeApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("S-Matrix Merger")
        self.geometry("800x600")

        self.files = []
        self.file_widgets = []

        # --- Main frame ---
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Controls ---
        controls_frame = ttk.LabelFrame(main_frame, text="Controls", padding="10")
        controls_frame.pack(fill=tk.X, pady=5)

        ttk.Label(controls_frame, text="Number of Ports (N):").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.n_ports_var = tk.IntVar(value=5)
        self.n_ports_spinbox = ttk.Spinbox(controls_frame, from_=2, to=99, textvariable=self.n_ports_var, width=5, command=self.update_port_checkboxes)
        self.n_ports_spinbox.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        self.add_files_button = ttk.Button(controls_frame, text="Add Touchstone Files", command=self.add_files)
        self.add_files_button.grid(row=0, column=2, padx=5, pady=5)

        # --- File List ---
        self.files_frame = ttk.LabelFrame(main_frame, text="Input Files", padding="10")
        self.files_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.canvas = tk.Canvas(self.files_frame)
        self.scrollbar = ttk.Scrollbar(self.files_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # --- Output ---
        output_frame = ttk.LabelFrame(main_frame, text="Output", padding="10")
        output_frame.pack(fill=tk.X, pady=5)

        ttk.Label(output_frame, text="Output File:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.output_file_var = tk.StringVar()
        self.output_file_entry = ttk.Entry(output_frame, textvariable=self.output_file_var, width=60)
        self.output_file_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.browse_output_button = ttk.Button(output_frame, text="Browse...", command=self.browse_output)
        self.browse_output_button.grid(row=0, column=2, padx=5, pady=5)
        output_frame.columnconfigure(1, weight=1)

        # --- Actions ---
        actions_frame = ttk.Frame(main_frame, padding="10")
        actions_frame.pack(fill=tk.X)

        self.merge_button = ttk.Button(actions_frame, text="Merge", command=self.merge_files)
        self.merge_button.pack(side=tk.RIGHT)

    def add_files(self):
        fnames = filedialog.askopenfilenames(
            title="Select Touchstone files",
            filetypes=(("Touchstone files", "*.s*p"), ("All files", "*.*"))
        )
        if fnames:
            for fname in fnames:
                if fname not in [f['path'] for f in self.files]:
                    self.files.append({'path': fname, 'ports': []})
            self.update_file_list()
            if len(self.files) == 1: # First file added
                self.update_default_output_path()

    def update_file_list(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.file_widgets = []

        n_ports = self.n_ports_var.get()

        for i, file_info in enumerate(self.files):
            file_frame = ttk.Frame(self.scrollable_frame)
            file_frame.pack(fill=tk.X, pady=2)

            label = ttk.Label(file_frame, text=os.path.basename(file_info['path']), width=30)
            label.pack(side=tk.LEFT, padx=5)

            ports_frame = ttk.Frame(file_frame)
            ports_frame.pack(side=tk.LEFT, padx=5)
            
            port_vars = []
            for j in range(n_ports):
                var = tk.BooleanVar(value=(j + 1) in file_info.get('ports', []))
                cb = ttk.Checkbutton(ports_frame, text=str(j + 1), variable=var)
                cb.pack(side=tk.LEFT)
                port_vars.append(var)

            remove_button = ttk.Button(file_frame, text="Remove", command=lambda i=i: self.remove_file(i))
            remove_button.pack(side=tk.RIGHT, padx=5)
            
            self.file_widgets.append({'frame': file_frame, 'port_vars': port_vars})

    def remove_file(self, index):
        self.files.pop(index)
        self.update_file_list()
        if not self.files:
            self.output_file_var.set("")
        elif index == 0:
            self.update_default_output_path()

    def update_port_checkboxes(self):
        self.save_port_selections()
        self.update_file_list()

    def save_port_selections(self):
        for i, file_info in enumerate(self.files):
            if i < len(self.file_widgets):
                selected_ports = []
                for j, var in enumerate(self.file_widgets[i]['port_vars']):
                    if var.get():
                        selected_ports.append(j + 1)
                file_info['ports'] = selected_ports

    def update_default_output_path(self):
        if not self.files:
            return
        
        first_file_path = self.files[0]['path']
        folder = os.path.dirname(first_file_path)
        n_ports = self.n_ports_var.get()
        
        default_name = f"reconstructed_{n_ports}port.s{n_ports}p"
        output_path = os.path.join(folder, default_name)

        # Ensure no conflict
        input_basenames = [os.path.basename(f['path']) for f in self.files]
        count = 1
        while os.path.basename(output_path) in input_basenames:
            default_name = f"reconstructed_{n_ports}port_{count}.s{n_ports}p"
            output_path = os.path.join(folder, default_name)
            count += 1
            
        self.output_file_var.set(output_path)

    def browse_output(self):
        n_ports = self.n_ports_var.get()
        initial_dir = ""
        if self.output_file_var.get():
            initial_dir = os.path.dirname(self.output_file_var.get())

        fname = filedialog.asksaveasfilename(
            title="Save Merged S-Matrix",
            initialdir=initial_dir,
            initialfile=f"reconstructed_{n_ports}port.s{n_ports}p",
            defaultextension=f".s{n_ports}p",
            filetypes=[(f"{n_ports}-port Touchstone", f"*.s{n_ports}p"), ("All files", "*.*")]
        )
        if fname:
            self.output_file_var.set(fname)

    def merge_files(self):
        self.save_port_selections()
        n_ports = self.n_ports_var.get()
        output_file = self.output_file_var.get()

        if not self.files:
            messagebox.showerror("Error", "No input files selected.")
            return
        
        if not output_file:
            messagebox.showerror("Error", "Output file not specified.")
            return

        networks = []
        port_sets = []
        all_used_ports = set()

        for file_info in self.files:
            if not file_info['ports']:
                messagebox.showerror("Error", f"No ports defined for {os.path.basename(file_info['path'])}.")
                return
            
            if len(file_info['ports']) == n_ports:
                 if not messagebox.askyesno("Consistency Check", f"All {n_ports} ports are selected for {os.path.basename(file_info['path'])}.\nThis file might already be a full {n_ports}-port network. Do you want to continue?"):
                     return

            try:
                net = rf.Network(file_info['path'])
                net.name = os.path.basename(file_info['path'])
                networks.append(net)
                port_sets.append(tuple(file_info['ports']))
                all_used_ports.update(file_info['ports'])
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load {file_info['path']}:\n{e}")
                return

        # Consistency check: all ports covered
        all_possible_ports = set(range(1, n_ports + 1))
        if all_used_ports != all_possible_ports:
            missing_ports = all_possible_ports - all_used_ports
            if not messagebox.askyesno("Consistency Check", f"The following ports are not covered by any input file: {sorted(list(missing_ports))}.\nThe resulting S-parameters for these ports will be zero. Do you want to continue?"):
                return

        try:
            full_net, counts = reconstruct_from_networks(networks, port_sets, n_ports=n_ports)
            
            # Check for conflicts before writing
            if os.path.abspath(output_file) in [os.path.abspath(f['path']) for f in self.files]:
                 messagebox.showerror("Error", "Output file cannot be the same as one of the input files.")
                 return

            full_net.write_touchstone(filename=output_file, form='ri')
            
            msg = f"Successfully merged {len(self.files)} files into '{os.path.basename(output_file)}'.\n\n"
            msg += "Contributions to each S_ij:\n"
            msg += str(counts)
            messagebox.showinfo("Success", msg)

        except Exception as e:
            messagebox.showerror("Merge Error", f"An error occurred during merging:\n{e}")


if __name__ == "__main__":
    app = SMatMergeApp()
    app.mainloop()
