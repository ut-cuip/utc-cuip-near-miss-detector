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

    def trim(self, time_threshold=120):
        """
        Trims old frames from the beginning of the dict
        Args:
            time_threshold (float, optional): the oldest (in seconds) a frame can be without being deleted
        """
        to_del = []

        # Lazy way to get first item in dict:
        for timestamp in self.frames:
            if time.time() - timestamp >= time_threshold:
                to_del.append(timestamp)
            # break  # Told you it was lazy
        
        to_del.reverse()
        
        for x in to_del:
            del self.frames[x]
        
        del to_del

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

                self.frames[time.time()] = frame

                self.trim()

                if (time.time() - loop_start_time) < (1 / 30):
                    time.sleep(((1 / 30) - (time.time() - loop_start_time)))
                else:
                    print(
                        "Loop took longer than 1/30th of a second. May experience continued delays."
                    )

                # Clean up in case GC doesn't
                del ret, frame, loop_start_time

            time.sleep(10)

