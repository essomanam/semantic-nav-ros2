"""2D detections + depth -> 3D object observations in the map frame.

Subscribes : /semantic_nav/detections (vision_msgs/Detection2DArray)
             depth_topic              (sensor_msgs/Image, aligned with the RGB image)
             camera_info_topic        (sensor_msgs/CameraInfo)
Publishes  : /semantic_nav/observations (semantic_nav_interfaces/SemanticObjectArray)

Pipeline for each detection:
  bbox centre (u, v) --robust depth--> Z --pinhole--> P_cam (optical frame)
  --TF at image stamp--> P_map

Assumption to check in week 3: the depth image is registered to the RGB
image (same resolution, same intrinsics). True for a Gazebo rgbd_camera sensor.
"""
import message_filters
import rclpy
import tf2_geometry_msgs  # noqa: F401  (registers PointStamped transforms)
from cv_bridge import CvBridge
from geometry_msgs.msg import PointStamped
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image
from tf2_ros import Buffer, TransformException, TransformListener
from vision_msgs.msg import Detection2DArray

from semantic_nav.geometry import depth_to_meters, pixel_to_camera_point, robust_bbox_depth
from semantic_nav_interfaces.msg import SemanticObject, SemanticObjectArray


class LocalizerNode(Node):
    def __init__(self):
        super().__init__("localizer")
        self.declare_parameter("depth_topic", "/rgbd_camera/depth_image")
        self.declare_parameter("camera_info_topic", "/rgbd_camera/camera_info")
        self.declare_parameter("map_frame", "map")
        self.declare_parameter("max_range", 6.0)
        self.declare_parameter("sync_slop", 0.1)

        self.map_frame = self.get_parameter("map_frame").value
        self.max_range = self.get_parameter("max_range").value
        self.K = None
        self.bridge = CvBridge()
        self.tf_buffer = Buffer()
        # spin_thread=True: TF keeps being received while we wait inside a callback
        self.tf_listener = TransformListener(self.tf_buffer, self, spin_thread=True)

        self.create_subscription(CameraInfo, self.get_parameter("camera_info_topic").value,
                                 self.on_info, qos_profile_sensor_data)
        det_sub = message_filters.Subscriber(self, Detection2DArray, "/semantic_nav/detections")
        depth_sub = message_filters.Subscriber(self, Image, self.get_parameter("depth_topic").value,
                                               qos_profile=qos_profile_sensor_data)
        self.sync = message_filters.ApproximateTimeSynchronizer(
            [det_sub, depth_sub], queue_size=10, slop=self.get_parameter("sync_slop").value)
        self.sync.registerCallback(self.on_synced)
        self.pub = self.create_publisher(SemanticObjectArray, "/semantic_nav/observations", 10)
        self.get_logger().info("localizer ready")

    def on_info(self, msg: CameraInfo):
        k = msg.k  # row-major 3x3
        self.K = (k[0], k[4], k[2], k[5])  # fx, fy, cx, cy

    def on_synced(self, dets: Detection2DArray, depth_msg: Image):
        if self.K is None or not dets.detections:
            return
        fx, fy, cx0, cy0 = self.K
        depth_m = depth_to_meters(self.bridge.imgmsg_to_cv2(depth_msg, "passthrough"))
        camera_frame = depth_msg.header.frame_id

        out = SemanticObjectArray()
        out.header.stamp = dets.header.stamp
        out.header.frame_id = self.map_frame
        for det in dets.detections:
            if not det.results:
                continue
            u, v = det.bbox.center.position.x, det.bbox.center.position.y
            z = robust_bbox_depth(depth_m, u, v, det.bbox.size_x, det.bbox.size_y,
                                  max_range=self.max_range)
            if z is None:
                continue
            x, y, z = pixel_to_camera_point(u, v, z, fx, fy, cx0, cy0)

            p = PointStamped()
            p.header.stamp = depth_msg.header.stamp
            p.header.frame_id = camera_frame
            p.point.x, p.point.y, p.point.z = x, y, z
            try:
                p_map = self.tf_buffer.transform(p, self.map_frame, timeout=Duration(seconds=0.1))
            except TransformException as exc:
                self.get_logger().warn(f"TF {camera_frame}->{self.map_frame}: {exc}",
                                       throttle_duration_sec=5.0)
                return

            obs = SemanticObject()
            obs.label = det.results[0].hypothesis.class_id
            obs.confidence = float(det.results[0].hypothesis.score)
            obs.position = p_map.point
            obs.n_observations = 1
            out.objects.append(obs)
        if out.objects:
            self.pub.publish(out)


def main():
    rclpy.init()
    node = LocalizerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
