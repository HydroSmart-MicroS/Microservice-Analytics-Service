import logging
import threading


class DevicePresenceWorker:
    def __init__(self,service,check):
        self.service,self.check=service,check
        self.stop_event=threading.Event()
        self.thread=None

    def start(self):
        def run():
            while not self.stop_event.is_set():
                try:
                    for row in self.service.pending():
                        if self.stop_event.is_set():break
                        self.check(row)
                except Exception:
                    logging.getLogger(__name__).warning('Device presence check delayed; dependencies unavailable')
                self.stop_event.wait(30)
        self.thread=threading.Thread(target=run,name='device-presence',daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:self.thread.join(timeout=5)
