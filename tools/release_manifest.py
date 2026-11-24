"""Verify current images and write the minimal portable installer manifest."""
from pathlib import Path
import json
from verify_artifacts import inspect
root=Path(__file__).resolve().parents[1]
version=(root/'VERSION').read_text().strip()
artifacts=[inspect(root/'uf2'/f'mr25ga-pico2w-airmouse-v{version}.uf2',True),
           inspect(root/'uf2'/f'lg-magic-pico2w-diagnostic-v{version}.uf2',False)]
manifest={'version':version,'board':'pico2_w / RP2350','artifacts':artifacts,
 'scope':'Clean application builds, no provisioned flash or private configuration'}
(root/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
(root/'uf2/SHA256SUMS.txt').write_text(''.join(a['sha256']+'  '+a['file']+'\n' for a in artifacts),encoding='ascii')
print(json.dumps(manifest,indent=2))
