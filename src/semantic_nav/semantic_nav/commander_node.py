"""Natural-language command -> Nav2 goal in front of the selected object.

Subscribes : /semantic_nav/command (std_msgs/String), e.g. "va vers la chaise la plus proche"
             /semantic_nav/objects (SemanticObjectArray)
Action     : navigate_to_pose (nav2_msgs/action/NavigateToPose)
Publishes  : /semantic_nav/status  (std_msgs/String)
Writes     : trials_csv, one line per command (used for the success-rate metric)

Try it:
  ros2 topic pub --once /semantic_nav/command std_msgs/msg/String "{data: 'va vers la chaise'}"
"""
import csv
import math
import time
from pathlib import Path

import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.time import Time
from std_msgs.msg import String
from tf2_ros import Buffer, TransformException, TransformListener

from semantic_nav.command_parser import ollama_client, parse_command
from semantic_nav.geometry import approach_pose, yaw_to_quaternion
from semantic_nav.semantic_map import SemanticMap, SemanticObject as Obj
from semantic_nav_interfaces.msg import SemanticObjectArray


class CommanderNode(Node):
    def __init__(self):
        super().__init__("commander")
        self.declare_parameter("map_frame", "map")
        self.declare_parameter("base_frame", "base_link")
        self.declare_parameter("standoff", 0.7)
        self.declare_parameter("use_llm", True)
        self.declare_parameter("llm_model", "qwen2.5:3b")
        self.declare_parameter("trials_csv", "/tmp/semantic_nav_trials.csv")

        self.map_frame = self.get_parameter("map_frame").value
        self.base_frame = self.get_parameter("base_frame").value
        self.standoff = self.get_parameter("standoff").value
        self.llm = ollama_client(self.get_parameter("llm_model").value) \
            if self.get_parameter("use_llm").value else None
        self.trials = Path(self.get_parameter("trials_csv").value)

        self.map = SemanticMap(min_observations=1)  # the map node already filters
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.nav = ActionClient(self, NavigateToPose, "navigate_to_pose")
        self.status_pub = self.create_publisher(String, "/semantic_nav/status", 10)
        self.create_subscription(SemanticObjectArray, "/semantic_nav/objects", self.on_objects, 10)
        self.create_subscription(String, "/semantic_nav/command", self.on_command, 10)
        self.current = None  # info about the running trial
        self.get_logger().info("commander ready")

    # ---------------------------------------------------------------- inputs
    def on_objects(self, msg: SemanticObjectArray):
        self.map.objects = {
            o.id: Obj(o.id, o.label, o.position.x, o.position.y, o.position.z,
                      n_obs=o.n_observations, max_conf=o.confidence)
            for o in msg.objects
        }

    def robot_xy(self):
        tf = self.tf_buffer.lookup_transform(self.map_frame, self.base_frame, Time())
        return tf.transform.translation.x, tf.transform.translation.y

    def on_command(self, msg: String):
        text = msg.data.strip()
        parsed = parse_command(text, self.map.labels(), self.llm)
        if parsed is None:
            return self.say(f"Commande non comprise ou objet inconnu : '{text}'. "
                            f"Objets connus : {self.map.labels()}")
        try:
            rxy = self.robot_xy()
        except TransformException as exc:
            return self.say(f"Position du robot indisponible : {exc}")
        target = self.map.query(parsed.label, rxy, parsed.criterion)
        if target is None:
            return self.say(f"Aucun objet '{parsed.label}' dans la carte.")

        gx, gy, yaw = approach_pose(rxy, (target.x, target.y), self.standoff)
        goal = NavigateToPose.Goal()
        goal.pose = PoseStamped()
        goal.pose.header.frame_id = self.map_frame
        goal.pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose.pose.position.x, goal.pose.pose.position.y = gx, gy
        (goal.pose.pose.orientation.x, goal.pose.pose.orientation.y,
         goal.pose.pose.orientation.z, goal.pose.pose.orientation.w) = yaw_to_quaternion(yaw)

        if not self.nav.wait_for_server(timeout_sec=2.0):
            return self.say("Serveur Nav2 'navigate_to_pose' indisponible.")
        self.current = {"command": text, "label": parsed.label, "criterion": parsed.criterion,
                        "parser": parsed.source, "target_id": target.object_id,
                        "tx": target.x, "ty": target.y, "t0": time.time()}
        self.say(f"Cible : {parsed.label} #{target.object_id} ({parsed.source}), "
                 f"objectif ({gx:.2f}, {gy:.2f})")
        self.nav.send_goal_async(goal).add_done_callback(self.on_goal_accepted)

    # ------------------------------------------------------------ nav result
    def on_goal_accepted(self, future):
        handle = future.result()
        if not handle.accepted:
            self.log_trial(False, "rejected")
            return self.say("Objectif refusé par Nav2.")
        handle.get_result_async().add_done_callback(self.on_result)

    def on_result(self, future):
        status = future.result().status
        ok = status == GoalStatus.STATUS_SUCCEEDED
        self.log_trial(ok, str(status))
        self.say("Arrivé devant l'objet." if ok else f"Navigation échouée (statut {status}).")

    def log_trial(self, success: bool, status: str):
        if self.current is None:
            return
        t0 = self.current.pop("t0")
        row = dict(self.current, success=int(success), status=status,
                   duration_s=round(time.time() - t0, 2))
        try:
            rx, ry = self.robot_xy()
            row["final_dist_to_object_m"] = round(math.hypot(rx - row["tx"], ry - row["ty"]), 3)
        except TransformException:
            row["final_dist_to_object_m"] = ""
        new = not self.trials.exists()
        with self.trials.open("a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(row))
            if new:
                w.writeheader()
            w.writerow(row)
        self.current = None

    def say(self, text: str):
        self.get_logger().info(text)
        self.status_pub.publish(String(data=text))


def main():
    rclpy.init()
    node = CommanderNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
