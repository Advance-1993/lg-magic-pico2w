"""BOOTSEL-only Pico 2 W installer. No remote commands, erase, OTP or force reset."""
from dataclasses import dataclass
from pathlib import Path
import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
from tools.verify_artifacts import inspect as inspect_uf2


@dataclass(frozen=True)
class Prepared:
    serial: str
    firmware: Path
    firmware_hash: str
    backup: Path
    backup_hash: str
    hid: bool


def board_identity(text):
    ids=re.findall(r'^\s*chipid:\s*0x([0-9a-fA-F]{1,16})\s*$',text,re.M)
    types=re.findall(r'^\s*type:\s*(RP\d+)\s*$',text,re.M)
    sizes=re.findall(r'^\s*flash size:\s*(\d+)K\s*$',text,re.M)
    if len(ids)!=1 or types!=['RP2350'] or sizes!=['4096']:
        raise RuntimeError('Expected exactly one RP2350 with 4096K flash in BOOTSEL. Unplug other Pico boards; check the printed Pico 2 W label.')
    secure=re.findall(r'^\s*secure boot:\s*(\d+)\s*$',text,re.M)
    if secure!=['0']:
        raise RuntimeError('Secure-boot state is unknown or enabled. This installer will not change it.')
    return ids[0].upper().zfill(16)


def sha256(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()


class Installer:
    def __init__(self,root,runner=None,backup_directory=None):
        self.root=Path(root).resolve()
        local=self.root/'tools/picotool/picotool.exe'
        self.tool=local if local.is_file() else Path(shutil.which('picotool') or '')
        if not self.tool.is_file():
            raise RuntimeError('picotool is missing. Install picotool and put it on PATH, or place it in tools/picotool/. See docs/SETUP.md.')
        self.runner=runner or subprocess.run
        self.backup_directory=Path(backup_directory) if backup_directory else self.root/'backups'
        self.session_log=None

    def run(self,*arguments,timeout=120):
        command=[str(self.tool),*map(str,arguments)]
        result=self.runner(command,capture_output=True,text=True,timeout=timeout,
                           creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        output=result.stdout+'\n'+result.stderr
        if self.session_log:
            with self.session_log.open('a',encoding='utf-8') as stream:
                stream.write('\nCOMMAND '+repr(command)+'\n'+output+'\n')
        if result.returncode:
            raise RuntimeError(f'picotool {arguments[0]} failed ({result.returncode}):\n{output[-2400:]}')
        return output

    def firmware(self,hid):
        version=(self.root/'VERSION').read_text().strip()
        if not re.fullmatch(r'\d+\.\d+(?:\.\d+)?',version): raise RuntimeError('Invalid VERSION')
        name=f'mr25ga-pico2w-airmouse-v{version}.uf2' if hid else f'lg-magic-pico2w-diagnostic-v{version}.uf2'
        path=self.root/'uf2'/name
        actual=inspect_uf2(path,hid)
        manifest=json.loads((self.root/'MANIFEST.json').read_text(encoding='utf-8'))
        expected=[a['sha256'] for a in manifest['artifacts'] if a['file']==name]
        if expected!=[actual['sha256']]:
            raise RuntimeError('Firmware checksum differs from the release manifest. Do not install this file; obtain the verified release package.')
        return path,actual['sha256']

    def prepare(self,hid):
        firmware,digest=self.firmware(hid)
        serial=board_identity(self.run('info','-a'))
        self.backup_directory.mkdir(parents=True,exist_ok=True)
        stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        backup=self.backup_directory/f'pico-{serial}-{stamp}-full-flash.bin'
        self.session_log=backup.with_suffix('.log')
        self.session_log.write_text(f'BOOTSEL install preparation for {serial}; physical wireless-board identity must be confirmed by the user.\n',encoding='utf-8')
        # Pin every device operation to this identity; never to an arbitrary first USB device.
        self.run('save','-a','-v',backup,'-t','bin','--ser',serial)
        if backup.stat().st_size!=4*1024*1024: raise RuntimeError('Full-flash backup has an unexpected length; installation stopped.')
        backup_hash=sha256(backup)
        if board_identity(self.run('info','-a','--ser',serial))!=serial:
            raise RuntimeError('Board identity changed; installation stopped.')
        record={'serial':serial,'bytes':backup.stat().st_size,'sha256':backup_hash,
                'firmware':firmware.name,'firmware_sha256':digest,
                'limits':'External flash only. RAM and OTP are not backed up or changed.',
                'restore':'Use this backup only on this same board. See BACKUP-RECOVERY.md.'}
        backup.with_suffix('.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
        return Prepared(serial,firmware,digest,backup,backup_hash,hid)

    def flash(self,prepared):
        if prepared.backup.stat().st_size!=4*1024*1024 or sha256(prepared.backup)!=prepared.backup_hash:
            raise RuntimeError('Backup is missing or changed; prepare a verified backup again.')
        firmware,digest=self.firmware(prepared.hid)
        if firmware!=prepared.firmware or digest!=prepared.firmware_hash:
            raise RuntimeError('Selected release changed after preparation; prepare again.')
        if board_identity(self.run('info','-a','--ser',prepared.serial))!=prepared.serial:
            raise RuntimeError('The prepared Pico is not connected. No firmware was written.')
        self.run('load','-v',firmware,'--ser',prepared.serial)
        try: self.run('reboot','--ser',prepared.serial)
        except Exception as error:
            raise RuntimeError('Firmware was written and verified, but reboot failed. Reconnect normally without BOOTSEL. '+str(error)) from error
        return f'Firmware written and verified on Pico {prepared.serial}. Reboot requested. Backup: {prepared.backup.name}'
