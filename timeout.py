import threading
import time


class Timeout(threading.Thread):
    def __init__(self, timeout, action):
        super().__init__()
        self.timeout = timeout
        self.action = action
        self._stop_event = threading.Event()

    def run(self):
        end_time = time.time() + self.timeout
        while time.time() < end_time:
            if self._stop_event.is_set():
                break
            time.sleep(1)

        if not self._stop_event.is_set():
            print("Timeout")
            self.action()

    def stop(self):
        self._stop_event.set()
