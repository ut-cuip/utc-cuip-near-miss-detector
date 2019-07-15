import datetime
import multiprocessing
import time

import cv2
import numpy as np

from pytorch_yolo.yolo import YOLO
from utils.sort import Sort
from trajectory import predict_location, time_til_collision
from utils.utils import distance_from_xy


def cap_worker(cap_queue):
    while True:
        cap = cv2.VideoCapture()
        cap.open(
            "rtsp://consumer:IyKv4uY7%g^8@10.199.51.162/axis-media/media.amp?streamprofile=H264-OpenCV-Optimized"
        )
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        while True:
            ret, frame = cap.read()
            if not ret:
                cap.release()
                del cap
                time.sleep(10)
                break
            else:
                frame = frame[128 : frame.shape[0], 0 : frame.shape[1]]
                original_dim = frame.shape
                dimension = (
                    frame.shape[0]
                    if (frame.shape[0] > frame.shape[1])
                    else frame.shape[1]
                )
                tmp = np.zeros((dimension, dimension, 3), np.uint8)
                tmp[0 : original_dim[0]] = frame
                del frame
                cap_queue.put((tmp, original_dim), block=True)


def main(cap_queue):
    
    yolo = YOLO(res="1024")
    sort = Sort(iou_threshold=0.05)
    whitelist = [
        "person",
        "bicycle",
        "car",
        "motorbike",
        "aeroplane",
        "bus",
        "truck",
        "boat",
        "fire hydrant",
        "stop sign",
        "parking meter",
        "bird",
        "cat",
        "dog",
        "backpack",
        "umbrella",
        "handbag",
        "suitcase",
    ]
    frames = 0
    while True:
        frame, original_dim = cap_queue.get(block=True)
        frames += 1
        outputs = yolo.get_results(frame)
        detections = []
        labels = []

        for output in outputs:
            label = yolo.classes[int(output[-1])]
            if not label in whitelist:
                del label
                continue

            tl = tuple(output[1:3].int())
            br = tuple(output[3:5].int())

            detections.append(
                np.array([tl[0].item(), tl[1].item(), br[0].item(), br[1].item()])
            )
            labels.append(label)

            del tl, br, label
        del outputs

        detections = np.array(detections)
        should_write = False

        if detections.shape[0] > 0:
            try:
                alive, _ = sort.update(detections, labels)
            except IndexError:
                del frame, detections, labels
                continue

            should_write = False
            for trk in alive:
                t = trk.get_state()[0]
                try:
                    bbox = [int(t[0]), int(t[1]), int(t[2]), int(t[3])]
                except ValueError:
                    continue
                cv2.rectangle(
                    frame,
                    (int(bbox[0]), int(bbox[1])),
                    (int(bbox[2]), int(bbox[3])),
                    trk.color,
                    2,
                )
                cv2.putText(
                    frame,
                    "{}:id {}".format(trk.get_label(), str(trk.id)),
                    (int(bbox[0]), int(bbox[1]) - 12),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.0005 * frame.shape[0],
                    trk.color,
                    2,
                )
                for location in trk.locations:
                    x1, y1, x2, y2 = location[1]
                    cv2.circle(
                        frame, (((int(x1) + int(x2)) // 2), int(y2)), 3, trk.color, -1
                    )
                    del x1, y1, x2, y2

                pred_x, pred_y = predict_location(trk, amount_to_predict=10)
                center_x = (int(bbox[0]) + int(bbox[2])) // 2
                center_y = (int(bbox[1]) + int(bbox[3])) // 2
                cv2.line(
                    frame,
                    (int(pred_x), int(pred_y)),
                    (center_x, center_y),
                    trk.color,
                    8,
                )
                # text = "{}".format(
                #     distance_from_xy((center_x, center_y), (int(pred_x), int(pred_y)))
                # )
                # midpoint = ((center_x + pred_x) // 2, (center_y + pred_y) // 2)
                # cv2.putText(frame, text, (int(midpoint[0]), int(midpoint[1])), cv2.FONT_HERSHEY_SIMPLEX, 1, trk.color)
                if len(alive) > 1:
                    for trk2 in alive:
                        if trk.id == trk2.id:
                            continue
                    ttc = time_til_collision(trk, trk2)
                    ttc_thresh = 5
                    if ttc > 0 and ttc < ttc_thresh:

                        print(
                            "Potential accident between ID {} and {}.\nTTC:{}s".format(
                                trk.id, trk2.id, ttc
                            )
                        )
                        cv2.putText(
                            frame,
                            "ID {} and {} have TTC {}".format(trk.id, trk2.id, ttc),
                            (0, 20),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            1,
                            (0, 0, 255),
                        )
                        should_write = True
                    del ttc_thresh, ttc

                del t, bbox, pred_x, pred_y, center_x, center_y
        # write_queue.put(frame[0 : original_dim[0], 0 : original_dim[1]])
        cv2.imshow("Object Tracking", frame[0 : original_dim[0], 0 : original_dim[1]])

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            raise KeyboardInterrupt
        del should_write


if __name__ == "__main__":
    multiprocessing.set_start_method("spawn", force=True)
    cap_queue = multiprocessing.Queue(1)
    processes = []
    processes.append(
        multiprocessing.Process(target=main, args=(cap_queue,))
    )
    processes.append(multiprocessing.Process(target=cap_worker, args=(cap_queue,)))

    try:
        for process in processes:
            process.start()
        for process in processes:
            process.join()
    except KeyboardInterrupt:
        for process in processes:
            process.terminate()
