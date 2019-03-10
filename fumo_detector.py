#!/usr/bin/python3.5
import numpy as np
import tensorflow as tf
from object_detection.utils import label_map_util
from object_detection.utils import visualization_utils as vis_util
from urllib.request import urlopen
import requests
from io import BytesIO
from numpy import array
# I had these in the vps for some reason, can't remember why. but gonna add them here
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

from PIL import Image

# silence warnings about compiler
import os
os.environ['TF_CPP_MIN_LOG_LEVEL']='2'

_PATH_TO_CKPT = os.path.join(os.path.dirname(__file__), "fumoModel/graph/frozen_inference_graph.pb")
_PATH_TO_LABELS = os.path.join(os.path.dirname(__file__), "fumoModel/object_detection.pbtxt")

NUM_CLASSES = 1

MAX_PIXELS = 12e6 # 12 megapixels?
# vps tends to freeze and crash when processing images over certain size

# do some initial loading
_detection_graph = tf.Graph()
with _detection_graph.as_default():
    od_graph_def = tf.GraphDef()
    with tf.gfile.GFile(_PATH_TO_CKPT, 'rb') as fid:
        serialized_graph = fid.read()
        od_graph_def.ParseFromString(serialized_graph)
        tf.import_graph_def(od_graph_def, name='')

# enter this so to remove the with and scope?
# not sure if right way to do it but this way it stays open and saves time
# when calling it over and over
_detection_graph.as_default().__enter__()
sess = tf.Session(graph=_detection_graph)
sess.__enter__()

image_tensor = _detection_graph.get_tensor_by_name('image_tensor:0')
# Each box represents a part of the image where a particular object was detected.
detection_boxes = _detection_graph.get_tensor_by_name('detection_boxes:0')
# Each score represent how level of confidence for each of the objects.
# Score is shown on the result image, together with the class label.
detection_scores = _detection_graph.get_tensor_by_name('detection_scores:0')
detection_classes = _detection_graph.get_tensor_by_name('detection_classes:0')
num_detections = _detection_graph.get_tensor_by_name('num_detections:0')

def resize_numpy_array_to_half(image):
    img = Image.fromarray(image)
    (im_width, im_height) = img.size
    max_size = (im_height/2, im_height/2)
    img.thumbnail(max_size)
    return np.array(img)
def _numpy_array_from_image(image):
    (im_width, im_height) = image.size
    return np.array(image.getdata()).reshape(
      (im_height, im_width, 3)).astype(np.uint8)


def _image_from_url(url):
    resp = requests.get(url)
    image = Image.open(BytesIO(resp.content))
    return image

# returns number of 'detected' fumos. doesn't really give numbers, but easier
# to assume it does and work that way. don't care how many, just if there are
def check(image_url):
    try:
        raw_image_data = _image_from_url(image_url)
        (im_width, im_height) = raw_image_data.size

        image_np = _numpy_array_from_image(raw_image_data)

        if im_width * im_height > MAX_PIXELS:
            image_np = resize_numpy_array_to_half(image_np)

        image_np_expanded = np.expand_dims(image_np, axis=0)
        # Actual detection.
        (boxes, scores, classes, num) = sess.run(
            [detection_boxes, detection_scores, detection_classes, num_detections],
            feed_dict={image_tensor: image_np_expanded})
        filtered_scores = [x for x in np.squeeze(scores) if x > 0.5]
        return len(filtered_scores)
    except ValueError as e:
        print(e)
        return 0
