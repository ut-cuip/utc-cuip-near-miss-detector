import json
import os
import time

import yaml
from confluent_kafka import Consumer, KafkaException

from frame_bufferer import FrameBufferer
from object import Object


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

    objects = []
    buffers = {
        config["cameras"][x]["camera_id"]: FrameBufferer(config["cameras"][x]["url"])
        for x in range(len(config["cameras"]))
    }
    
    for cam_id in buffers:
        buffers[cam_id].start()

    while True:
        try:
            consumer.poll(1)
            msg = consumer.consume()
            # Clean up old objects
            object_indices_to_del = []

            # Get data from Kafka
            if msg is not None:
                for m in msg:
                    if m.error():
                        continue
                    j = json.loads(m.value())
                    objects.append(Object(j["label"], j["camera_id"], j["locations"]))

            # Test results against each other:
            for object_a in objects:
                found = False
                for object_b in object:
                    if object_a == object_b:
                        continue
                    # Only check near-misses if at the same place
                    if object_a.cam_id == object_b.cam_id:
                        # Only print if there *is* a near-miss
                        if object_a.near_miss(object_b, threshold=20):
                            print(
                                "Near miss detected between {} and {} at {}".format(
                                    object_a.label, object_b.label, object_a.cam_id
                                )
                            )
                            # Break here because there's little chance it happens again with the same vehicle
                            found = True
                            break
                if found:
                    break

            # Cleanup old vars
            for i in range(len(objects)):
                # If it's older than 2 minutes
                if time.time() - objects[i].create_time >= 120:
                    object_indices_to_del.append(i)
            for i in reversed(object_indices_to_del):
                objects.pop(i)
            del msg, object_indices_to_del

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
