from glob import glob

from setuptools import find_packages, setup

package_name = "semantic_nav"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", glob("launch/*.py")),
        ("share/" + package_name + "/config", glob("config/*")),
        ("share/" + package_name + "/eval", glob("eval/*.yaml")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Esso-Manam MANGANMANA",
    maintainer_email="manganmanasamuel@gmail.com",
    description="Semantic mapping and natural-language navigation (ROS 2 / Nav2)",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "detector = semantic_nav.detector_node:main",
            "localizer = semantic_nav.localizer_node:main",
            "semantic_map = semantic_nav.semantic_map_node:main",
            "commander = semantic_nav.commander_node:main",
            "evaluate_map = semantic_nav.evaluate_map:main",
        ],
    },
)
