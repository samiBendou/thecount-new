import threading
import tkinter as tk
import traceback
from tkinter import messagebox

from core import *
from gui import Window
from plot import render_synthesis


class App:
    import_account: Account | None
    current_account: Account | None
    export_account: Account | None

    thread: threading.Thread | None

    window: Window

    def __init__(self) -> None:
        self.import_account = None
        self.current_account = None
        self.export_account = None

        self.thread = None

        self.window = Window(self.on_merge, self.on_synthetize, self.on_quit)

    def on_merge(self):
        backup = self.window.config_bar.backup_check.is_checked()
        self._do_merge(backup)

    def on_synthetize(self):
        only_last_month = self.window.config_bar.last_month_check.is_checked()
        backup = self.window.config_bar.backup_check.is_checked()
        self.window.action_bar.button_synthetize["state"] = tk.DISABLED
        self.window.action_bar.button_merge["state"] = tk.DISABLED

        self._do_merge(backup)

        if self.thread is not None:
            self.thread.join()

        self.thread = threading.Thread(
            target=self._do_synthetize, args=(only_last_month,))
        self.thread.start()

    def on_quit(self):
        self.window.root.destroy()

    def _do_synthetize(self, only_last_month: bool):
        end_date = self.export_account.ended_at()
        start_date = self.export_account.started_at()
        days = 1
        dates = make_linear_date(start_date, end_date, days)
        month_scale = make_accounting_term_dates(start_date, end_date)
        self.window.progress_bar.step(amount=-100)

        progress = 100 if only_last_month else 1/len(month_scale)*100
        render_synthesis(self.export_account, dates)
        self.window.progress_bar.step(amount=progress)

        all_periods = list(zip(month_scale, month_scale[1:]))
        periods = [all_periods[-1]] if only_last_month else all_periods
        for start, end in periods:
            dates = make_linear_date(start, end, days)
            render_synthesis(self.export_account, dates)
            self.window.progress_bar.step(amount=progress)

        messagebox.showinfo(
            "Done", f"Successfully generated synthesis reports from {start_date.isoformat()} to {end_date.isoformat()}")

        self.window.action_bar.button_synthetize["state"] = tk.NORMAL
        self.window.action_bar.button_merge["state"] = tk.NORMAL

    def _do_merge(self, backup: bool):
        try:
            import_filename = self.window.import_picker.filename()
            import_file = read_xls_file(import_filename)
            self.import_account = Account.parse_import(import_file)

            current_filename = self.window.current_picker.filename()
            current_file = read_csv_file(current_filename)
            self.current_account = Account.parse_current(current_file)

        except Exception as e:
            traceback.print_exception(e)
            messagebox.showerror("Unable to read files", f"{e}")
            return

        try:
            if backup:
                backup_filename = current_filename + ".backup"
                current_rows = self.current_account.to_export()
                write_csv_file(backup_filename, current_rows)

            self.export_account = self.current_account.merge(
                self.import_account)
            export_rows = self.export_account.to_export()

            write_csv_file(current_filename, export_rows)
        except Exception as e:
            traceback.print_exception(e)
            messagebox.showerror("Unable to write files", f"{e}")
            return

        msg = f"Successfully merged {len(self.import_account.transactions)} transactions !"
        messagebox.showinfo("Done", msg)
