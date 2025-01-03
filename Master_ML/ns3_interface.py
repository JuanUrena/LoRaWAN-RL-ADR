import os
import subprocess
import sys
import threading
import shutil
import numpy as np
import gym
import math
import fcntl
from cloudinit.version import FEATURES
from gym import spaces
from tensorflow.python.keras.engine.data_adapter import select_data_adapter
from xdg.BaseDirectory import xdg_data_dirs

FEATURE_ID = 0
FEATURE_X = 1
FEATURE_Y = 2
FEATURE_TP = 3
FEATURE_SF = 4
FEATURE_SNR = 5
FEATURE_GW_CLOSER = 6
FEATURE_DIST_GW = 7

FEATURE_CURRENT_NODE = 8
#FEATURE_DIST_GW = 5

DICT_ACTION_TP = {0:[2, 12],
                  1:[4, 12],
                  2:[6, 12],
                  3:[8, 12],
                  4:[10, 12],
                  5:[12, 12],
                  6:[14, 12],
                  7:[2, 11],
                  8:[4, 11],
                  9:[6, 11],
                  10:[8, 11],
                  11:[10, 11],
                  12:[12, 11],
                  13:[14, 11],
                  14:[2, 10],
                  15:[4, 10],
                  16:[6, 10],
                  17:[8, 10],
                  18:[10, 10],
                  19:[12, 10],
                  20:[14, 10],
                  21: [2, 9],
                  22: [4, 9],
                  23: [6, 9],
                  24: [8, 9],
                  25: [10, 9],
                  26: [12, 9],
                  27: [14, 9],
                  28: [2, 8],
                  29: [4, 8],
                  30: [6, 8],
                  31: [8, 8],
                  32: [10, 8],
                  33: [12, 8],
                  34: [14, 8],
                  35: [2, 7],
                  36: [4, 7],
                  37: [6, 7],
                  38: [8, 7],
                  39: [10, 7],
                  40: [12, 7],
                  41: [14, 7]
                  }



SIZE = 10000
MAX_TP = 14
MIN_SF = 7
MAX_SF = 12

