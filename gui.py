import os
import tkinter as tk
from tkinter import filedialog as fd
from tkinter import ttk


class FilePickerFrame(tk.Frame):
    filevar: tk.Variable
    label: tk.Label
    entry: tk.Entry
    button: tk.Button

    def __init__(self, root, name, initial=None):
        super().__init__(root)
        cwd = os.getcwd()
        initial = initial if initial is not None else ""
        self.filevar = tk.StringVar(root, value=f"{cwd}{os.path.sep}{initial}")
        self.label = ttk.Label(self, text=name,  width=20)
        self.entry = ttk.Entry(self, textvariable=self.filevar)
        self.button = ttk.Button(self, text="Select a file",
                                 command=self._select_file)

        self.label.pack(side=tk.LEFT)
        self.entry.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        self.button.pack(side=tk.RIGHT)

    def _select_file(self):
        cwd = os.getcwd()

        filetypes = (
            ('CSV Files', '*.csv'),
            ('CSV Files', '*.xls'),
            ('CSV Files', '*.xlsx'),
            ('All files', '*.*')
        )

        filename = fd.askopenfilename(
            title="Open a file",
            initialdir=cwd,
            filetypes=filetypes)

        if filename is not None and filename != "":
            self.filevar.set(filename)

    def filename(self):
        return self.filevar.get()


class ActionBarFrame(tk.Frame):
    button_merge: tk.Button
    button_synthetize: tk.Button

    def __init__(self, root, on_merge, on_synthetize):
        super().__init__(root)

        self.button_merge = ttk.Button(self, text="Merge records",
                                       command=on_merge)
        self.button_synthetize = ttk.Button(self, text="Synthetize records",
                                            command=on_synthetize)

        self.button_merge.pack(side=tk.LEFT)
        self.button_synthetize.pack(side=tk.RIGHT)


class Window:
    root: tk.Tk
    progress_bar: ttk.Progressbar
    import_picker: FilePickerFrame
    current_picker: FilePickerFrame
    action_bar: ActionBarFrame

    def __init__(self, on_merge, on_synthetize, on_quit):
        self.root = tk.Tk()
        self.root.title("Select a transactions record")
        self.root.geometry("900x120")
        self.root.resizable(width=False, height=False)
        self.root.protocol("WM_DELETE_WINDOW", on_quit)

        self.import_picker = FilePickerFrame(
            self.root, "Import record")
        self.import_picker.pack(fill=tk.BOTH)

        self.current_picker = FilePickerFrame(
            self.root, "Current record")
        self.current_picker.pack(fill=tk.BOTH)

        self.progress_bar = ttk.Progressbar(self.root, value=0)
        self.progress_bar.pack(fill=tk.BOTH)

        self.action_bar = ActionBarFrame(self.root, on_merge=on_merge,
                                         on_synthetize=on_synthetize)
        self.action_bar.pack()
