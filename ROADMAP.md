# Feuille de route : 6 semaines + 1 de marge

Du 28 septembre au 15 novembre 2026, à raison d'environ 8 à 10 h par semaine à côté du M2.
Chaque semaine se termine par un critère « c'est fini quand... » vérifiable, et par un commit.
Si une semaine déborde, on rogne sur les extensions, jamais sur l'évaluation (semaine 6) :
c'est elle qui fait la différence avec un projet de tutoriel.

Ce dépôt contient déjà le squelette de tous les nœuds et 22 tests unitaires sur la partie
algorithmique. Ton travail consiste à le faire tourner dans la simulation, à comprendre et
ajuster chaque brique, et à mesurer les résultats.

---

## Semaine 1 (28 sept. au 4 oct.) : environnement et robot qui se déplace

- [ ] Installer Ubuntu 24.04, ROS 2 Jazzy, Gazebo et Nav2 (`docs/installation.md`, étapes 1 et 2)
- [ ] Lancer `ros2 launch nav2_bringup tb4_simulation_launch.py slam:=True`
- [ ] Piloter le robot au clavier, regarder la carte se construire dans RViz
- [ ] Envoyer un objectif avec le bouton « Nav2 Goal » de RViz
- [ ] Faire l'inventaire des topics et des repères :
      `ros2 topic list`, `ros2 run tf2_tools view_frames` (génère un PDF de l'arbre TF)
- [ ] **Question clé :** le robot a-t-il une caméra RGB-D ? Cherche un topic de profondeur.
      Si non, la tâche de la semaine 2 est d'en ajouter une (`docs/camera_rgbd.md`).
- [ ] Créer le dépôt GitHub et pousser ce squelette

**C'est fini quand** le robot atteint un objectif cliqué dans RViz sur une carte construite par SLAM.

Notions à maîtriser en parallèle (le tutoriel officiel ROS 2 « Beginner: CLI tools » et
« Client libraries » suffisent) : nœud, topic, service, action, paramètre, launch, TF.

## Semaine 2 (5 au 11 oct.) : caméra et monde avec des objets

- [ ] Si besoin, ajouter la caméra RGB-D (`docs/camera_rgbd.md`)
- [ ] Ajouter au monde 6 à 10 objets que YOLO sait reconnaître (classes COCO : chaise, canapé,
      plante en pot, table, télé, lit...). Les modèles Gazebo Fuel (https://app.gazebosim.org/fuel)
      en proposent beaucoup.
- [ ] Noter la position exacte de chaque objet dans `eval/ground_truth.yaml`
      (attention au décalage entre le repère du monde et le repère `map`, voir le commentaire du fichier)
- [ ] Mettre à jour les noms de topics dans `config/params.yaml`
- [ ] Visualiser l'image et la profondeur dans `rqt_image_view`

**C'est fini quand** tu vois les objets dans l'image de la caméra et que la profondeur a des valeurs cohérentes.

## Semaine 3 (12 au 18 oct.) : détection et projection 3D

- [ ] Créer le venv et installer Ultralytics (`docs/installation.md`, étape 3)
- [ ] Lancer `ros2 run semantic_nav detector --ros-args --params-file ...` et regarder
      `/semantic_nav/detections_image`
- [ ] Mesurer ce que YOLO détecte vraiment sur les rendus Gazebo. Les images de synthèse
      diffèrent des photos réelles (écart de domaine) : certaines classes seront mal reconnues.
      Note-le, c'est un résultat.
- [ ] Lancer `localizer` et vérifier dans RViz (ajoute un affichage des `/semantic_nav/observations`
      ou échoue proprement sur les avertissements TF)
- [ ] Relire `geometry.py` et savoir réexpliquer au tableau la rétroprojection sténopé et le passage
      repère optique -> `map` : c'est une question d'entretien classique

**C'est fini quand** les observations d'une chaise tombent à moins de ~30 cm de sa vraie position.

## Semaine 4 (19 au 25 oct.) : carte sémantique

- [ ] Lancer `semantic_map`, afficher `/semantic_nav/markers` (MarkerArray) dans RViz
- [ ] Explorer toute la pièce et vérifier que chaque objet apparaît une seule fois
- [ ] Régler `assoc_radius` et `min_observations` : que se passe-t-il avec deux chaises côte à côte ?
- [ ] Première évaluation :
      `ros2 run semantic_nav evaluate_map --pred /tmp/semantic_map.json --gt eval/ground_truth.yaml`

**C'est fini quand** la carte contient tous les objets visibles, sans doublon, et que tu as un premier chiffre d'erreur moyenne.

## Semaine 5 (26 oct. au 1er nov.) : commande en langage naturel et navigation

- [ ] Tester d'abord sans LLM : `ros2 launch semantic_nav semantic_nav.launch.py use_llm:=false`
- [ ] Envoyer « va vers la chaise la plus proche » et regarder le robot y aller
- [ ] Installer Ollama et un modèle 3B, puis relancer avec le LLM
- [ ] Préparer 20 à 30 phrases de test, dont des formulations indirectes
      (« rejoins l'endroit où on peut s'asseoir ») : c'est là que le LLM doit apporter
      quelque chose par rapport aux mots-clés, et il faut le mesurer

**C'est fini quand** le robot rejoint le bon objet à partir d'une phrase, avec et sans LLM.

## Semaine 6 (2 au 8 nov.) : évaluation, vidéo, README

- [ ] Protocole de navigation : 30 commandes depuis des positions de départ variées.
      Les résultats s'enregistrent tout seuls dans `/tmp/semantic_nav_trials.csv`.
- [ ] Calculer : taux de réussite, durée moyenne, distance finale à l'objet
- [ ] Comparer le parseur par mots-clés et le LLM sur tes phrases de test
      (taux de bonne interprétation, latence)
- [ ] Mesurer la latence du détecteur (CPU, et GPU si disponible)
- [ ] Enregistrer une vidéo de démo de 60 à 90 s (Gazebo + RViz côte à côte, commande tapée à l'écran)
- [ ] Remplir le README : GIF en haut, tableau des résultats, limites

**C'est fini quand** un inconnu comprend le projet en 30 secondes en ouvrant le dépôt.

## Semaine 7 (9 au 15 nov.) : marge, puis diffusion

- [ ] Rattraper le retard éventuel
- [ ] Post LinkedIn : problème, schéma, vidéo, un chiffre clé, lien GitHub
- [ ] Ajouter le projet dans la section Projets de LinkedIn et sur le CV

---

## Extensions (seulement si tout ce qui précède est fini)

| Extension | Ce qu'elle montre | Effort |
|---|---|---|
| Export du détecteur en ONNX ou TensorRT, mesure du gain de latence | IA embarquée | Faible |
| Fine-tuning de YOLO sur des images Gazebo annotées automatiquement (les positions sont connues) | Adaptation de domaine, ton point fort en data science | Moyen |
| Suppression des objets qui ont disparu (décroissance de confiance quand l'objet devrait être visible mais ne l'est pas) | Cartographie dynamique | Moyen |
| Exploration autonome (frontières) au lieu de la téléopération | Autonomie complète | Moyen à élevé |
| Test sur un vrai TurtleBot du labo | Passage simulation vers réel | Selon matériel |

## Journal de bord

Tiens un fichier `NOTES.md` : chaque bug résolu, chaque choix de paramètre et pourquoi.
En entretien, « j'ai eu tel problème, voilà comment je l'ai diagnostiqué » vaut plus que la démo elle-même.
