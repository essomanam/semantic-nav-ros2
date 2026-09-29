"""YOLO object detector: RGB image -> vision_msgs/Detection2DArray.

Subscribes : rgb_topic            (sensor_msgs/Image)
Publishes  : /semantic_nav/detections       (vision_msgs/Detection2DArray)
             /semantic_nav/detections_image (sensor_msgs/Image, annotated, optional)

The detection header is a copy of the image header: same stamp and frame,
which the localizer needs to synchronise with the depth image.
"""
import time

import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from vision_msgs.msg import Detection2D, Detection2DArray, ObjectHypothesisWithPose


class DetectorNode(Node):
    def __init__(self):
        super().__init__("detector")
        self.declare_parameter("rgb_topic", "/rgbd_camera/image")
        self.declare_parameter("model", "yolo11n.pt")
        self.declare_parameter("confidence", 0.4)
        self.declare_parameter("device", "cpu")          # "cuda:0" if a GPU is available
        self.declare_parameter("classes", [""])          # empty = all COCO classes
        self.declare_parameter("publish_annotated", True)

        from ultralytics import YOLO  # imported here: heavy import, clearer error
        self.model = YOLO(self.get_parameter("model").value)
        self.conf = self.get_parameter("confidence").value
        self.device = self.get_parameter("device").value
        wanted = [c for c in self.get_parameter("classes").value if c]
        self.class_filter = set(wanted) if wanted else None
        self.publish_annotated = self.get_parameter("publish_annotated").value

        self.bridge = CvBridge()
        self.pub = self.create_publisher(Detection2DArray, "/semantic_nav/detections", 10)
        self.pub_img = self.create_publisher(Image, "/semantic_nav/detections_image", 1)
        self.create_subscription(Image, self.get_parameter("rgb_topic").value,
                                 self.on_image, qos_profile_sensor_data)
        self.get_logger().info("detector ready")

    def on_image(self, msg: Image):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        t0 = time.perf_counter()
        result = self.model.predict(frame, conf=self.conf, device=self.device, verbose=False)[0]
        latency_ms = (time.perf_counter() - t0) * 1000.0

        out = Detection2DArray()
        out.header = msg.header
        for box in result.boxes:
            label = result.names[int(box.cls)]
            if self.class_filter and label not in self.class_filter:
                continue
            cx, cy, w, h = (float(v) for v in box.xywh[0])
            det = Detection2D()
            det.header = msg.header
            det.bbox.center.position.x = cx
            det.bbox.center.position.y = cy
            det.bbox.size_x = w
            det.bbox.size_y = h
            hyp = ObjectHypothesisWithPose()
            hyp.hypothesis.class_id = label
            hyp.hypothesis.score = float(box.conf)
            det.results.append(hyp)
            out.detections.append(det)
        self.pub.publish(out)
        self.get_logger().debug(f"{len(out.detections)} detections, {latency_ms:.1f} ms")

        if self.publish_annotated and self.pub_img.get_subscription_count() > 0:
            annotated = self.bridge.cv2_to_imgmsg(result.plot(), encoding="bgr8")
            annotated.header = msg.header
            self.pub_img.publish(annotated)


def main():
    rclpy.init()
    node = DetectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
