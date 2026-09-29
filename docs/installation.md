# Installation

Configuration cible, à ne plus changer une fois qu'elle marche :

| Élément | Version |
|---|---|
| OS | Ubuntu 24.04 LTS (natif ou dual boot de préférence) |
| ROS 2 | Jazzy Jalisco (LTS, supportée jusqu'en 2029) |
| Simulateur | Gazebo Harmonic (celui qui va avec Jazzy) |
| Python | 3.12 (celui d'Ubuntu 24.04) |

Sous Windows, WSL2 avec Ubuntu 24.04 fonctionne (Gazebo s'affiche via WSLg), mais c'est plus lent et
parfois instable pour le rendu 3D. Si tu peux, fais un dual boot. Les salles de TP de l'UTBM ont
peut-être aussi des postes Ubuntu avec ROS 2 : demande.

## 1. ROS 2 Jazzy

Suis la page officielle, c'est elle qui fait foi si une commande change :
https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html

Au moment d'écrire ces lignes, cela donne :

```bash
sudo apt install software-properties-common curl -y
sudo add-apt-repository universe
export ROS_APT_SOURCE_VERSION=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | grep -F "tag_name" | awk -F\" '{print $4}')
curl -L -o /tmp/ros2-apt-source.deb "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(. /etc/os-release && echo ${UBUNTU_CODENAME:-${VERSION_CODENAME}})_all.deb"
sudo dpkg -i /tmp/ros2-apt-source.deb
sudo apt update && sudo apt upgrade -y
sudo apt install -y ros-jazzy-desktop ros-dev-tools
echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc && source ~/.bashrc
```

## 2. Simulation, navigation et dépendances du projet

```bash
sudo apt install -y \
  ros-jazzy-ros-gz \
  ros-jazzy-navigation2 ros-jazzy-nav2-bringup \
  ros-jazzy-slam-toolbox \
  ros-jazzy-vision-msgs ros-jazzy-cv-bridge ros-jazzy-tf2-geometry-msgs \
  ros-jazzy-teleop-twist-keyboard \
  python3-scipy python3-yaml python3-pytest
```

`nav2-bringup` tire normalement les paquets de simulation TurtleBot 4 minimal
(`nav2_minimal_tb4_sim`, `nav2_minimal_tb4_description`). Vérifie avec
`ros2 pkg list | grep nav2_minimal`.

## 3. Environnement Python pour YOLO

On isole Ultralytics dans un venv qui voit quand même les paquets ROS (`--system-site-packages`).
Le venv doit être **en dehors** du workspace, sinon colcon essaie de le compiler.

```bash
python3 -m venv --system-site-packages ~/venvs/semnav
source ~/venvs/semnav/bin/activate
pip install ultralytics "numpy<2"
```

Pourquoi `numpy<2` : `cv_bridge` d'Ubuntu 24.04 est compilé contre NumPy 1.x. Si pip installe
NumPy 2, `cv_bridge` plante à l'import avec une erreur peu claire. C'est le piège le plus fréquent.

## 4. LLM local (optionnel, semaine 5)

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:3b     # ~2 Go ; un modèle 3B suffit pour extraire un label
```

Le projet fonctionne sans : `use_llm:=false` utilise le parseur par mots-clés.

## 5. Compiler le workspace

```bash
mkdir -p ~/ros2_ws && cd ~/ros2_ws
git clone <url-de-ton-depot> .        # le dépôt contient le dossier src/
source ~/venvs/semnav/bin/activate
colcon build --symlink-install
source install/setup.bash
```

Tests unitaires (sans lancer la simulation) :

```bash
cd ~/ros2_ws/src/semantic_nav && python3 -m pytest -q test
```

## 6. Terminaux à ouvrir pour une session complète

Dans chaque terminal : `source /opt/ros/jazzy/setup.bash && source ~/ros2_ws/install/setup.bash`
(et `source ~/venvs/semnav/bin/activate` pour le terminal 2).

```bash
# Terminal 1 : simulation + SLAM + Nav2 + RViz
ros2 launch nav2_bringup tb4_simulation_launch.py slam:=True

# Terminal 2 : couche sémantique
ros2 launch semantic_nav semantic_nav.launch.py

# Terminal 3 : explorer, puis donner un ordre
ros2 run teleop_twist_keyboard teleop_twist_keyboard
ros2 topic pub --once /semantic_nav/command std_msgs/msg/String "{data: 'va vers la chaise la plus proche'}"
ros2 topic echo /semantic_nav/status
```
