"""Read the owned Xvfb -displayfd notification completely before caller closes its pipe.
Pure imports; no process spawning, graphics loads, world access or acceptance shortcuts.
"""
import os
import re
import select
import time


class DisplayReadyError(RuntimeError):
    pass


def require_display_alive(process):
    code=process.poll()
    if code is not None:
        raise DisplayReadyError('Owned Xvfb exited: '+str(code))


def read_display_number(read_fd, process, timeout=10, *, wait=None, read=None, clock=None):
    """A short pipe read is not a complete line. Caller retains/owns fd closure.
    Read at most four protocol bytes (three digits plus newline), within one deadline,
    and reject EOF, malformed/oversized input or a child already observed exited.
    The injected I/O functions let source tests exercise real protocol fragmentation.
    """
    if timeout<=0 or timeout>30:
        raise ValueError('Display timeout must be in (0,30]')
    wait=select.select if wait is None else wait
    read=os.read if read is None else read
    clock=time.monotonic if clock is None else clock
    deadline=clock()+timeout
    raw=b''
    while b'\n' not in raw:
        require_display_alive(process)
        remaining=deadline-clock()
        if remaining<=0:
            raise DisplayReadyError('Owned Xvfb display notification timeout')
        ready=wait([read_fd],[],[],min(remaining,.1))[0]
        if not ready:
            continue
        block=read(read_fd,5-len(raw))
        if not block:
            raise DisplayReadyError('Owned Xvfb display notification EOF before newline')
        raw+=block
        if len(raw)>4:
            raise DisplayReadyError('Owned Xvfb display notification exceeds four bytes')
    if re.fullmatch(rb'[0-9]{1,3}\n',raw) is None:
        raise DisplayReadyError('Owned Xvfb display notification malformed')
    require_display_alive(process)
    return ':'+raw[:-1].decode('ascii')
