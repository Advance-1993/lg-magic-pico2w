"""Check publication boundaries, generic private data, hashes and doc links.

Run on a clean publication copy, not a used install. No personal denylist is
embedded. This is a conservative local check, not a guarantee against every
possible secret. It does not contact a device or external service.
"""
from pathlib import Path
import hashlib,json,re
root=Path(__file__).resolve().parents[1]
errors=[];count=0
for p in root.rglob('*'):
 rel=p.relative_to(root)
 if '.git' in rel.parts or '.venv' in rel.parts or '__pycache__' in rel.parts:continue
 if not p.is_file():continue
 if any(part in {'backups','logs','_runtime','build','work','host-integration'} for part in rel.parts):
  errors.append(str(rel)+': private/generated directory');continue
 if rel.parts[:2] in [('tools','pico-sdk'),('tools','picotool')]:continue
 if p.suffix in {'.elf','.bin','.zip','.pyc','.pem','.key'}:
  errors.append(str(rel)+': unapproved artifact');continue
 data=p.read_bytes();count+=1
 # UF2 payloads can split strings; also scan the reconstructed flash below.
 blobs=[data]
 if p.suffix=='.uf2':
  import struct
  flash=bytearray(b'\xff')*(4*1024*1024)
  for offset in range(0,len(data),512):
   address,size=struct.unpack_from('<II',data,offset+12)
   if 0x10000000<=address and address+size<=0x10400000:
    flash[address-0x10000000:address-0x10000000+size]=data[offset+32:offset+32+size]
  blobs.append(bytes(flash))
 for blob in blobs:
  if re.search(rb'(?i)(?:[A-Z]:[/\\]Users[/\\]|/home/[a-z0-9_.-]+/|/Users/[a-z0-9_.-]+/)',blob):
   errors.append(str(rel)+': local user path')
  if re.search(rb'(?:ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)',blob):
   errors.append(str(rel)+': possible credential')
  for mac in re.findall(rb'(?<![A-Fa-f0-9])(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}(?![A-Fa-f0-9])',blob):
   allowed={b'AA:BB:CC:DD:EE:FF',b'02:00:00:00:00:01'}
   # Unprovisioned CYW43 SDK NVRAM templates and BTstack's null-address string.
   # These shared upstream constants are not an operator's device identities.
   if p.suffix=='.uf2' or rel.as_posix()=='tools/check_public.py':
    allowed|={b'00:00:00:00:00:00',b'00:A0:50:B5:59:5E',b'00:90:4C:C5:12:38'}
   if mac.upper() not in allowed:
    errors.append(str(rel)+': non-example Bluetooth address')
 if p.suffix=='.md':
  for link in re.findall(r'\]\(([^)]+)\)',data.decode('utf-8')):
   target=link.strip('<>').split('#',1)[0]
   if target and '://' not in target and not target.startswith('mailto:') and not (p.parent/target).exists():
    errors.append(str(rel)+': broken local link '+target)
manifest=json.loads((root/'MANIFEST.json').read_text(encoding='utf-8'))
for a in manifest['artifacts']:
 p=root/'uf2'/a['file']
 if hashlib.sha256(p.read_bytes()).hexdigest()!=a['sha256']:errors.append('Firmware checksum mismatch')
if errors:raise SystemExit('\n'.join(sorted(set(errors))))
print(f'PASS: {count} publication files; boundaries, local links, firmware hashes and generic privacy patterns')
