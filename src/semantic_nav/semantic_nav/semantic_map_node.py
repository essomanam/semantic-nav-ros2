"""Fuses observations into a persistent object map, displayed in RViz.

Subscribes : /semantic_nav/observations (SemanticObjectArray)
Publishes  : /semantic_nav/objects      (SemanticObjectArray, confirmed objects, 1 Hz)
             /semantic_nav/markers      (visualization_msgs/MarkerArray)
Writes     : snapshot_path (JSON) at each publication, used by the offline evaluation.
"""
import json
from pathlib import Path

import rclpy
from rclpy.node import Node
from visualization_msgs.msg import Marker, MarkerArray

from semantic_nav.semantic_map import SemanticMap
from semantic_nav_interfaces.msg import SemanticObject, SemanticObjectArray


class SemanticMapNode(Node):
    def __init__(self):
        super().__init__("semantic_map")
        self.declare_parameter("map_frame", "map")
        self.declare_parameter("assoc_radius", 0.5)
        self.declare_parameter("min_observations", 3)
        self.declare_parameter("min_confidence", 0.4)
        self.declare_parameter("snapshot_path", "/tmp/semantic_map.json")

        self.map_frame = self.get_parameter("map_frame").value
        self.snapshot = Path(self.get_parameter("snapshot_path").value)
        self.map = SemanticMap(
            assoc_radius=self.get_parameter("assoc_radius").value,
            min_observations=self.get_parameter("min_observations").value,
            min_confidence=self.get_parameter("min_confidence").value,
        )
        self.create_subscription(SemanticObjectArray, "/semantic_nav/observations", self.on_obs, 10)
        self.pub = self.create_publisher(SemanticObjectArray, "/semantic_nav/objects", 10)
        self.pub_markers = self.create_publisher(MarkerArray, "/semantic_nav/markers", 10)
        self.create_timer(1.0, self.publish)
        self.get_logger().info("semantic map ready")

    def on_obs(self, msg: SemanticObjectArray):
        t = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        for o in msg.objects:
            self.map.add_observation(o.label, (o.position.x, o.position.y, o.position.z),
                                     o.confidence, t)

    def publish(self):
        now = self.get_clock().now().to_msg()
        out = SemanticObjectArray()
        out.header.stamp, out.header.frame_id = now, self.map_frame
        markers = MarkerArray()
        confirmed = self.map.confirmed()
        for obj in confirmed:
            m = SemanticObject()
            m.id, m.label, m.confidence, m.n_observations = obj.object_id, obj.label, obj.max_conf, obj.n_obs
            m.position.x, m.position.y, m.position.z = obj.x, obj.y, obj.z
            out.objects.append(m)
            markers.markers.extend(self._markers(obj, now))
        self.pub.publish(out)
        self.pub_markers.publish(markers)
        self.snapshot.write_text(json.dumps([o.as_dict() for o in confirmed], indent=2))

    def _markers(self, obj, stamp):
        sphere = Marker()
        sphere.header.frame_id, sphere.header.stamp = self.map_frame, stamp
        sphere.ns, sphere.id, sphere.type = "objects", obj.object_id, Marker.SPHERE
        sphere.pose.position.x, sphere.pose.position.y, sphere.pose.position.z = obj.x, obj.y, 0.2
        sphere.pose.orientation.w = 1.0
        sphere.scale.x = sphere.scale.y = sphere.scale.z = 0.25
        sphere.color.r, sphere.color.g, sphere.color.b, sphere.color.a = 0.1, 0.6, 1.0, 0.9

        text = Marker()
        text.header = sphere.header
        text.ns, text.id, text.type = "labels", obj.object_id, Marker.TEXT_VIEW_FACING
        text.pose.position.x, text.pose.position.y, text.pose.position.z = obj.x, obj.y, 0.55
        text.pose.orientation.w = 1.0
        text.scale.z = 0.2
        text.color.r = text.color.g = text.color.b = text.color.a = 1.0
        text.text = f"{obj.label} #{obj.object_id} ({obj.n_obs})"
        return [sphere, text]


def main():
    rclpy.init()
    node = SemanticMapNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
