"""Explicit, reversible preparation followed by a confirmed BOOTSEL flash."""
from tkinter import ttk, messagebox
import tkinter as tk
from installer import Installer


class InstallDialog:
    def __init__(self,app,root_path):
        self.app,self.root_path=app,root_path
        self.prepared,self.installer=None,None
        self.window=tk.Toplevel(app.root)
        self.window.title('Install new Pico 2 W'); self.window.geometry('720x620'); self.window.minsize(700,600)
        self.window.protocol('WM_DELETE_WINDOW',self.close)
        frame=ttk.Frame(self.window,padding=16); frame.pack(fill='both',expand=True)
        ttk.Label(frame,text='Install firmware on a Pico 2 W',font=('Segoe UI',15,'bold')).pack(anchor='w')
        instructions=('1. Unplug other Pico boards. Check this board’s printed Pico 2 W label.\n'
                      '2. Hold BOOTSEL while connecting a USB data cable, then release it.\n'
                      '3. Choose firmware and prepare a verified full-flash backup.\n'
                      '4. Review the detected identity before confirming installation.\n\n'
                      'RP2350 identification alone cannot prove the wireless board model.\n'
                      'A new/unknown remote needs diagnostics before its inputs can be translated.')
        ttk.Label(frame,text=instructions,wraplength=650,justify='left').pack(anchor='w',pady=12)
        self.physical=tk.BooleanVar(value=False)
        ttk.Checkbutton(frame,text='I checked the printed model: this is a Pico 2 W.',variable=self.physical,command=self.invalidate).pack(anchor='w')
        ttk.Label(frame,text='Firmware:').pack(anchor='w',pady=(12,2))
        self.profile=ttk.Combobox(frame,state='readonly',values=('MR25GA — keyboard / mouse / media','Different or unknown remote — serial diagnostic only'))
        self.profile.current(0); self.profile.pack(fill='x'); self.profile.bind('<<ComboboxSelected>>',lambda event:self.invalidate())
        self.status=tk.StringVar(value='Nothing will be written until a verified backup exists and you confirm Install.')
        ttk.Label(frame,textvariable=self.status,wraplength=650,justify='left').pack(anchor='w',pady=12)
        row=ttk.Frame(frame); row.pack(fill='x')
        ttk.Button(row,text='Inspect Pico and back up',command=self.prepare).pack(side='left')
        self.flash_button=ttk.Button(row,text='Install verified firmware…',command=self.flash,state='disabled')
        self.flash_button.pack(side='left',padx=8)
        self.next_button=ttk.Button(frame,text='Next: connect USB in companion',command=self.next,state='disabled')
        self.next_button.pack(anchor='w',pady=12)
        ttk.Label(frame,text='Backup covers external flash, not RAM or OTP. It belongs to this board only. No erase, remote update, OTP or vendor commands are used.',wraplength=650).pack(anchor='w')

    def invalidate(self):
        self.prepared=None; self.flash_button.configure(state='disabled')
        self.status.set('Selection changed. Inspect and back up this Pico before installing.')

    def prepare(self):
        if self.app.busy: return
        if not self.physical.get():
            messagebox.showinfo('Check board label','Check the printed Pico 2 W model and tick the confirmation first.',parent=self.window); return
        self.invalidate(); hid=self.profile.current()==0
        if self.app.bridge:
            self.app.bridge.close(); self.app.bridge=None
            self.app.usb.set('USB serial closed for installation; reconnect after reboot')
        self.status.set('Checking identity and firmware, then reading/verifying all 4 MB of external flash. Please wait.')
        def run():
            self.installer=Installer(self.root_path)
            return self.installer.prepare(hid)
        def ready(prepared):
            self.app.note(f'Installer backup verified: {prepared.backup}')
            if not self.window.winfo_exists(): return
            if self.profile.current()!=(0 if prepared.hid else 1) or not self.physical.get():
                self.status.set('Backup is safe, but the selection changed. Inspect and back up again before installation.'); return
            self.prepared=prepared
            self.status.set(f'Pico: {prepared.serial}\nImage: {prepared.firmware.name}\nFull-flash backup verified: {prepared.backup.name}\nBackup SHA-256: {prepared.backup_hash}')
            self.flash_button.configure(state='normal')
        self.app.work(run,ready)

    def flash(self):
        prepared=self.prepared
        if self.app.busy or not prepared or not self.physical.get(): return
        if prepared.hid!=(self.profile.current()==0):
            self.invalidate(); return
        text=(f'Write {prepared.firmware.name} to Pico {prepared.serial}?\n\n'
              f'Existing flash is backed up and verified in:\n{prepared.backup}\n\n'
              'This replaces its application. RAM and OTP cannot be restored from this backup. Only proceed for the physically checked Pico 2 W.')
        if not messagebox.askokcancel('Install on this Pico',text,parent=self.window): return
        self.prepared=None; self.flash_button.configure(state='disabled')
        self.status.set('Rechecking board, image and backup, then writing and verifying. Keep USB connected.')
        def done(result):
            self.app.note(result)
            if not self.window.winfo_exists(): return
            self.status.set(result+'\n\nWait for USB to enumerate, then connect USB in the companion and use Pair remote. For an existing saved pair, press an ordinary arrow; do not unregister again.')
            self.next_button.configure(state='normal')
        self.app.work(lambda:self.installer.flash(prepared),done)

    def next(self):
        self.window.destroy(); self.app.connect()

    def close(self):
        if self.app.busy:
            messagebox.showinfo('Operation in progress','Wait for the backup/write operation to finish before closing.',parent=self.window); return
        self.window.destroy()