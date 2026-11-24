"""Local Tk desktop companion. Firmware works independently when this is closed."""

from pathlib import Path

import queue

import re

import threading

import time

import tkinter as tk

from tkinter import ttk, messagebox, simpledialog

from decimal import Decimal

import json

from manage import Bridge, choose_port, pairing_result

from timeout_settings import TIMEOUT_CHOICES,timeout_label,read_timeout,save_timeout,timeout_choices_for_version

from connection_events import ConnectionTimeline,parse_event,read_history,uptime_label

from output_mappings import OUTPUTS,describe,read_mappings,save_mapping,restore_mappings

from install_dialog import InstallDialog

from host_actions import runtime_directory,validate_request,write_json,perform_mouse_on,REQUEST_NAME



ROOT = Path(__file__).resolve().parent

BUTTONS = {0x8040:'Up arrow',0x8041:'Down arrow',0x8007:'Left arrow',0x8006:'Right arrow',

           0x8044:'Wheel / OK',0x8028:'Back / Return',0x807C:'Home (house)',

           0x8002:'Volume +',0x8003:'Volume −',0x8000:'Channel +',0x8001:'Channel −',

           0x808B:'AI / Voice',0x8029:'Screen with question mark',

           0x80A1:'Home inside a circle',0x80AB:'Guide',0x8045:'123',0x8043:'Select / Settings'}

BUTTONS.update({code:f'Streaming shortcut {i}' for i,code in enumerate((0x8056,0x805C,0x8031,0x8049,0x8048,0x800C),1)})

ACTIONS = {0x8040:'Up arrow',0x8041:'Down arrow',0x8007:'Left arrow',0x8006:'Right arrow',

           0x8044:'Enter',0x8028:'Escape',0x807C:'Windows / Start (Left GUI)',

           0x8002:'F23',0x8003:'F24',0x8000:'Volume Up (media key)',

           0x8001:'Volume Down (media key)',0x808B:'Toggle pointer; no Windows key'}

ACTIONS.update(dict(zip((0x8056,0x805C,0x8031,0x8049,0x8048,0x800C,0x8029,0x80A1,0x80AB,0x8045,0x8043),

                        (f'F{i}' for i in range(13,24)))))

ACTIONS[0x8043]='F12'  # Settings frees F23 for dedicated TV volume.





def windows_action(code, pointer=False):

    if code==0x8044 and pointer: return 'Left mouse button (click; hold to drag)'

    return ACTIONS.get(code,'Unmapped; no Windows key')





def load_labels(path):

    """Local display labels only; cannot alter the firmware mappings."""

    try:

        if path.stat().st_size>16384: return {}

        data=json.loads(path.read_text(encoding='utf-8'))

        if not isinstance(data,dict): return {}

        return {int(code,16):label for code,label in data.items()

                if isinstance(code,str) and re.fullmatch('[0-9A-Fa-f]{4}',code)

                and int(code,16) in BUTTONS and isinstance(label,str)

                and 0<len(label)<=64 and all(c.isprintable() for c in label)}

    except (OSError,ValueError): return {}





def input_report(line):

    """Decode only the verified complete report; no inferred battery field."""

    match = re.search(r'\bREPORT .*id=FD len=20 offset=0 data=([0-9A-F]{40})\b', line)

    if not match:

        return None

    data = bytes.fromhex(match[1])

    if data[0] != 0xFD:

        return None

    return int.from_bytes(data[17:19], 'big'), int.from_bytes(data[19:], 'big', signed=True)





