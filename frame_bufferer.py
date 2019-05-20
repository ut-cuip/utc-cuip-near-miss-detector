import time
from threading import Thread

import cv2


class FrameBufferer:
    def __init__(self, camera_endpoint):
        """Creates a bufferer process for getting video feeds"""
        self.url = camera_endpoint
        self.frames = {}
        self.should_run = False
        self.should_stop = False

    def start(self):
        self.should_run = True
        self.worker = Thread(target=loop, daemon=True)
        self.worker.start()

    def pause(self):
        self.should_run = False

    def stop(self):
        self.should_run = False
        self.should_stop = True

    def loop(self):
        """Starts the loop for grabbing and updating video feeds"""
        cap = cv2.VideoCapture()
        cap.open(self.url)
        while not self.should_stop:
            while self.should_run:
                loop_start_time = time.time()
                ret, frame = cap.read()
                if not ret:
                    break
                self.frames[str(time.time())] = frame

                # Check if the frames are too old
                while time.time() - self.frames.items()[0][0] >= 120:
                    del self.frames[self.frames.items()[0][0]]

                if (time.time() - loop_start_time) < (1 / 30):
                    time.sleep(((1 / 30) - (time.time() - loop_start_time)))
                else:
                    print(
                        "Loop took longer than 1/30th of a second. May experience continued delays."
                    )

            time.sleep(10)

