"""Portable pipe-protocol tests. No Xvfb, graphics/native child or real server is started."""
from collections import deque
import unittest
from display_ready import DisplayReadyError,read_display_number,require_display_alive


class Child:
    def __init__(self,exit_codes=(None,)):
        self.codes=deque(exit_codes);self.last=None
    def poll(self):
        if self.codes:self.last=self.codes.popleft()
        return self.last


class ScriptedPipe:
    def __init__(self,chunks):
        self.chunks=deque(chunks);self.now=0;self.reads=0;self.delimiter_seen=False
        self.closed=False;self.closed_before_delimiter=False
    def clock(self):return self.now
    def wait(self,readers,writers,errors,timeout):
        self.now+=timeout
        return (readers if self.chunks else [],[],[])
    def read(self,fd,size):
        self.reads+=1;block=self.chunks.popleft()
        if len(block)>size:
            self.chunks.appendleft(block[size:]);block=block[:size]
        if b'\n'in block:self.delimiter_seen=True
        return block
    def close(self):
        self.closed=True;self.closed_before_delimiter=not self.delimiter_seen
    def receive(self,child=None,timeout=1):
        return read_display_number(7,child or Child(),timeout,wait=self.wait,read=self.read,clock=self.clock)


class DisplayProtocol(unittest.TestCase):
    def test_fragmented_digits_then_newline_keeps_reader_until_writer_finishes(self):
        pipe=ScriptedPipe([b'4',b'2',b'\n'])
        try:result=pipe.receive()
        finally:pipe.close()
        self.assertEqual(result,':42')
        self.assertEqual(pipe.reads,3)
        self.assertFalse(pipe.closed_before_delimiter)
        self.assertFalse(pipe.chunks)
    def test_complete_single_notification_and_three_digit_display(self):
        for packet in (b'0\n',b'999\n'):
            with self.subTest(packet=packet):
                self.assertEqual(ScriptedPipe([packet]).receive(),':'+packet[:-1].decode('ascii'))
    def test_eof_after_digits_and_empty_eof_are_not_ready(self):
        for chunks in ([b'8',b''],[b'']):
            with self.subTest(chunks=chunks):
                with self.assertRaisesRegex(DisplayReadyError,'EOF before newline'):
                    ScriptedPipe(chunks).receive()
    def test_timeout_and_oversized_or_malformed_notification_rejected(self):
        with self.assertRaisesRegex(DisplayReadyError,'timeout'):
            ScriptedPipe([]).receive(timeout=.3)
        for packet in (b'1000\n',b'x\n',b'\n',b'12\n3'):
            with self.subTest(packet=packet):
                with self.assertRaises(DisplayReadyError):ScriptedPipe([packet]).receive()
    def test_exited_before_notification_and_exit_after_last_byte_rejected(self):
        with self.assertRaisesRegex(DisplayReadyError,'exited: 1'):
            ScriptedPipe([b'4\n']).receive(Child([1]))
        with self.assertRaisesRegex(DisplayReadyError,'exited: 1'):
            ScriptedPipe([b'4\n']).receive(Child([None,1]))
        with self.assertRaisesRegex(DisplayReadyError,'exited: -15'):
            require_display_alive(Child([-15]))


if __name__=='__main__':unittest.main()
