#!/usr/bin/env python3
"""One-command setup, build, and startup; Ctrl+C stops the entire app."""
import os
from pathlib import Path
import subprocess
import sys
import socket
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
python=ROOT/'.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
def run(args): subprocess.run([str(x) for x in args],check=True)
try:
    if not python.exists(): run([sys.executable,'-m','venv','.venv'])
    requirements=ROOT/'backend/requirements.txt'
    marker=ROOT/'.venv/.requirements'
    if not marker.exists() or marker.read_bytes()!=requirements.read_bytes():
        run([python,'-m','pip','install','-r',requirements]); marker.write_bytes(requirements.read_bytes())
    run(['npm','--prefix','frontend','install','--no-audit','--no-fund'])
    run(['npm','--prefix','frontend','run','build'])
    requested=os.getenv('PORT')
    port=None
    for candidate in ([int(requested)] if requested else range(8000,8021)):
        try:
            with socket.socket() as probe: probe.bind(('127.0.0.1',candidate))
            port=candidate; break
        except OSError: continue
    if port is None: raise SystemExit('No free local port. Set PORT to an available port.')
    print(f'\nBioForge Lab → http://localhost:{port}\nAPI docs → http://localhost:{port}/docs\nCtrl+C stops the app.\n',flush=True)
    run([python,'-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port',str(port)])
except KeyboardInterrupt:
    print('\nBioForge Lab stopped.')
except subprocess.CalledProcessError as exc:
    sys.exit(exc.returncode)
