# Privacy

This publication contains source, synthetic test fixtures, rebuilt application
UF2s and documentation, not anyone's board flash or captured Bluetooth session.
No account, cloud connection, analytics or TV credentials are needed for normal use.

After local use, logs and backups can reveal Bluetooth addresses, board serials,
button activity, file paths and pairing keys. Git ignores `backups/`, `logs/`,
`_runtime/`, environments, local labels and builds. Ignoring is not encryption and
does not remove data already committed. Do not upload a used working directory
or full-flash readback. Use `python tools/check_public.py` before sharing a copy.

For issue reports include remote/board model, version, OS, reproduction steps and
only a short redacted diagnostic excerpt. Remove device addresses/serials, paths,
usernames, TV network details and all keys. No raw full-flash backup is needed.
Screenshots can also contain identifying information. Check them before uploading.

Third-party author names/copyright notices are retained for attribution, not
personal information about the operator of the original development system.
No Git history is included in this export. Choose a GitHub no-reply commit email
before making your own first commit if you want to keep your email private.
