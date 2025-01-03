import os

import torch
import numpy as np
import sys
import random

from ns3_interface import Ns3Simulator
from my_model import MyAgent

def set_seed(seed):
    torch.manual_seed(seed)
    np.random.seed(seed)
    random.seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)

# Al inicio de cada entrenamiento
seed = 45  # Cambia este número en cada experimento
set_seed(seed)

torch.set_num_threads(5)

env = Ns3Simulator()
input_size = env.observation_space.shape[0]
action_size = env.num_actions
print(input_size)
print(action_size)
new_agent = MyAgent(input_size, action_size, learning_rate=1e-4)


# Parámetros de entrenamiento
num_episodes = 394
env.start()
for episode in range(num_episodes):
    #state = env.reset()
    episode_reward = 0
    done = False

    while not done:
        #Input con los nuevos datos y el nodo de ns3
        state, node_index = env.wait_adr_request()
        action = new_agent.select_action(state, node_index)
        #print("Action: " + str(action))

        next_state, reward, done, _ = env.step(action)
        # Mensaje a NS-3 con la PT (y SF)
        new_agent.rewards.append(reward)
        state = next_state
        episode_reward += reward
    # Recibir energia NS-3
    new_agent.finish_episode()
    print(f"Episodio {episode+1}/{num_episodes}, Recompensa total: {episode_reward:.2f}")

os.mkdir("policy_network_008")
for i in range(new_agent.N):
    name = "policy_network_" + str(i).zfill(4) + ".pth"
    path = "policy_network_008/" + name
    torch.save(new_agent.policy_network[i].state_dict(), path)
print('Modelo guardado en policy_network')