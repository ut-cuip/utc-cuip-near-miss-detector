"""A wrapper class for a YOLO model"""
from torch.autograd import Variable

from pytorch_yolo.darknet import Darknet
from pytorch_yolo.preprocess import letterbox_image, prep_image
from pytorch_yolo.util import *


class YOLO:
    def __init__(self, conf=0.75, res="448", nms=0.4):
        self.confidence = conf
        self.res = res
        self.nms_thresh = nms
        self.CUDA = torch.cuda.is_available()
        self.model = Darknet("./pytorch_yolo/yolov3.cfg")
        self.model.load_weights("./pytorch_yolo/yolov3.weights")
        self.input_dim = int(self.model.net_info["height"])
        assert self.input_dim % 32 == 0
        assert self.input_dim > 32
        if self.CUDA:
            self.model.cuda()
        self.model(self.get_test_input(), self.CUDA)
        self.model.eval()
        self.classes = load_classes("./pytorch_yolo/coco.names")

    def get_test_input(self):
        """For model eval"""
        img = cv2.imread("./pytorch_yolo/dog-cycle-car.png")
        img = cv2.resize(img, (self.input_dim, self.input_dim))
        img_ = img[:, :, ::-1].transpose((2, 0, 1))
        img_ = img_[np.newaxis, :, :, :] / 255.0
        img_ = torch.from_numpy(img_).float()
        img_ = Variable(img_)

        if self.CUDA:
            img_ = img_.cuda()

        return img_

    def prep_image(self, img, inp_dim):
        """Preprocessing on the image to make it the correct shape"""
        orig_im = img
        dim = orig_im.shape[1], orig_im.shape[0]
        img = letterbox_image(orig_im, (inp_dim, inp_dim))
        img_ = img[:, :, ::-1].transpose((2, 0, 1)).copy()
        img_ = torch.from_numpy(img_).float().div(255.0).unsqueeze(0)
        return img_, orig_im, dim

    def get_results(self, frame):
        """Gets the resulting labels and bb using YOLO"""
        img, orig_img, dim = self.prep_image(frame, self.input_dim)
        img_dim = torch.FloatTensor(dim).repeat(1, 2)

        if self.CUDA:
            img_dim = img_dim.cuda()
            img = img.cuda()
        with torch.no_grad():
            output = self.model(Variable(img), self.CUDA)
        output = write_results(
            output, self.confidence, 80, nms=True, nms_conf=self.nms_thresh
        )
        img_dim = img_dim.repeat(output.size(0), 1)
        scaling_factor = torch.min(self.input_dim / img_dim, 1)[0].view(-1, 1)
        output[:, [1, 3]] -= (
            self.input_dim - scaling_factor * img_dim[:, 0].view(-1, 1)
        ) / 2
        output[:, [2, 4]] -= (
            self.input_dim - scaling_factor * img_dim[:, 1].view(-1, 1)
        ) / 2
        output[:, 1:5] /= scaling_factor

        for i in range(output.shape[0]):
            output[i, [1, 3]] = torch.clamp(output[i, [1, 3]], 0.0, img_dim[i, 0])
            output[i, [2, 4]] = torch.clamp(output[i, [2, 4]], 0.0, img_dim[i, 1])

        del img, orig_img

        return output
