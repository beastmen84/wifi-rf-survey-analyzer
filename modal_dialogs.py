import tkinter as tk


class ModalDialogMixin:
    def create_modal_dialog(self, title):
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        self.register_modal_dialog(dialog)
        return dialog

    def register_modal_dialog(self, dialog):
        self.modal_dialogs.append(dialog)

        def forget_dialog(_event=None):
            self.modal_dialogs = [
                existing_dialog
                for existing_dialog in self.modal_dialogs
                if existing_dialog is not dialog and existing_dialog.winfo_exists()
            ]

        dialog.bind("<Destroy>", forget_dialog, add="+")

    def get_active_modal_dialog(self):
        for dialog in reversed(self.modal_dialogs):
            if dialog.winfo_exists():
                return dialog

        return None

    def bring_dialog_to_front(self, dialog):
        if not dialog or not dialog.winfo_exists():
            return

        dialog.deiconify()
        dialog.lift(self.root)
        try:
            dialog.attributes("-topmost", True)
            dialog.after(150, lambda: dialog.winfo_exists() and dialog.attributes("-topmost", False))
        except tk.TclError:
            pass
        dialog.focus_force()

    def restore_active_modal_dialog(self, _event=None):
        dialog = self.get_active_modal_dialog()
        if dialog is not None:
            self.root.after(50, lambda: self.bring_dialog_to_front(dialog))

    def center_dialog(self, dialog):
        dialog.update_idletasks()

        parent_x = self.root.winfo_rootx()
        parent_y = self.root.winfo_rooty()
        parent_width = self.root.winfo_width()
        parent_height = self.root.winfo_height()
        dialog_width = dialog.winfo_width()
        dialog_height = dialog.winfo_height()

        if parent_width <= 1 or parent_height <= 1:
            parent_x = 0
            parent_y = 0
            parent_width = self.root.winfo_screenwidth()
            parent_height = self.root.winfo_screenheight()

        x = parent_x + max(0, (parent_width - dialog_width) // 2)
        y = parent_y + max(0, (parent_height - dialog_height) // 2)
        dialog.geometry(f"+{x}+{y}")
        self.bring_dialog_to_front(dialog)
