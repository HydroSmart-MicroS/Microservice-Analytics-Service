import threading
from contextlib import contextmanager

class LifecycleGate:
    # shortcut: one local analytics instance; a shared gate is required before horizontal scaling.
    def __init__(self):self.condition=threading.Condition();self.readers=0;self.writer=False;self.waiting=0
    def acquire(self):
        with self.condition:
            self.condition.wait_for(lambda:not self.writer and not self.waiting)
            self.readers+=1
    def release(self):
        with self.condition:self.readers-=1;self.condition.notify_all()
    @contextmanager
    def read(self):
        self.acquire()
        try:yield
        finally:self.release()
    @contextmanager
    def write(self):
        with self.condition:
            self.waiting+=1
            self.condition.wait_for(lambda:not self.writer and not self.readers)
            self.waiting-=1;self.writer=True
        try:yield
        finally:
            with self.condition:self.writer=False;self.condition.notify_all()

gate=LifecycleGate()
