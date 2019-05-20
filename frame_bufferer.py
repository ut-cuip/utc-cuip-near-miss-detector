import time
from threading import Thread

import cv2


class FrameBufferer:
    def __init__(self, camera_endpoint):
        """
        Creates a bufferer process for getting video feeds
        Args:
            camera_endpoint (str)/(int): The URL or int for the camera to buffer
        """
        self.url = camera_endpoint
        self.frames = {}
        self.should_run = False
        self.should_stop = False

    def start(self):
        """Starts the thread fetching the frames"""
        self.should_run = True
        self.worker = Thread(target=self.loop, daemon=True)
        self.worker.start()

    def pause(self):
        """Pauses the thread fetching the frames"""
        self.should_run = False

    def stop(self):
        """Stops the thread fetching the frames"""
        self.should_run = False
        self.should_stop = True

    def find_frame(self, timestamp):
        """
        Finds the frame closest to the timestamp given
        Args:
            timestamp (float): The timestamp to search for
        """
        if list(self.frames.items()):
            best_ts = list(self.frames.items())[0][0]
            best_diff = abs(timestamp - best_ts)

            for ts in self.frames:
                if abs(ts - timestamp) < best_diff:
                    best_ts = ts
                    best_diff = abs(ts - timestamp)

            return self.frames[best_ts]
        else:
            print("Waiting for frames")
            time.sleep(0.01)
            return self.find_frame(timestamp)

    def trim(self, time_threshold=120):
        """
        Trims old frames from the beginning of the dict
        Args:
            time_threshold (float, optional): the oldest (in seconds) a frame can be without being deleted
        """
        to_del = []

        for timestamp in self.frames:
            if time.time() - timestamp >= time_threshold:
                to_del.append(timestamp)

        for x in reversed(to_del):
            del self.frames[x]

        del to_del

    def loop(self):
        """Starts the loop for grabbing and updating video feeds"""
        while not self.should_stop:
            last_trim = time.time()
            cap = cv2.VideoCapture()
            cap.open(self.url)
            while self.should_run:
                start = time.time()
                ret, frame = cap.read()
                if not ret:
                    cap.release()
                    del cap
                    break

                self.frames[time.time()] = frame

                if time.time() - last_trim >= 10:  # only trim every 10s:
                    self.trim()
                    last_trim = time.time()

                time.sleep(max((1 / 30) - (time.time() - start), 0))

                # Clean up in case GC doesn't
                del ret, frame, start

            time.sleep(10)