def power_description(line):

    match=re.search(r'\bPOWER state=(usb_off|idle|awake) .*?idle_ms=(\d+) limit_ms=(\d+).*?enabled=([01])',line)

    if not match: return None

    mode,elapsed,limit,enabled=match.groups()

    if mode=='usb_off': return 'Bluetooth: paused — USB host unavailable'

    if mode=='idle': return 'Bluetooth: idle pause — press a remote button to reconnect'

    if enabled=='0': return 'Bluetooth: available — idle pause disabled for this session'

    seconds=max(0,(int(limit)-int(elapsed)+999)//1000)

    countdown=(f'{seconds//3600}:{seconds//60%60:02d}:{seconds%60:02d}' if seconds>=3600 else f'{seconds//60}:{seconds%60:02d}')
    return f'Bluetooth: available — idle pause in {countdown}'





class Companion:

    def __init__(self, root):

        self.root, self.bridge = root, None

        self.events = queue.Queue()

        self.mark, self.code, self.last_report = 0, 0, 0

        self.busy, self.pair_window, self.closing = False, None, False

        self.load_gain = True

        self.pointer_mode=False

        self.device_mappings=None

        self.mapping_required=False

        self.legacy_defaults=False

        self.install_window=None

        self.timeout_supported=False;self.history_supported=False;self.timeout_loaded=False

        self.timeline=ConnectionTimeline();self.next_status_poll=0;self.next_history_poll=0

        self.labels=load_labels(ROOT/'companion-labels.json')

        root.title('LG Remote · Pico 2 W')

        root.geometry('800x680'); root.minsize(740,640)

        root.protocol('WM_DELETE_WINDOW', self.close)

        outer = ttk.Frame(root, padding=16); outer.pack(fill='both', expand=True)

        ttk.Label(outer, text='LG Remote Companion', font=('Segoe UI',18,'bold')).pack(anchor='w')

        ttk.Label(outer, text='Local setup and diagnostics · optional during normal use').pack(anchor='w', pady=(0,12))

        self.usb = tk.StringVar(value='USB: disconnected')

        self.firmware = tk.StringVar(value='Firmware: unknown · tested profile: MR25GA')

        self.remote = tk.StringVar(value='Remote: unknown')

        self.peer = tk.StringVar(value='Saved peer: unknown')

        self.active = tk.StringVar(value='Active peer: none')

        self.power = tk.StringVar(value='Bluetooth power policy: awaiting status')

        self.mouse = tk.StringVar(value='Pointer: unknown')

        self.activity = tk.StringVar(value='Input: waiting')

        for value in (self.usb,self.remote,self.power,self.mouse,self.activity):

            ttk.Label(outer, textvariable=value, wraplength=710).pack(anchor='w', pady=2)

        row = ttk.Frame(outer); row.pack(fill='x',pady=12)

        ttk.Button(row,text='Connect USB',command=self.connect).pack(side='left')

        ttk.Button(row,text='Install new Pico…',command=self.show_install).pack(side='left',padx=6)

        ttk.Button(row,text='Pair remote…',command=self.pair_dialog).pack(side='left',padx=6)

        ttk.Button(row,text='Resume remote',command=lambda:self.command('resume')).pack(side='left')

        settings = ttk.LabelFrame(outer,text='Pointer',padding=10); settings.pack(fill='x')

        ttk.Label(settings,text='Speed (gain 1–100):').pack(side='left')

        self.gain=tk.StringVar(value='12.500')

        ttk.Entry(settings,textvariable=self.gain,width=9).pack(side='left',padx=6)

        ttk.Button(settings,text='Save speed',command=self.save_gain).pack(side='left')

        ttk.Button(settings,text='Calibrate…',command=self.calibrate).pack(side='left',padx=6)

        ttk.Button(settings,text='Pointer off',command=lambda:self.command('mouse off')).pack(side='left')

        ttk.Label(outer,text='Idle disconnect also clears pointer · Wake: pickup/button. Battery level is not validated.',wraplength=710).pack(anchor='w',pady=(8,10))

        ttk.Label(outer,text='Local event logs: logs/companion-*.txt · Close other serial utilities first.',wraplength=740).pack(side='bottom',anchor='w',pady=(8,0))

        tabs=ttk.Notebook(outer); tabs.pack(fill='both',expand=True)

        live_tab=ttk.Frame(tabs,padding=8); mapping_tab=ttk.Frame(tabs,padding=8)

        tabs.add(live_tab,text='Live input'); tabs.add(mapping_tab,text='Button mappings')

        output_tab=ttk.Frame(tabs,padding=10); tabs.add(output_tab,text='Output keys'); self.init_output_tab(output_tab)

        connection_tab=ttk.Frame(tabs,padding=10);tabs.add(connection_tab,text='Connection');self.init_connection_tab(connection_tab)

        device_tab=ttk.Frame(tabs,padding=12);tabs.add(device_tab,text='Device info')

        for value in (self.firmware,self.peer,self.active):

            ttk.Label(device_tab,textvariable=value,wraplength=710).pack(anchor='w',pady=5)

        ttk.Label(device_tab,text='LED on = Bluetooth link connected. HID input setup can finish later. Power remains TV IR.',wraplength=710).pack(anchor='w',pady=12)

        self.live=tk.StringVar(value='Remote button: none held')

        self.output=tk.StringVar(value='Windows action: none')

        self.raw_code=tk.StringVar(value='Remote code: —')

        for value in (self.live,self.output,self.raw_code):

            ttk.Label(live_tab,textvariable=value,wraplength=680).pack(anchor='w',pady=2)

        self.log=tk.Text(live_tab,height=6,wrap='word',state='disabled',font=('Consolas',10))

        self.log.pack(fill='both',expand=True,pady=(6,0))

        columns=('button','action','code')

        self.mapping_tree=ttk.Treeview(mapping_tab,columns=columns,show='headings',height=6)

        for key,title,width in (('button','Button on remote',240),('action','Windows action',270),('code','Code',65)):

            self.mapping_tree.heading(key,text=title); self.mapping_tree.column(key,width=width,minwidth=50)

        scroll=ttk.Scrollbar(mapping_tab,orient='vertical',command=self.mapping_tree.yview)

        self.mapping_tree.configure(yscrollcommand=scroll.set)

        scroll.pack(side='right',fill='y'); self.mapping_tree.pack(fill='both',expand=True)

        ttk.Button(mapping_tab,text='Rename selected button label…',command=self.rename_button).pack(anchor='w',pady=(6,0))

        self.mapping_tree.bind('<Double-1>',lambda event:self.rename_button())

        self.populate_mappings()

        self.root.after(100,self.tick)





    def init_connection_tab(self,tab):

        settings=ttk.LabelFrame(tab,text='Inactivity disconnect (saved on Pico)',padding=8);settings.pack(fill='x')

        self.timeout_value=tk.StringVar(value=timeout_label(90))

        self.timeout_choice=ttk.Combobox(settings,textvariable=self.timeout_value,values=list(TIMEOUT_CHOICES),state='disabled',width=18)

        self.timeout_choice.pack(side='left')

        self.timeout_read_button=ttk.Button(settings,text='Read',state='disabled',command=self.load_timeout);self.timeout_read_button.pack(side='left',padx=6)

        self.timeout_save_button=ttk.Button(settings,text='Save timeout',state='disabled',command=self.save_idle_timeout);self.timeout_save_button.pack(side='left')

        self.timeout_status=tk.StringVar(value='Connect USB. Editing requires HID firmware 0.21 or newer.')

        ttk.Label(tab,textvariable=self.timeout_status,wraplength=680).pack(anchor='w',pady=(6,10))

        ttk.Label(tab,text='Connection history · Pico keeps the last 32 events in RAM while powered. Uptime is measured since Pico boot.',wraplength=680).pack(anchor='w')

        columns=('boot','uptime','event','detail')

        self.history_read_button=ttk.Button(tab,text='Refresh history',state='disabled',command=self.load_history);self.history_read_button.pack(side='bottom',anchor='w')

        tree_frame=ttk.Frame(tab);tree_frame.pack(fill='both',expand=True,pady=6)

        self.connection_tree=ttk.Treeview(tree_frame,columns=columns,show='headings',height=5)

        for key,title,width in [('boot','Boot',65),('uptime','Pico uptime',110),('event','Event',215),('detail','Details',270)]:

            self.connection_tree.heading(key,text=title);self.connection_tree.column(key,width=width,minwidth=45)

        scrollbar=ttk.Scrollbar(tree_frame,orient='vertical',command=self.connection_tree.yview)

        self.connection_tree.configure(yscrollcommand=scrollbar.set);scrollbar.pack(side='right',fill='y')

        self.connection_tree.pack(side='left',fill='both',expand=True)



    def timeout_loaded_from_pico(self,setting):

        if setting is None:

            self.timeout_supported=False;self.timeout_choice.configure(state='disabled');self.timeout_save_button.configure(state='disabled')

            self.timeout_status.set('This image does not support editable HID inactivity settings.');return

        self.timeout_loaded=True;self.timeout_value.set(timeout_label(setting.seconds))

        self.timeout_status.set(f'Pico timeout: {timeout_label(setting.seconds)} · '+('saved in flash' if setting.source=='flash' else 'factory default'))



    def load_timeout(self):

        if self.bridge and not self.busy and self.timeout_supported:

            self.work(lambda:read_timeout(self.bridge),self.timeout_loaded_from_pico)



    def save_idle_timeout(self):

        if not self.bridge or self.busy or not self.timeout_supported: return

        seconds=TIMEOUT_CHOICES.get(self.timeout_value.get())

        if seconds is None: return

        def done(setting):

            self.timeout_loaded_from_pico(setting)

            self.timeout_status.set(self.timeout_status.get()+' · flash readback verified. A new countdown starts if connected.')

            self.note(f'Inactivity timeout saved on Pico: {timeout_label(setting.seconds)}')

        self.work(lambda:save_timeout(self.bridge,seconds),done)



    def render_connection_history(self):

        self.connection_tree.delete(*self.connection_tree.get_children())

        for event in self.timeline.events():

            self.connection_tree.insert('', 'end', values=(event.boot[-4:],uptime_label(event.uptime_ms),event.label,event.description))

        rows=self.connection_tree.get_children()

        if rows: self.connection_tree.see(rows[-1])



    def accept_connection_event(self,event):

        if not self.timeline.add(event): return False

        if self.bridge: self.bridge.record('CONNECTION',f'boot={event.boot} seq={event.sequence} {uptime_label(event.uptime_ms)} {event.label}: {event.description}')

        return True



    def history_loaded(self,events):

        for event in events: self.accept_connection_event(event)

        self.render_connection_history()



    def load_history(self):

        if self.bridge and not self.busy and self.history_supported:

            self.next_history_poll=time.monotonic()+10

            self.work(lambda:read_history(self.bridge),self.history_loaded)



    def show_install(self):

        if self.busy: return

        if self.install_window and self.install_window.window.winfo_exists():

            self.install_window.window.lift(); return

        self.install_window=InstallDialog(self,ROOT)



    def effective_action(self,code,pointer=False):

        if code==0x8044 and pointer:
            return 'Left mouse button (click; hold to drag)' if getattr(self,'drag_supported',False) else 'Left mouse click'

        if self.device_mappings is not None:

            if code not in self.device_mappings: return 'Unmapped; no Windows key'

            action=self.device_mappings[code]

            text=describe(action)

            if action==('key',0x6D): text+=' — AHK: double tap → TV off + PC shutdown'

            return text

        if self.mapping_required: return 'Mapping not read; use Read from Pico'

        if self.legacy_defaults and code in (0x8002,0x8003,0x8043):

            return {0x8002:'Page Up',0x8003:'Page Down',0x8043:'F23'}[code]

        return windows_action(code,pointer)



    def init_output_tab(self,tab):

        ttk.Label(tab,text='Save a button’s output on the Pico. Changes work with this window closed.',wraplength=670).pack(anchor='w')

        ttk.Label(tab,text='Physical button:').pack(anchor='w',pady=(10,2))

        self.edit_button=ttk.Combobox(tab,state='readonly'); self.edit_button.pack(fill='x')

        self.edit_button.bind('<<ComboboxSelected>>',lambda event:self.mapping_selection())

        ttk.Label(tab,text='Windows key / action:').pack(anchor='w',pady=(10,2))

        self.edit_output=ttk.Combobox(tab,state='readonly',values=list(OUTPUTS)); self.edit_output.pack(fill='x')

        row=ttk.Frame(tab); row.pack(fill='x',pady=10)

        ttk.Button(row,text='Read from Pico',command=self.load_mappings).pack(side='left')

        self.save_output_button=ttk.Button(row,text='Save button',command=self.save_output,state='disabled'); self.save_output_button.pack(side='left',padx=6)

        self.reset_output_button=ttk.Button(row,text='Restore all defaults…',command=self.reset_outputs,state='disabled'); self.reset_output_button.pack(side='left')

        self.mapping_status=tk.StringVar(value='Connect USB. Editing requires firmware 0.12 or newer with HID enabled.')

        ttk.Label(tab,textvariable=self.mapping_status,wraplength=670).pack(anchor='w')

        ttk.Label(tab,text='Single keys/media actions only. Wheel/OK always left-clicks in pointer mode. Wheel rotation and Power are fixed. Saving releases held inputs and switches the pointer off.',wraplength=670).pack(anchor='w',pady=10)



    def mapping_selection(self):

        index=self.edit_button.current()

        if index<0: return

        code=list(BUTTONS)[index]

        self.edit_output['values']=[name for name,action in OUTPUTS.items() if not(code==0x8044 and action[0]=='pointer')]

        if self.device_mappings is not None:

            self.edit_output.set(describe(self.device_mappings[code]))

        else: self.edit_output.set('')



    def mappings_loaded(self,result):

        self.device_mappings=result

        state='normal' if result is not None else 'disabled'

        self.save_output_button.configure(state=state); self.reset_output_button.configure(state=state)

        self.mapping_status.set('Mappings read from Pico. Select a button and output, then Save button.' if result is not None else 'This firmware has no editable mapping API. Install the 0.12 HID build to enable this tab.')

        self.populate_mappings()



    def load_mappings(self):

        if not self.bridge or self.busy: return

        self.work(lambda:read_mappings(self.bridge,set(BUTTONS)),self.mappings_loaded)



    def save_output(self):

        if not self.bridge or self.busy or self.device_mappings is None: return

        index=self.edit_button.current(); label=self.edit_output.get()

        if index<0 or label not in OUTPUTS:

            messagebox.showinfo('Choose output','Select a physical button and a named output.',parent=self.root); return

        code=list(BUTTONS)[index]; action=OUTPUTS[label]

        def done(result):

            self.mappings_loaded(result)

            self.mapping_status.set(f'{self.button_label(code)} → {label}: saved and flash readback verified. Pointer is off.')

            if not any(kind=='pointer' for kind,value in result.values()):

                self.mapping_status.set(self.mapping_status.get()+' No button currently toggles the pointer; assign one or restore defaults.')

            self.note(self.mapping_status.get())

        self.work(lambda:save_mapping(self.bridge,code,action,set(BUTTONS)),done)



    def reset_outputs(self):

        if not self.bridge or self.busy or self.device_mappings is None: return

        if not messagebox.askokcancel('Restore output defaults','Restore all original button outputs, including Home → Windows, volume rocker → F23/F24 TV volume, channel rocker → Windows volume, F13–F22 shortcuts and Settings → F12? Mouse speed, calibration and pairing will be kept.',parent=self.root): return

        self.work(lambda:restore_mappings(self.bridge,set(BUTTONS)),self.mappings_loaded)



    def button_label(self,code):

        return self.labels.get(code,BUTTONS.get(code,'Unknown physical button'))



    def populate_mappings(self):

        self.mapping_tree.delete(*self.mapping_tree.get_children())

        for code in BUTTONS:

            action=self.effective_action(code)

            if code==0x8044: action=self.effective_action(code,False)+' / left click in pointer mode'

            self.mapping_tree.insert('','end',iid=f'{code:04X}',values=(self.button_label(code),action,f'0x{code:04X}'))

        self.mapping_tree.insert('','end',iid='wheel',values=('Wheel rotation','Mouse wheel up / down','byte 19'))

        self.mapping_tree.insert('','end',iid='power',values=('Power','TV infrared; unmapped on Pico','—'))

        if hasattr(self,'edit_button'):

            selected=self.edit_button.current()

            self.edit_button['values']=[f'{self.button_label(code)} [0x{code:04X}]' for code in BUTTONS]

            self.edit_button.current(max(0,selected)); self.mapping_selection()



    def rename_button(self):

        selected=self.mapping_tree.selection()

        if not selected or not re.fullmatch('[0-9A-F]{4}',selected[0]): return

        code=int(selected[0],16)

        label=simpledialog.askstring('Remote button label','Printed name/icon (display only; Windows mapping stays unchanged):',

                                     initialvalue=self.button_label(code),parent=self.root)

        if label is None: return

        label=label.strip()

        if not 0<len(label)<=64 or not all(c.isprintable() for c in label):

            messagebox.showerror('Invalid label','Use 1–64 printable characters.',parent=self.root); return

        updated=dict(self.labels); updated[code]=label

        try:

            path=ROOT/'companion-labels.json'; temporary=path.with_suffix('.json.tmp')

            temporary.write_text(json.dumps({f'{key:04X}':value for key,value in updated.items()},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

            temporary.replace(path)

        except OSError as error:

            messagebox.showerror('Could not save label',str(error),parent=self.root); return

        self.labels=updated; self.populate_mappings()



    def note(self,text):

        self.log.configure(state='normal'); self.log.insert('end',text+'\n')

        if int(self.log.index('end-1c').split('.')[0])>150:

            self.log.delete('1.0','30.0')

        self.log.see('end'); self.log.configure(state='disabled')



    def work(self,fn,done=None):

        if self.busy:

            messagebox.showinfo('Working','Please wait for the current operation.',parent=self.root); return

        self.busy=True

        def run():

            try: self.events.put(('done',done,fn()))

            except Exception as error: self.events.put(('error',str(error)))

        threading.Thread(target=run,daemon=True).start()



    def connect(self):

        if self.bridge and not self.bridge.error:

            return

        def open_bridge():

            if self.bridge: self.bridge.close()

            (ROOT/'logs').mkdir(exist_ok=True)

            return Bridge(choose_port(None),ROOT/'logs'/time.strftime('companion-%Y%m%d-%H%M%S.txt'),quiet=True,log_reports=False)

        def opened(bridge):

            self.bridge=bridge; self.mark=0; self.code=0

            self.last_report=0; self.load_gain=True

            self.usb.set(f'USB: {bridge.port.device} · Pico {bridge.port.serial_number}')

            bridge.send('help'); bridge.send('status'); bridge.send('mouse status')

            self.device_mappings=None;self.timeout_loaded=False

            self.timeout_supported=False;self.history_supported=False;self.timeline=ConnectionTimeline();self.render_connection_history()

            self.next_status_poll=0;self.next_history_poll=0;self.load_mappings()

            self.note('USB connected. Press a Bluetooth button to wake the remote; the first press may only reconnect.')

        self.work(open_bridge,opened)



    def command(self,text):

        if self.bridge and not self.bridge.error and not self.busy:

            try: self.bridge.send(text)

            except Exception as error: self.note(str(error))



    def save_gain(self):

        try:

            value=Decimal(self.gain.get())

            if not value.is_finite() or not 1<=value<=100 or value.as_tuple().exponent < -3: raise ValueError()

        except Exception:

            messagebox.showerror('Invalid speed','Enter 1–100 with up to three decimal places.',parent=self.root); return

        if not self.bridge: return

        def save():

            mark=self.bridge.send(f'mouse gain {value:f}')

            result=self.bridge.wait(r'GYRO config store',mark)

            if 'readback=1' not in result: raise RuntimeError('Settings readback failed: '+result)

            self.bridge.send('mouse status')

            return 'Speed saved and flash readback verified.'

        self.work(save,self.note)



    def calibrate(self):

        if not self.bridge or self.busy: return

        if not messagebox.askokcancel('Still calibration','Wake the remote, place it flat on a stable table, then leave it untouched for at least five seconds.\n\nStart now?',parent=self.root): return

        def run():

            mark=self.bridge.send('calibrate')

            line=self.bridge.wait('GYRO calibration (PASS|REJECTED)',mark,timeout=30)

            self.bridge.send('mouse status'); return line

        self.work(run,self.note)



    def pair_dialog(self):

        if not self.bridge or self.busy:

            messagebox.showinfo('Connect first','Connect USB and wait for any operation to finish.',parent=self.root); return

        if self.pair_window and self.pair_window.winfo_exists():

            self.pair_window.lift(); return

        if self.bridge.port.pid==0x4005:

            model=simpledialog.askstring('Verify physical label','Enter the model printed on the remote. This HID firmware supports the tested MR25GA layout only.',parent=self.root)

            if model is None: return

            if (model or '').strip().upper()!='MR25GA':

                messagebox.showinfo('Diagnostic required','Use the CDC-only diagnostic for a different/unknown model. See PAIRING.md.',parent=self.root); return

        if not messagebox.askokcancel('Prepare pairing','Unplug the original TV at the wall. Confirm you can restore the remote to it: Back + Home five seconds, then point at the powered-on TV and press Wheel/OK.\n\nContinue only when recovery is understood and the TV is unplugged.',parent=self.root): return

        win=tk.Toplevel(self.root); self.pair_window=win

        win.title('Pair remote'); win.geometry('690x420')

        frame=ttk.Frame(win,padding=14); frame.pack(fill='both',expand=True)

        prompt=tk.StringVar(value='Preparing scan; old bond retained until you select Pair.')

        ttk.Label(frame,textvariable=prompt,wraplength=650).pack(anchor='w',pady=(0,10))

        tree=ttk.Treeview(frame,columns=('name','address','type','rssi'),show='headings',height=8)

        for column,width in (('name',170),('address',180),('type',45),('rssi',55)):

            tree.heading(column,text=column.title()); tree.column(column,width=width)

        tree.pack(fill='both',expand=True)

        def refresh():

            selected=tree.selection()

            with self.bridge.condition:

                items=[(key,dict(info)) for key,info in self.bridge.devices.items()]

            items=[item for item in items if time.monotonic()-item[1]['seen']<60]

            items.sort(key=lambda item:(item[1].get('manufacturer')!=0xC4,-item[1]['seen']))

            tree.delete(*tree.get_children())

            for (address,kind),info in items:

                tree.insert('', 'end',iid=f'{address} {kind}',values=(info.get('name','(unnamed)'),address,kind,info.get('rssi','')))

            for item in selected:

                if tree.exists(item): tree.selection_set(item)

        def start_pair():

            selection=tree.selection()

            if not selection or self.busy: return

            address,kind=selection[0].split()

            if not messagebox.askokcancel('Replace saved peer',f'Pair {address}, type {kind}?\nThis removes the Pico’s previous local bond. Names are hints, not model verification.',parent=win): return

            prompt.set('Preparing selected peer. Wait for the pairing-armed instruction.')

            def run():

                mark=self.bridge.send('forget'); self.bridge.wait('FORGOT local bond',mark)

                mark=self.bridge.send(f'forget {address} {kind}'); self.bridge.wait('FORGOT explicit local address',mark)

                self.bridge.scan_ready()

                mark=self.bridge.send(f'pair {address} {kind}')

                self.bridge.wait('PAIR armed',mark)

                self.events.put(('note','Pair armed: press only Wheel/OK now.'))

                self.events.put(('prompt',win,prompt,'Pair armed: press ONLY Wheel/OK once near the Pico. Wait for a real input report.'))

                line=pairing_result(self.bridge,mark)

                if not re.search(r'id=FD len=20\b',line):

                    raise RuntimeError('Paired, but report layout differs from the tested profile. Use CDC-only diagnostics before translating input.')

                return 'Paired: subscription and real input report received. Test buttons before assuming compatibility.'

            def complete(result):

                self.note(result)

                if win.winfo_exists(): prompt.set(result)

            self.work(run,complete)

        buttons=ttk.Frame(frame); buttons.pack(fill='x',pady=10)

        ttk.Button(buttons,text='Refresh devices',command=refresh).pack(side='left')

        ttk.Button(buttons,text='Pair selected',command=start_pair).pack(side='left',padx=8)

        ttk.Label(frame,text='Retry: press only Wheel/OK, refresh, select and pair again. Never repeat Back + Home for routine reconnect.',wraplength=650).pack(anchor='w')

        def ready(_):

            if win.winfo_exists(): prompt.set('Hold Back + Home five seconds ONCE, then Wheel/OK near the Pico. Refresh devices and select yours.')

        def scan():

            with self.bridge.condition: self.bridge.devices.clear()

            self.bridge.scan_ready()

        self.work(scan,ready)





    def poll_host_actions(self):

        # The USB owner handles one allowlisted request on its existing reader.

        if self.busy or not self.bridge or self.bridge.error: return

        directory=runtime_directory(ROOT)

        if not directory.exists(): return

        for request in sorted(directory.glob('*.request.json'))[:8]:

            if not REQUEST_NAME.fullmatch(request.name): continue

            reply=request.with_name(request.name.replace('.request.','.reply.'))

            data=None

            try:

                if request.stat().st_size>512: raise ValueError('Oversized host request')

                data=json.loads(request.read_text(encoding='utf-8'))

                validate_request(data,self.bridge.port.serial_number,time.time())

                claimed=request.with_name(request.name.replace('.request.','.processing.'))

                request.replace(claimed)

            except FileNotFoundError: continue

            except (ValueError,OSError) as error:

                # Do not consume a request directed at a different attached board.

                if isinstance(data,dict) and data.get('serial')!=self.bridge.port.serial_number: continue

                write_json(reply,{'ok':False,'message':str(error)}); request.unlink(missing_ok=True); continue

            def run():

                try: return {'ok':True,'message':perform_mouse_on(self.bridge)}

                except Exception as error: return {'ok':False,'message':str(error)}

            def done(result,reply=reply,claimed=claimed):

                write_json(reply,result); claimed.unlink(missing_ok=True)

                self.note('F22 pointer request: '+('ON verified' if result['ok'] else result['message']))

            self.work(run,done); break



    def tick(self):

        if self.closing: return

        while not self.events.empty():

            event=self.events.get()

            if event[0]=='done':

                self.busy=False

                if event[1]: event[1](event[2])

            elif event[0]=='error':

                self.busy=False; self.note('Error: '+event[1])

                messagebox.showerror('Operation failed',event[1]+'\nSee the local logs. No automatic retry was performed.',parent=self.root)

            elif event[0]=='prompt':

                if event[1].winfo_exists(): event[2].set(event[3])

            else: self.note(event[1])

        bridge=self.bridge

        if bridge:

            with bridge.condition: lines=[(seq,line) for seq,line in bridge.history if seq>self.mark]

            history_changed=False

            for sequence,line in lines:

                self.mark=sequence

                version=re.search(r'LG BRIDGE version=([\d.]+).*HID=(\d)',line)

                if version:

                    self.firmware.set(f'Firmware: {version[1]} · '+('tested profile: MR25GA' if version[2]=='1' else 'CDC-only diagnostic; no USB inputs'))

                    self.drag_supported=tuple(map(int,version[1].split('.')[:2]))>=(0,24) and version[2]=='1'
                    self.legacy_defaults=tuple(map(int,version[1].split('.')[:2]))<(0,12)

                    self.mapping_required=not self.legacy_defaults and version[2]=='1'

                    modern=tuple(map(int,version[1].split('.')[:2]))>=(0,21)

                    self.timeout_supported=modern and version[2]=='1';self.history_supported=modern

                    self.timeout_choice.configure(state='readonly' if self.timeout_supported else 'disabled',values=list(timeout_choices_for_version(version[1])))

                    for button in (self.timeout_read_button,self.timeout_save_button): button.configure(state='normal' if self.timeout_supported else 'disabled')

                    self.history_read_button.configure(state='normal' if modern else 'disabled')

                match=re.search(r'STATUS state=(\d+).*bonded=(\d+).*connect_enabled=(\d+)',line)

                if match:

                    states={'0':'starting','1':'scanning','2':'connecting','3':'encrypting','4':'querying HID','5':'ready'}

                    self.remote.set(f'Remote: {states.get(match[1],match[1])} · bonded={match[2]} · auto-connect={match[3]}')

                    if match[1] not in ('3','4','5'): self.active.set('Active peer: none')

                if 'PEER saved=' in line: self.peer.set('Saved peer: '+line.split('saved=',1)[1])

                if 'PEER active=' in line: self.active.set('Active peer: '+line.split('active=',1)[1])

                if match and match[2]=='0': self.peer.set('Saved peer: none')

                event=parse_event(line)

                if event: history_changed=self.accept_connection_event(event) or history_changed

                power=power_description(line)

                if power: self.power.set(power)

                gyro=re.search(r'GYRO mode=(\d+) gain=([\d.]+)',line)

                if gyro:

                    self.pointer_mode=gyro[1]=='1'

                    self.mouse.set('Pointer: '+('on' if gyro[1]=='1' else 'off')+' · saved gain '+gyro[2])

                    if self.load_gain:

                        self.gain.set(gyro[2]); self.load_gain=False

                    # Never overwrite a speed the user is editing.

                mode=re.search(r'MOUSE mode=(ON|OFF)',line)

                if mode: self.pointer_mode=mode[1]=='ON'

                report=input_report(line)

                if report:

                    code,wheel=report; self.last_report=time.monotonic()

                    if code!=self.code:

                        text=(f'{self.button_label(code)} → {self.effective_action(code,self.pointer_mode)} [0x{code:04X}]') if code else 'Released'

                        self.live.set('Remote button: '+(self.button_label(code) if code else 'none held'))

                        self.output.set('Windows action: '+(self.effective_action(code,self.pointer_mode) if code else 'released'))

                        self.raw_code.set(f'Remote code: 0x{code:04X}')

                        self.note(text); self.code=code

                        bridge.record('INPUT',text)

                    if wheel:

                        text=f'Wheel rotation → Mouse wheel {wheel:+d}'

                        self.output.set('Windows action: '+f'Mouse wheel {wheel:+d}')

                        self.note(text); bridge.record('INPUT',text)

                elif not re.search(r'\b(REPORT|ADV|AD|STATUS|POWER|POWER_EVENT|TIMEOUT|TIMEOUT_STORE|TIMEOUT_REJECT|HISTORY|HISTORY_BEGIN|HISTORY_END|LINK_EVENT|PEER|TRANSLATE|GYRO mode)\b|\bMAP(?:_| )|LG BRIDGE|HEARTBEAT|Scanning for|Scan timeout',line):

                    self.note(line)

            if history_changed: self.render_connection_history()

            if bridge.error:

                self.usb.set('USB disconnected · click Connect USB after reconnecting')

                self.power.set('Bluetooth power policy: USB connection unavailable')

                self.remote.set('Remote: connection unavailable'); self.live.set('Remote button: none held'); self.output.set('Windows action: USB disconnected'); self.code=0

            if self.last_report:

                age=time.monotonic()-self.last_report

                self.activity.set(f'Last remote report: {age:.1f}s ago')

                if age>0.7 and self.code:

                    self.code=0; self.live.set('Remote button: none held (report timeout)'); self.output.set('Windows action: released by report watchdog')

            if not self.busy and not bridge.error:

                now=time.monotonic()

                if now>=self.next_status_poll:

                    self.next_status_poll=now+2;self.command('status');self.command('mouse status')

                if self.timeout_supported and not self.timeout_loaded: self.load_timeout()

                elif self.history_supported and now>=self.next_history_poll: self.load_history()

        self.poll_host_actions()

        self.root.after(100,self.tick)



    def close(self):

        if self.busy:

            messagebox.showinfo('Operation in progress','Wait for the operation to finish before closing.',parent=self.root); return

        self.closing=True

        if self.bridge: self.bridge.close()

        self.root.destroy()





if __name__=='__main__':

    app=tk.Tk(); Companion(app); app.mainloop()

