"""Enforce the offline test boundary before importing any original harness."""
import os, sys

def offline_boundary(event,args):
    if event=='import' and args and (args[0]=='bpy' or args[0].startswith('bpy.')):
        raise ImportError('Offline QA: real bpy import prohibited')
    if event=='open' and args and isinstance(args[0],(str,bytes,os.PathLike)):
        path=os.fsdecode(args[0]).lower()
        if path.endswith('.blend') or '.blend' in path.rsplit('/',1)[-1]:
            raise RuntimeError('Offline QA: .blend file access prohibited')
    if event in ('socket.connect','socket.getaddrinfo'):
        raise RuntimeError('Offline QA: network prohibited')
    if event in ('subprocess.Popen','os.system'):
        raise RuntimeError('Offline QA: child process prohibited inside harness')
sys.addaudithook(offline_boundary)
