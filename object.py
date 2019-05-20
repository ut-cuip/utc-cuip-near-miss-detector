import math
import time
from datetime import datetime

import cv2
import numpy as np


class Object:
    def __init__(self, label, cam_id, locations):
        """
        A geometric representation of an object
        Args:
            label (str): the label of the object
            cam_id (str): the camera id that the object was detected at
            locations (dict): a dict of timestamp (float) -> locations (tuple of form x1, y1, x2, y2)
        """
        self.label = label
        self.cam_id = cam_id
        self.locations = locations
        self.create_time = time.time()
        self.detect_time = locations[0]["timestamp"]
        self.joints = [Joint(x["coords"], x["timestamp"]) for x in locations]

    def near_miss(self, other_object, min_threshold=15, max_threshold=50):
        """
        Detects if there is a near-miss event with another object
        Args:
            other_object (Object): the other object being checked for near-miss with
            min_threshold (int, optional): minimum distance a hitbox must be to be considered near-miss. Default: 15
            max_threshold (int, optional): maximum distance a hitbox must be to be considered near-miss. Default: 50
        """
        for joint_a in self.joints:
            for joint_b in other_object.joints:
                # Only check this joint if they occurred within 3 seconds of each other
                if abs(joint_a.timestamp - joint_b.timestamp) <= 3:
                    if joint_a.overlaps(joint_b):
                        self.draw(other_object)
                        return True
                    elif (
                        joint_a.distance(joint_b) >= min_threshold
                        and joint_a.distance(joint_b) <= max_threshold
                    ):
                        self.draw(other_object)
                        return True
        return False

    def draw(self, img, other_object):
        """
        Draws the two objects together and saves to an image
        Args:
            img (numpy.ndarray): The frame to draw onto
            other_object (Object): The other object whose hitboxes to also draw
        """
        for joint in self.joints:
            cv2.rectangle(
                img,
                (int(joint.x_start), int(joint.y_start)),
                (int(joint.x_end), int(joint.y_end)),
                (255, 0, 0),
                2,
            )
        for joint in other_object.joints:
            cv2.rectangle(
                img,
                (int(joint.x_start), int(joint.y_start)),
                (int(joint.x_end), int(joint.y_end)),
                (0, 0, 255),
                2,
            )
        cv2.imwrite(
            "./images/{}_{}.png".format(
                self.cam_id, datetime.fromtimestamp(time.time())
            ),
            img,
        )

    class Joint:
        def __init__(self, location, timestamp):
            """
            A nested joint class, which represents a part of an object's object
            Args:
                location (tuple): the location to of this joint, of format (x1, y1, x2, y2)
                timestamp (float): the timestamp associated with this location
            """
            self.x_start = location[0]
            self.y_start = location[1]
            self.x_end = location[2]
            self.y_end = location[3]
            self.timestamp = timestamp

        def overlaps(self, other_joint):
            """
            Checks if the this bounding box intersects with another
            Args:
                other_joint (Joint): The other joint to check intersection with
            """
            if self.x_start > other_joint.x_end or other_joint.x_start > self.x_end:
                return False

            if self.y_start < other_joint.y_end or other_joint.y_start < self.y_end:
                return False

            return True

        def distance(self, other_joint):
            """
            Finds the distance between the bottom center locations of two hitboxes
            Args:
               other_joint (Joint): The other joint to find the distance between
            """
            center_a = [(self.x_start + self.x_end) / 2, self.y_end]
            center_b = [
                (other_joint.x_start + other_joint.x_end) / 2,
                other_joint.y_end,  # Pick *just* the bottom to get the bottom center
            ]

            return math.sqrt(
                ((center_b[0] - center_a[0]) ** 2) + ((center_b[1] - center_a[1]) ** 2)
            )
