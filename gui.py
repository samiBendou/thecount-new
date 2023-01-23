import os
import tkinter as tk
from tkinter import filedialog as fd
from tkinter import ttk


class FilePickerFrame(tk.Frame):
    var_file: tk.Variable
    label: tk.Label
    entry: tk.Entry
    button: tk.Button

    def __init__(self, root, name, initial=None):
        super().__init__(root)
        cwd = os.getcwd()
        initial = initial if initial is not None else ""
        self.var_file = tk.StringVar(
            root, value=f"{cwd}{os.path.sep}{initial}")
        self.label = ttk.Label(self, text=name,  width=20)
        self.entry = ttk.Entry(self, textvariable=self.var_file)
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
            self.var_file.set(filename)

    def filename(self):
        return self.var_file.get()


class CheckFrame(tk.Frame):
    var_check: tk.Variable
    label: tk.Label
    check: tk.Checkbutton

    def __init__(self, root, name, intial=True):
        super().__init__(root)
        self.var_check = tk.BooleanVar(root, value=intial)
        self.label = ttk.Label(self, text=name)
        self.check = ttk.Checkbutton(self, variable=self.var_check)

        self.label.pack(side=tk.LEFT)
        self.check.pack(side=tk.RIGHT)

    def is_checked(self):
        return self.var_check.get()


class ConfigurationBarFrame(tk.Frame):
    last_month_check: CheckFrame
    backup_check: CheckFrame

    def __init__(self, root):
        super().__init__(root)
        self.last_month_check = CheckFrame(self, "Only last month")
        self.backup_check = CheckFrame(self, "Backup current data")
        self.last_month_check.pack(side=tk.LEFT)
        self.backup_check.pack(side=tk.LEFT)


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
    config_bar: ConfigurationBarFrame
    action_bar: ActionBarFrame

    def __init__(self, on_merge, on_synthetize, on_quit):
        self.root = tk.Tk()
        self.root.title("Select a transactions record")

        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.root.protocol("WM_DELETE_WINDOW", on_quit)

        self.import_picker = FilePickerFrame(
            self.root, "Import record")
        self.import_picker.pack(fill=tk.BOTH)

        self.current_picker = FilePickerFrame(
            self.root, "Current record")
        self.current_picker.pack(fill=tk.BOTH)

        self.config_bar = ConfigurationBarFrame(self.root)
        self.config_bar.pack()

        self.progress_bar = ttk.Progressbar(self.root, value=0)
        self.progress_bar.pack(fill=tk.BOTH)

        self.action_bar = ActionBarFrame(self.root, on_merge=on_merge,
                                         on_synthetize=on_synthetize)
        self.action_bar.pack(pady=10)
