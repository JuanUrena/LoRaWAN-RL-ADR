# This program prints Hello, world!
import sys
import pandas as pd
from rich.jupyter import display

print('Hello, world!')



def process_new_end_device(end_devices, data):
    data_splitted = data.split(",")
    print(data_splitted)
    end_devices["node_ID"].append(data_splitted[0])
    end_devices["pos_x"].append(data_splitted[1])
    end_devices["pos_y"].append(data_splitted[2])
    end_devices["mac"].append(data_splitted[3])

    return end_devices



with open("/tmp/pipe2python", "r") as f_in:
    data = [1,2,3]
    end_devices = {
        "node_ID": [],
        "pos_x": [],
        "pos_y": [],
        "mac": []
    }
    while True:
        line = f_in.readline()

        print(line)
        if len(line):
            line = line[:-1]
            line_splitted = line.split(":")

            component = line_splitted[0]
            data_csv = line_splitted[1]

            if component == "ED":
                # Info about ED
                end_devices = process_new_end_device(end_devices, data_csv)
            elif component == "ENG":
                # Energia -> Reward
                print(end_devices)
                df = pd.DataFrame(end_devices)
                df.set_index('node_ID', inplace=True)

                print(df)
                sys.exit()
            elif component == "ADR":
                # Request of parameters
                continue


            with open("/tmp/pype2NS3", "w") as f_out:
                f_out.write("HI!")
                f_out.close()
                print("HI")






        

