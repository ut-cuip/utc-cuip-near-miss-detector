import json
import math
import os
import time

import cv2
import numpy as np
import yaml
from confluent_kafka import Consumer, KafkaException
from datetime import datetime


class Joint:
    def __init__(self, location, timestamp):
        self.x_start = location[0]
        self.y_start = location[1]
        self.x_end = location[2]
        self.y_end = location[3]
        self.timestamp = timestamp

    def overlaps(self, other_joint):
        if self.x_start > other_joint.x_end or other_joint.x_start > self.x_end:
            return False

        if self.y_start < other_joint.y_end or other_joint.y_start < self.y_end:
            return False

        return True

    def distance(self, other_joint):
        center_a = [(self.x_start + self.x_end) / 2, self.y_end]
        center_b = [
            (other_joint.x_start + other_joint.x_end) / 2,
            other_joint.y_end,  # Pick *just* the bottom to get the bottom center
        ]

        return math.sqrt(
            ((center_b[0] - center_a[0]) ** 2) + ((center_b[1] - center_a[1]) ** 2)
        )


class Path:
    """A path object represents every location (and timestamp) of an object"""

    def __init__(self, label, cam_id, locations):
        self.label = label
        self.cam_id = cam_id
        self.locations = locations
        self.create_time = time.time()
        self.detect_time = locations[0]["timestamp"]
        self.joints = [Joint(x["coords"], x["timestamp"]) for x in locations]

    def near_miss(self, other_path, threshold=30):
        for joint_a in self.joints:
            for joint_b in other_path.joints:
                if joint_a.overlaps(joint_b):
                    self.draw(other_path)
                    return True
                elif joint_a.distance(joint_b) <= threshold:
                    self.draw(other_path)
                    return True
        return False

    def draw(self, other_path):
        """Draws the two paths together and saves to an image"""
        img = np.zeros((1080, 1920, 4), np.uint8)
        for joint in self.joints:
            cv2.rectangle(
                img,
                (joint.x_start, joint.y_start),
                (joint.x_end, joint.y_end),
                (255, 0, 0),
            )
        for joint in other_path.joints:
            cv2.rectangle(
                img,
                (joint.x_start, joint.y_start),
                (joint.x_end, joint.y_end),
                (0, 0, 255),
            )
        cv2.imwrite(
            "./images/{}_{}.png".format(
                self.cam_id, datetime.fromtimestamp(time.time())
            ),
            img,
        )


def main(config):
    """
    The main program loop which reads in Kafka items and processes them

    Args:
        config (pyyaml config): The main config file for this application
    """
    consumer = Consumer(
        {
            "bootstrap.servers": config["kafka"][0]["bootstrap-servers"],
            "group.id": "near-miss-detection",
        }
    )
    consumer.subscribe([config["kafka"][0]["topic"]])

    paths = []

    while True:
        try:
            consumer.poll(1)
            msg = consumer.consume()
            # Clean up old paths
            path_indices_to_del = []

            # Get data from Kafka
            if msg is not None:
                for m in msg:
                    if m.error():
                        continue
                    j = json.loads(m.value())
                    paths.append(Path(j["label"], j["camera_id"], j["locations"]))

            # Test results against each other:
            for path_a in paths:
                found = False
                for path_b in paths:
                    if path_a == path_b:
                        continue
                    # Only check near-misses if at the same place
                    if path_a.cam_id == path_b.cam_id:
                        # Only check near-misses if they're within the same time period
                        if abs(path_a.detect_time - path_b.detect_time) <= 5:
                            # Only print if there *is* a near-miss
                            if path_a.near_miss(path_b, threshold=20):
                                print(
                                    "Near miss detected between {} and {} at {}".format(
                                        path_a.label, path_b.label, path_a.cam_id
                                    )
                                )
                                # Break here because there's little chance it happens again with the same vehicle
                                found = True
                                break
                if found:
                    break

            # Cleanup old vars
            for i in range(len(paths)):
                # If it's older than 2 minutes
                if time.time() - paths[i].create_time >= 120:
                    path_indices_to_del.append(i)
            for i in reversed(path_indices_to_del):
                paths.pop(i)
            del msg, path_indices_to_del

            # Sleep so we don't thrash Kafka
            time.sleep(1)
        except KeyboardInterrupt:
            break
    consumer.close()


if __name__ == "__main__":
    if os.path.exists("config.yaml"):
        with open("config.yaml") as file:
            config = yaml.load(file.read(), Loader=yaml.Loader)
        main(config)
    else:
        print("No config file found")
        exit()
