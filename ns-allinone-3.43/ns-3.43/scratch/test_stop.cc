#include "ns3/core-module.h"
#include <fstream>
#include <thread>
#include <iostream>

using namespace ns3;

// Ruta al archivo que controlará la reanudación
const std::string controlFile = "/tmp/start_signal.txt";

// Función para verificar si el archivo contiene la palabra "start"
bool CheckStartFile() {
    std::ifstream file(controlFile);
    if (!file.is_open()) {
        return false; // Si no se puede abrir el archivo, asumimos que no está listo
    }
    std::string line;
    std::getline(file, line); // Leer la primera línea
    return line == "start";   // Devuelve true si el contenido es "start"
}

// Función para esperar activamente hasta que el archivo contenga "start"
void WaitForStartSignal() {
    std::cout << "Esperando señal para reanudar la simulación..." << std::endl;

    // Esperar activamente hasta que el archivo contenga la palabra "start"
    while (!CheckStartFile()) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100)); // Espera activa
    }

    std::cout << "Señal recibida: Reanudando la simulación." << std::endl;
}

// Función para escribir el tiempo de simulación cada segundo
void PrintSimulationTime() {
    double currentTime = Simulator::Now().GetSeconds();
    std::cout << "Tiempo simulado: " << currentTime << "s" << std::endl;

    // Pausar la simulación en el tiempo simulado 5.0
    if (currentTime == 5.0) {
        Simulator::Stop();        // Pausa la simulación
        WaitForStartSignal();     // Espera hasta que el archivo contenga "start"
        Simulator::Run();         // Reanuda la simulación
    }

    // Programar el siguiente evento hasta los 10 segundos
    if (currentTime < 10.0) {
        Simulator::Schedule(Seconds(1.0), &PrintSimulationTime);
    }
}

int main() {
    // Programar el primer evento
    Simulator::Schedule(Seconds(1.0), &PrintSimulationTime);

    // Ejecutar la simulación
    Simulator::Run();
    Simulator::Destroy();

    std::cout << "Simulación finalizada." << std::endl;

    return 0;
}
