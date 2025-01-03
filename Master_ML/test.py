class car:
    def __init__(self):

        self.a = 0

    def cambio(self):

        self.set_data(7)

    def set_data(self, data):
        self.a = data


coche = car()

coche.cambio()

print(str(coche.a).zfill(3))

