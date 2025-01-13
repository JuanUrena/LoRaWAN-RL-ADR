# test.py

import torch
from my_model import MyNeuralNetwork
from ns3_interface import Ns3Simulator

# Configuración
env = Ns3Simulator()
input_size = env.observation_space.shape[0]
action_size = env.num_actions
policy_network = {}
# Crear instancia del modelo
for i in range(env.N):
    policy_network[i] = MyNeuralNetwork(input_size, action_size)
    name = "policy_network_" + str(i).zfill(4) + ".pth"
    path = "policy_network_017/" + name
    policy_network[i].load_state_dict(torch.load(path))
    policy_network[i].eval()

# Cargar el modelo entrenado
# policy_network.load_state_dict(torch.load('policy_network_007.pth'))
# policy_network.eval()

# Función de selección de acción
def select_action(state, node_index):
    state_tensor = torch.FloatTensor(state).unsqueeze(0)
    with torch.no_grad():
        probs = policy_network[node_index](state_tensor)
    action = torch.argmax(probs, dim=1).item()
    """
    m = torch.distributions.Categorical(probs)
    action = m.sample().item()
    return action
    """
    return action

# Ejecutar episodios de testeo
num_test_episodes = 205
env.start()
for episode in range(num_test_episodes):
    #state = env.reset()
    done = False
    total_reward = 0

    while not done:
        # Input con los nuevos datos y el nodo de ns3
        state, node_index = env.wait_adr_request()

        action = select_action(state, node_index)
        next_state, reward, done, info = env.step(action)
        total_reward += reward
        state = next_state

    print(f'Episodio de testeo {episode+1}/{num_test_episodes} completado, Recompensa total: {total_reward}')