class Ns3Simulator(gym.Env):
    def __init__(self):
        self.clean_tmp_folder()
        super(Ns3Simulator, self).__init__()


        # ... Run NS-3 ...
        self.end_devices_features = None
        self.energy_consumed = {}
        self.N = 100 # Número de nodos
        self.first_node_id = -1
        self.d = 8 # Número de características por nodo id, x, y, tp, snr, closer_gw, dist_gw
        self.num_tp= 7 # 7 niveles de pot -> 2, 4, 6, 8, 10, 12, 14
        self.num_sf = 6  # 7 niveles de pot -> 12, 11, 10, 9, 8, 7

        self.num_actions = self.num_sf * self.num_tp

        # Agregamos 1 al número de características por el indicador del nodo actual
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(self.N * (self.d + 1),), dtype=np.float32
        )
        self.action_space = spaces.Discrete(self.num_actions)

        self.input = open("/tmp/pipe2python", "w+")
        self.adr_request = open("/tmp/ADR_req", "w+")
        self.adr_interface = "/tmp/model_answer"
        self.adr_interface_copy = "/tmp/store_mess"
        self.adr_ack_file = "/tmp/ADR_ack"
        self.energy_consumed_file = "/tmp/energy_consumed"
        thread = threading.Thread(target=self.run_ns3)
        thread.start()

        self.gw_x = {}
        self.gw_y = {}
        self.gw_first_id = float('inf')
        self.gw_number = 0
        self.min_dist_max = 0

        self.ed_number = 0

        self.mac_to_devices = {}
        self.end_devices_features = []
        self.end_devices_features, self.mac_to_devices = self.get_data_ns3()



        self.current_node = 0  # indice del nodo actual
        self.configured_node = []
        self.state = None

        self.auxiliar_previous_node = 0

    def run_ns3(self):
        command = ["/home/juan/ns-allinone-3.43/ns-3.43/ns3 run scratch/adr-example-juan"]
        subprocess.run(command, shell=True)

    def clean_tmp_folder(self):
        if os.path.exists("/tmp/python_signal"):
            os.remove("/tmp/python_signal")
        if os.path.exists("/tmp/pipe2python"):
            os.remove("/tmp/pipe2python")
        if os.path.exists("/tmp/ADR_req"):
            os.remove("/tmp/ADR_req")
        if os.path.exists("/tmp/ADR_signal"):
            os.remove("/tmp/ADR_signal")
        if os.path.exists("/tmp/energy_consumed"):
            os.remove("/tmp/energy_consumed")
        if os.path.exists("/tmp/store_mess"):
            os.remove("/tmp/store_mess")


    def start(self):
        file = open("/tmp/python_signal", "w+")
        fcntl.flock(file.fileno(), fcntl.LOCK_EX)
        file.write("Start")
        fcntl.flock(file.fileno(), fcntl.LOCK_UN)
        file.close()


    def get_data_ns3(self):
        # Ejecuto ns-3 en un hilo nuevo

        dict_mac = {}
        end_devices_data = []
        n = 0

        while True:
            line = self.input.readline()
            if len(line):
                #print(line)

                line = line[:-1]
                line_splitted = line.split(":")

                component = line_splitted[0]
                data_csv = line_splitted[1]
                if component == "ED":
                    # Info about ED
                    n = n + 1
                    end_devices_data, dict_mac = self.process_new_end_device(end_devices_data, data_csv, dict_mac)
                elif component == "GW":
                    gw_data = self.process_new_gw(self.gw_x, self.gw_y, data_csv)
            if n == self.N:
                end_devices_data = self.last_process_ed(end_devices_data)
                return  end_devices_data, dict_mac

    def last_process_ed(self, data):

        for data_row in data:
            data_row[FEATURE_ID] = (data_row[FEATURE_ID] - self.first_node_id) / self.ed_number
            data_row[FEATURE_DIST_GW] = data_row[FEATURE_DIST_GW] / self.min_dist_max

        return data



    def process_position(self, position):
        position = float(position)
        new_position = (position + SIZE)/ (SIZE*2)
        if new_position < 0:
            print("Hello")
        return new_position


    def process_tp(self, tp):

        new_tp = int(tp) / MAX_TP

        return new_tp

    def process_sf(self, sf):

        new_sf = (int(sf) - MIN_SF) / MAX_SF

        return new_sf

    def process_snr(self, snr):
        snr_aux = 0
        new_snr = 0
        snr = float(snr)
        if snr < -20:
            snr_aux = -22
        elif snr > -7.5:
            snr_aux = -6
        else:
            snr_aux = snr

        snr_aux = snr_aux + 22
        new_snr = snr_aux / (22 - 6)

        return new_snr

    def process_gw_id(self, id):
        new_id = (id - self.gw_first_id) / self.gw_number
        return new_id

    def process_new_gw(self, data_x, data_y, new_data):
        data_splitted = new_data.split(",")
        #print(data_splitted)

        id = int(data_splitted[0])
        x = float(data_splitted[1])
        y = float(data_splitted[2])

        data_x[id] = x
        data_y[id] = y

        if id < self.gw_first_id:
            self.gw_first_id = id

        self.gw_number = self.gw_number + 1


        return data_x, data_y


    def calculate_closer_gw(self, x_nodo, y_nodo):

        distancia_min = float('inf')  # Inicializamos con infinito
        id_gw_mas_cercana = None

        for gw_id in self.gw_x.keys():
            x_gw = self.gw_x[gw_id]
            y_gw = self.gw_y[gw_id]

            # Calculamos la distancia euclidiana
            distancia = math.sqrt((x_nodo - x_gw) ** 2 + (y_nodo - y_gw) ** 2)

            # Actualizamos la GW más cercana si encontramos una distancia menor
            if distancia < distancia_min:
                distancia_min = distancia
                id_gw_mas_cercana = gw_id

                if distancia > self.min_dist_max:
                    self.min_dist_max = distancia

        return id_gw_mas_cercana, distancia_min


    def process_new_end_device(self, data, new_data, dict_mac):
        data_splitted = new_data.split(",")
        #print(data_splitted)
        new_device_features = []

        new_device_features.append(int(data_splitted[0]))
        x_data = float(data_splitted[1])
        y_data = float(data_splitted[2])
        new_device_features.append(self.process_position(x_data))
        new_device_features.append(self.process_position(y_data))
        new_device_features.append(self.process_tp(MAX_TP)) # Por defecto la TP inicial es 14
        new_device_features.append(self.process_sf(MAX_SF))
        new_device_features.append(1) # No conocemos la SNR

        closer_gw, min_dist = self.calculate_closer_gw(x_data, y_data)
        new_device_features.append(self.process_gw_id(int(closer_gw)))
        new_device_features.append(min_dist)


        data.append(new_device_features)
        id_node = int(data_splitted[0])
        if id_node < self.first_node_id or self.first_node_id == -1 :
            self.first_node_id = id_node
        self.ed_number = self.ed_number + 1
        dict_mac[data_splitted[3]] = id_node

        return data, dict_mac



    def initialize_end_devices_features(self):
        end_devices = {
            "node_ID": [],
            "pos_x": [],
            "pos_y": [],
            "mac": []
        }
        return end_devices


    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        if seed is not None:
            np.random.seed(seed)

        self.current_node = 0
        self.configured_node = []
        self.end_devices_features = self.initialize_end_devices_features()
        self.state = self.get_flat_state()
        return self.state

    def check_new_adr_request(self):
        if os.path.exists("/tmp/adr_flag"):
            #print("FLAG")
            return True
        else:
            return False

    def wait_adr_request(self):
        while True:
            if os.path.exists("/tmp/adr_flag"):
                #print("FLAG")
                os.remove("/tmp/adr_flag")
            else:
                continue

            new_request = self.adr_request.readline()
            #print(new_request)
            if len(new_request):
                new_request = new_request[:-1]
                line_splitted = new_request.split(":")

                component = line_splitted[0]
                data_csv = line_splitted[1]
                #print(data_csv)

                if component == "ADR":
                    data_splitted = data_csv.split(",")
                    node_mac = data_splitted[0]
                    node_TP = data_splitted[1]
                    node_SF = data_splitted[2]
                    node_SNR = data_splitted[3]

                    break
        self.update_node_feature(node_mac, node_TP, node_SF, node_SNR)
        self.state = self.get_flat_state()
        return self.state, self.current_node

    def update_node_feature(self, mac, tp, sf, snr):
        #Update SNR, TP, SF from the info received
        node_id = self.mac_to_devices[mac]

        node_index = node_id - self.first_node_id

        self.set_snr_for_node(node_index, self.process_snr(snr))
        self.set_tp_for_node(node_index, self.process_tp(tp))
        self.set_sf_for_node(node_index, self.process_sf(sf))
        self.current_node = node_index


    def step(self, action):
        # Aplica la acción al nodo actual
        tp_sf_action = DICT_ACTION_TP[action]
        tp_action = tp_sf_action[0]
        sf_action = tp_sf_action[1]
        #print("Action: " + str(action) + ". TP: " + str(tp_action)+ "; SF: " + str(sf_action))
        self.set_tp_for_node(self.current_node, self.process_tp(tp_action))
        self.set_sf_for_node(self.current_node, self.process_sf(sf_action))
        # Info a ns-3
        adr_interface_pipe = open(self.adr_interface, "w")
        fcntl.flock(adr_interface_pipe.fileno(), fcntl.LOCK_EX)
        adr_interface_pipe.write(str(sf_action).zfill(2) + "," + str(tp_action).zfill(2))
        fcntl.flock(adr_interface_pipe.fileno(), fcntl.LOCK_UN)
        adr_interface_pipe.close()
        adr_interface_pipe_copy = open(self.adr_interface_copy, "a")
        adr_interface_pipe_copy.write(str(sf_action).zfill(2) + "," + str(tp_action).zfill(2) + "; ")
        adr_interface_pipe_copy.close()
        #print("Action to NS3")
        #print("ACK")
        while True:

            if os.path.exists(self.adr_ack_file):
                #print("Found ACK")
                os.remove(self.adr_ack_file)
                #print(os.path.exists(self.adr_ack_file))
                break
        if not self.current_node in self.configured_node:
            self.configured_node.append(self.current_node)
        # Si no es una retransmision
        # Avanza al siguiente nodo o finaliza el episodio



        done = False
        if len(self.configured_node) < self.N:
            #self.state = self.get_flat_state() # Creo que no hace falta, ya que luego llegara una req y lo hare con mas info nueva
            reward = 0  # Recompensa diferida
        else:

            # Puede que tengamos retansmisiones de los utlimo


            # Todos los nodos han sido configurados, esperar a la recompensa
            # Obtén la recompensa basada en el consumo energético total
            reward = 0
            while True:
                if os.path.exists(self.energy_consumed_file):
                    #print("Energia encontrada")
                    reward = self.get_reward()  # Negativo para minimizar
                    done = True
                    self.configured_node = []
                    break
                elif self.check_new_adr_request():
                    reward = 0
                    break
            #self.state = self.get_flat_state() # Creo que no hace falta, ya que luego llegara una req y lo hare con mas info nueva


        return self.state, reward, done, {}

    def get_flat_state(self):
        # Retorna el estado como un vector aplanado con el indicador del nodo actual
        states = []
        for node_i in range(self.N):
            state = self.end_devices_features[node_i].copy()
            #print(state)
            #state[FEATURE_ID] = (state[FEATURE_ID] - self.first_node_id) / self.ed_number
            # Indicamos a la red neuronal cual es el nodo de la acción
            if node_i == self.current_node:
                indicator = 1  # Nodo actual
            else:
                indicator = 0  # Otros nodos
            state.append(indicator)  # Agregar el indicador al estado del nodo
            states.extend(state)
        return np.array(states, dtype=np.float32)

    def set_tp_for_node(self, node_index, tp_value):
        # Establece la TP para el nodo especificado
        self.end_devices_features[node_index][FEATURE_TP] = int(tp_value)

    def set_sf_for_node(self, node_index, sf_value):
        # Establece la TP para el nodo especificado
        self.end_devices_features[node_index][FEATURE_SF] = int(sf_value)

    def set_snr_for_node(self, node_index, snr_value):
        # Establece la TP para el nodo especificado
        valor_snr = float(snr_value)
        self.end_devices_features[node_index][FEATURE_SNR] = float(snr_value)




    def get_reward(self):
        # Esperar el consumo de energia desde NS-3 y sumar
        total_energy_consumption = self.get_total_energy_consumption()
        reward = -total_energy_consumption  # Negativo para minimizar
        print("Recompensa Intervalo: " + str(reward))
        #print("Recompensa Almacenada:")
        energy_total = 0
        #for i_timestamp, i_value in self.energy_consumed.items():
        #    print(str(i_timestamp) + " : " + str(i_value))
        #    energy_total = energy_total + i_value
        #print("Total : " + str(energy_total))

        return reward

    def get_reward_from_NS3(self):
        # Leer fichero desde NS-3
        #print("Esperando energia")
        while True:
            if os.path.exists(self.energy_consumed_file):
                #print("Energia encontrada")
                file_energy = open(self.energy_consumed_file, "r+")
                break
            else:

                continue
        energy_used_network = {}
        all_devices_energy = False
        while not all_devices_energy:
            for line in file_energy:
                all_devices_energy = False
                line = line[:-1]
                line_splitted = line.split(":")

                component = line_splitted[0]
                data_csv = line_splitted[1]
                if component == "ENG":
                    timestamp = data_csv.split(",")[0]
                    if not(timestamp in energy_used_network.keys()):
                        if not(timestamp in self.energy_consumed.keys()):
                            energy_used_network[timestamp] = 0
                            self.energy_consumed[timestamp] = 0
                        else:
                            energy_used_network[timestamp] = self.energy_consumed[timestamp]
                    energy_by_device = data_csv.split(",")[2]
                    energy_by_device = float(energy_by_device[:-1])
                    energy_used_network[timestamp] = energy_used_network[timestamp]  + energy_by_device
                if component == "END":
                    all_devices_energy = True
        file_energy.close()
        shutil.move(self.energy_consumed_file, "/tmp/" + str(timestamp))
        period_energy = 0
        for i_timestamp, i_energy_consumed in energy_used_network.items():
            if len(list(self.energy_consumed.keys())) == 0:
                self.energy_consumed[i_timestamp] = i_energy_consumed
                period_energy = i_energy_consumed
            else:
                # Only the energy in the last interval
                timesmtamp_keys = list(self.energy_consumed.keys())
                my_index = timesmtamp_keys.index(i_timestamp)
                previous_timestamp = timesmtamp_keys[my_index - 1]
                previous_total_energy = self.energy_consumed[previous_timestamp]
                period_energy = i_energy_consumed - previous_total_energy
                self.energy_consumed[i_timestamp] = i_energy_consumed

        return period_energy

    def get_total_energy_consumption(self):
        # Sumar todos los consumos energeticos
        reward = self.get_reward_from_NS3()

        return reward