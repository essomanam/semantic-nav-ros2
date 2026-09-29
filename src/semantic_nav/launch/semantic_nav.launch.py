"""Launch the semantic navigation layer (the simulation and Nav2 run separately).

  ros2 launch semantic_nav semantic_nav.launch.py
  ros2 launch semantic_nav semantic_nav.launch.py use_llm:=false
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    params = os.path.join(get_package_share_directory("semantic_nav"), "config", "params.yaml")
    params_arg = DeclareLaunchArgument("params_file", default_value=params)
    llm_arg = DeclareLaunchArgument("use_llm", default_value="true")
    p = LaunchConfiguration("params_file")

    def node(executable, extra=None):
        return Node(package="semantic_nav", executable=executable, name=executable,
                    parameters=[p] + ([extra] if extra else []), output="screen")

    return LaunchDescription([
        params_arg, llm_arg,
        node("detector"),
        node("localizer"),
        node("semantic_map"),
        node("commander", {"use_llm": ParameterValue(LaunchConfiguration("use_llm"), value_type=bool)}),
    ])
