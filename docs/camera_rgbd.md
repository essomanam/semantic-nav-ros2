# Ajouter une caméra RGB-D au robot simulé (si elle manque)

À faire seulement si, en semaine 1, `ros2 topic list` ne montre aucun topic d'image de profondeur.
Les noms `/rgbd_camera/...` utilisés dans `config/params.yaml` correspondent à la configuration
ci-dessous. Tout ce fichier est **à vérifier sur ta machine** : les détails de Gazebo changent
d'une version à l'autre, et c'est normal d'avoir à ajuster.

## Principe

1. Un lien `camera_link` fixé sur le robot, plus un repère optique `camera_optical_frame`
   (z vers l'avant, x à droite, y vers le bas), tourné de rpy = (-pi/2, 0, -pi/2) par rapport à `camera_link`.
2. Un capteur Gazebo `rgbd_camera` attaché à `camera_link`. Sous Gazebo Harmonic, il publie
   `<topic>/image`, `<topic>/depth_image`, `<topic>/camera_info` et `<topic>/points`.
3. Un pont `ros_gz_bridge` qui fait passer ces topics de Gazebo vers ROS 2.

## Extrait URDF / xacro

Copie le xacro du robot (`nav2_minimal_tb4_description`) dans ton propre package plutôt que de
modifier les fichiers installés, puis ajoute :

```xml
<link name="camera_link"/>
<joint name="camera_joint" type="fixed">
  <parent link="base_link"/>
  <child link="camera_link"/>
  <origin xyz="0.10 0 0.30" rpy="0 0 0"/>
</joint>

<link name="camera_optical_frame"/>
<joint name="camera_optical_joint" type="fixed">
  <parent link="camera_link"/>
  <child link="camera_optical_frame"/>
  <origin xyz="0 0 0" rpy="-1.5708 0 -1.5708"/>
</joint>

<gazebo reference="camera_link">
  <sensor name="rgbd_camera" type="rgbd_camera">
    <always_on>true</always_on>
    <update_rate>10</update_rate>
    <topic>rgbd_camera</topic>
    <gz_frame_id>camera_optical_frame</gz_frame_id>
    <camera>
      <horizontal_fov>1.047</horizontal_fov>
      <image><width>640</width><height>480</height><format>R8G8B8</format></image>
      <clip><near>0.1</near><far>10.0</far></clip>
    </camera>
  </sensor>
</gazebo>
```

Le monde doit charger le système `gz-sim-sensors-system` (c'est déjà le cas si le lidar marche).

## Pont ROS 2 / Gazebo (YAML pour `ros_gz_bridge`)

```yaml
- ros_topic_name: /rgbd_camera/image
  gz_topic_name: /rgbd_camera/image
  ros_type_name: sensor_msgs/msg/Image
  gz_type_name: gz.msgs.Image
  direction: GZ_TO_ROS
- ros_topic_name: /rgbd_camera/depth_image
  gz_topic_name: /rgbd_camera/depth_image
  ros_type_name: sensor_msgs/msg/Image
  gz_type_name: gz.msgs.Image
  direction: GZ_TO_ROS
- ros_topic_name: /rgbd_camera/camera_info
  gz_topic_name: /rgbd_camera/camera_info
  ros_type_name: sensor_msgs/msg/CameraInfo
  gz_type_name: gz.msgs.CameraInfo
  direction: GZ_TO_ROS
```

## Vérifications

```bash
ros2 topic hz /rgbd_camera/image                      # ~10 Hz attendus
ros2 topic echo --once /rgbd_camera/depth_image --field encoding   # 32FC1 attendu
ros2 run tf2_ros tf2_echo map camera_optical_frame     # la transformation doit exister
ros2 run rqt_image_view rqt_image_view                 # voir les images
```

Si le `frame_id` des images ne correspond à aucun repère TF, la localisation 3D échouera
(le localizer affiche alors un avertissement TF). C'est le rôle de `gz_frame_id`.
