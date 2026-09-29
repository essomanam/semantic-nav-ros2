# One object of the semantic map (or one raw observation, then n_observations = 1)
uint32 id
string label
geometry_msgs/Point position   # in header.frame_id of the parent array (map)
float32 confidence
uint32 n_observations
