import numpy as np

def get_flat_state(self):
    states = []
    for node_index in range(self.N):
        state = self.get_state_for_node(node_index)
        if node_index == self.current_node:
            indicator = 1.0  # Nodo actual
        else:
            indicator = 0.0  # Otros nodos
        state.append(indicator)  # Agregar el indicador al estado del nodo
        states.extend(state)  # Agregar las características del nodo al vector de estado
    return np.array(states, dtype=np.float32)