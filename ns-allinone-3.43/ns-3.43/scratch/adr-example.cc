/*
 * Copyright (c) 2018 University of Padova
 *
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * Author: Davide Magrin <magrinda@dei.unipd.it>
 */

/*
 * This program creates a simple network which uses an Adaptive Data Rate (ADR) algorithm to set up
 * the Spreading Factors of the devices in the Network.
 */

#include "ns3/command-line.h"
#include "ns3/config.h"
#include "ns3/core-module.h"
#include "ns3/forwarder-helper.h"
#include "ns3/gateway-lora-phy.h"
#include "ns3/hex-grid-position-allocator.h"
#include "ns3/log.h"
#include "ns3/lora-channel.h"
#include "ns3/lora-device-address-generator.h"
#include "ns3/lora-helper.h"
#include "ns3/lora-phy-helper.h"
#include "ns3/lorawan-mac-helper.h"
#include "ns3/mobility-helper.h"
#include "ns3/network-module.h"
#include "ns3/network-server-helper.h"
#include "ns3/periodic-sender-helper.h"
#include "ns3/periodic-sender.h"
#include "ns3/point-to-point-module.h"
#include "ns3/random-variable-stream.h"
#include "ns3/rectangle.h"
#include "ns3/string.h"
#include "ns3/netanim-module.h"
#include "ns3/mobility-module.h"
#include "ns3/basic-energy-source-helper.h"
#include "ns3/lora-radio-energy-model-helper.h"
#include "ns3/file-helper.h"

using namespace ns3;
using namespace lorawan;

NS_LOG_COMPONENT_DEFINE("AdrExample");

/** Record received pkts by Data Rate (DR) [index 0 -> DR5, index 5 -> DR0]. */
auto packetsSent = std::vector<int>(6, 0);
/** Record received pkts by Data Rate (DR) [index 0 -> DR5, index 5 -> DR0]. */
auto packetsReceived = std::vector<int>(6, 0);

/**
 * Record a change in the data rate setting on an end device.
 *
 * \param oldDr The previous data rate value.
 * \param newDr The updated data rate value.
 */
void
OnDataRateChange(uint8_t oldDr, uint8_t newDr)
{
    NS_LOG_DEBUG("DR" << unsigned(oldDr) << " -> DR" << unsigned(newDr));
}

/**
 * Record a change in the transmission power setting on an end device.
 *
 * \param oldTxPower The previous transmission power value.
 * \param newTxPower The updated transmission power value.
 */
void
OnTxPowerChange(double oldTxPower, double newTxPower)
{
    NS_LOG_DEBUG(oldTxPower << " dBm -> " << newTxPower << " dBm");
}

/**
 * Record the beginning of a transmission by an end device.
 *
 * \param packet A pointer to the packet sent.
 * \param senderNodeId Node id of the sender end device.
 */
void
OnTransmissionCallback(Ptr<const Packet> packet, uint32_t senderNodeId)
{
    //NS_LOG_FUNCTION(packet << senderNodeId);
    LoraTag tag;
    packet->PeekPacketTag(tag);
    //std::cout << "Time: " << Simulator::Now().GetSeconds() << " Nodo: " << unsigned(senderNodeId) << " SF:" << unsigned(tag.GetSpreadingFactor()) << std::endl;
    packetsSent.at(tag.GetSpreadingFactor() - 7)++;
}

/**
 * Record the correct reception of a packet by a gateway.
 *
 * \param packet A pointer to the packet received.
 * \param receiverNodeId Node id of the receiver gateway.
 */
void
OnPacketReceptionCallback(Ptr<const Packet> packet, uint32_t receiverNodeId)
{
    //NS_LOG_FUNCTION(packet << receiverNodeId);
    LoraTag tag;
    packet->PeekPacketTag(tag);
    //std::cout << "SF:" << unsigned(tag.GetSpreadingFactor())<< std::endl;
    if (tag.GetSpreadingFactor() > 6) {
        packetsReceived.at(tag.GetSpreadingFactor() - 7)++;
    }
}

void energyConsumed(DeviceEnergyModelContainer deviceModels, int interval)
{
    int i_node = 0;
    for (auto iter = deviceModels.Begin(); iter != deviceModels.End(); iter++)
    {
        double energyConsumed = (*iter)->GetTotalEnergyConsumption();
        std::cout << "End of simulation ("
                      << Simulator::Now().GetSeconds()
                      << "s) Total energy consumed by radio " << unsigned(i_node) << " : "  << energyConsumed << "J"<< std::endl;
        i_node++;
    }
    
    Simulator::Schedule(Seconds(interval), &energyConsumed, deviceModels, interval);    
}


int
main(int argc, char* argv[])
{
    bool verbose = false;
    bool adrEnabled = true;
    bool initializeSF = false;
    int nDevices = 2;
    int nPeriods = 5;
    int timeBetweenPackets = 1200;
    double mobileNodeProbability = 0;
    double sideLengthMeters = 50;
    int gatewayDistanceMeters = 100;
    double maxRandomLossDB = 10;
    double minSpeedMetersPerSecond = 2;
    double maxSpeedMetersPerSecond = 16;
    std::string adrType = "ns3::AdrComponent";
    int maxTrans = 3;

    CommandLine cmd(__FILE__);
    cmd.AddValue("verbose", "Whether to print output or not", verbose);
    cmd.AddValue("MultipleGwCombiningMethod", "ns3::AdrComponent::MultipleGwCombiningMethod");
    cmd.AddValue("MultiplePacketsCombiningMethod",
                 "ns3::AdrComponent::MultiplePacketsCombiningMethod");
    cmd.AddValue("HistoryRange", "ns3::AdrComponent::HistoryRange");
    cmd.AddValue("MType", "ns3::EndDeviceLorawanMac::MType");
    cmd.AddValue("EDDRAdaptation", "ns3::EndDeviceLorawanMac::EnableEDDataRateAdaptation", adrEnabled);
    cmd.AddValue("ChangeTransmissionPower", "ns3::AdrComponent::ChangeTransmissionPower");
    cmd.AddValue("AdrEnabled", "Whether to enable Adaptive Data Rate (ADR)", adrEnabled);
    cmd.AddValue("nDevices", "Number of devices to simulate", nDevices);
    cmd.AddValue("PeriodsToSimulate", "Number of periods (20m) to simulate", nPeriods);
    cmd.AddValue("MobileNodeProbability",
                 "Probability of a node being a mobile node",
                 mobileNodeProbability);
    cmd.AddValue("sideLength",
                 "Length (m) of the side of the rectangle nodes will be placed in",
                 sideLengthMeters);
    cmd.AddValue("maxRandomLoss",
                 "Maximum amount (dB) of the random loss component",
                 maxRandomLossDB);
    cmd.AddValue("gatewayDistance", "Distance (m) between gateways", gatewayDistanceMeters);
    cmd.AddValue("initializeSF", "Whether to initialize the SFs", initializeSF);
    cmd.AddValue("MinSpeed", "Minimum speed (m/s) for mobile devices", minSpeedMetersPerSecond);
    cmd.AddValue("MaxSpeed", "Maximum speed (m/s) for mobile devices", maxSpeedMetersPerSecond);
    cmd.AddValue("MaxTransmissions", "ns3::EndDeviceLorawanMac::MaxTransmissions");
    cmd.Parse(argc, argv);

    int gatewayRings = 2 + (std::sqrt(2) * sideLengthMeters) / (gatewayDistanceMeters);
    int nGateways = 3 * gatewayRings * gatewayRings - 3 * gatewayRings + 1;

    // Logging
    //////////

    LogComponentEnable("AdrExample", LOG_LEVEL_ALL);
    LogComponentEnable ("LoraPacketTracker", LOG_LEVEL_ALL);
    // LogComponentEnable ("NetworkServer", LOG_LEVEL_ALL);
    // LogComponentEnable ("NetworkController", LOG_LEVEL_ALL);
    // LogComponentEnable ("NetworkScheduler", LOG_LEVEL_ALL);
    // LogComponentEnable ("NetworkStatus", LOG_LEVEL_ALL);
    // LogComponentEnable ("EndDeviceStatus", LOG_LEVEL_ALL);
    LogComponentEnable("AdrComponent", LOG_LEVEL_ALL);
    // LogComponentEnable("ClassAEndDeviceLorawanMac", LOG_LEVEL_ALL);
    // LogComponentEnable ("LogicalLoraChannelHelper", LOG_LEVEL_ALL);
    // LogComponentEnable ("MacCommand", LOG_LEVEL_ALL);
    // LogComponentEnable ("AdrExploraSf", LOG_LEVEL_ALL);
    // LogComponentEnable ("AdrExploraAt", LOG_LEVEL_ALL);
     LogComponentEnable ("EndDeviceLorawanMac", LOG_LEVEL_ALL);
    //LogComponentEnableAll(LOG_PREFIX_FUNC);
    LogComponentEnableAll(LOG_PREFIX_NODE);
    LogComponentEnableAll(LOG_PREFIX_TIME);

    // Set the end devices to allow data rate control (i.e. adaptive data rate) from the network
    // server
    Config::SetDefault("ns3::EndDeviceLorawanMac::DRControl", BooleanValue(true));

    // Create a simple wireless channel
    ///////////////////////////////////

    Ptr<LogDistancePropagationLossModel> loss = CreateObject<LogDistancePropagationLossModel>();
    loss->SetPathLossExponent(3.76);
    loss->SetReference(1, 7.7);

    Ptr<UniformRandomVariable> x = CreateObject<UniformRandomVariable>();
    x->SetAttribute("Min", DoubleValue(0.0));
    x->SetAttribute("Max", DoubleValue(maxRandomLossDB));

    Ptr<RandomPropagationLossModel> randomLoss = CreateObject<RandomPropagationLossModel>();
    randomLoss->SetAttribute("Variable", PointerValue(x));

    loss->SetNext(randomLoss);

    Ptr<PropagationDelayModel> delay = CreateObject<ConstantSpeedPropagationDelayModel>();

    Ptr<LoraChannel> channel = CreateObject<LoraChannel>(loss, delay);

    // Helpers
    //////////

    // End device mobility
    MobilityHelper mobilityEd;
    MobilityHelper mobilityGw;
    mobilityEd.SetPositionAllocator("ns3::RandomRectanglePositionAllocator",
                                    "X",
                                    PointerValue(CreateObjectWithAttributes<UniformRandomVariable>(
                                        "Min",
                                        DoubleValue(-sideLengthMeters),
                                        "Max",
                                        DoubleValue(sideLengthMeters))),
                                    "Y",
                                    PointerValue(CreateObjectWithAttributes<UniformRandomVariable>(
                                        "Min",
                                        DoubleValue(-sideLengthMeters),
                                        "Max",
                                        DoubleValue(sideLengthMeters))));

    // // Gateway mobility
    // Ptr<ListPositionAllocator> positionAllocGw = CreateObject<ListPositionAllocator> ();
    // positionAllocGw->Add (Vector (0.0, 0.0, 15.0));
    // positionAllocGw->Add (Vector (-5000.0, -5000.0, 15.0));
    // positionAllocGw->Add (Vector (-5000.0, 5000.0, 15.0));
    // positionAllocGw->Add (Vector (5000.0, -5000.0, 15.0));
    // positionAllocGw->Add (Vector (5000.0, 5000.0, 15.0));
    // mobilityGw.SetPositionAllocator (positionAllocGw);
    // mobilityGw.SetMobilityModel ("ns3::ConstantPositionMobilityModel");
    Ptr<HexGridPositionAllocator> hexAllocator =
        CreateObject<HexGridPositionAllocator>(gatewayDistanceMeters / 2);
    mobilityGw.SetPositionAllocator(hexAllocator);
    mobilityGw.SetMobilityModel("ns3::ConstantPositionMobilityModel");

    // Create the LoraPhyHelper
    LoraPhyHelper phyHelper = LoraPhyHelper();
    phyHelper.SetChannel(channel);

    // Create the LorawanMacHelper
    LorawanMacHelper macHelper = LorawanMacHelper();

    // Create the LoraHelper
    LoraHelper helper = LoraHelper();
    helper.EnablePacketTracking();

    ////////////////
    // Create gateways //
    ////////////////

    NodeContainer gateways;
    gateways.Create(nGateways);
    mobilityGw.Install(gateways);
    std::cout << "Informacion de las GW" << std::endl;
    std::cout << "Numero de GWs: " << nGateways << std::endl;

    // Create the LoraNetDevices of the gateways
    phyHelper.SetDeviceType(LoraPhyHelper::GW);
    macHelper.SetDeviceType(LorawanMacHelper::GW);
    helper.Install(phyHelper, macHelper, gateways);

    // Create end devices
    /////////////

    NodeContainer endDevices;
    endDevices.Create(nDevices);

    // Install mobility model on fixed nodes
    mobilityEd.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    int fixedPositionNodes = double(nDevices) * (1 - mobileNodeProbability);
    std::cout << "Informacion de los ED\n";
    std::cout << "Numero de ED con posiciones fijas: " << nDevices << "\n";
    for (int i = 0; i < fixedPositionNodes; ++i)
    {
        mobilityEd.Install(endDevices.Get(i));
        Ptr<ConstantPositionMobilityModel> mobility = endDevices.Get(i)->GetObject<ConstantPositionMobilityModel>();
        Vector pos = mobility->GetPosition();
        std::cout << "Nodo " << endDevices.Get(i)->GetId() << " - Posición: (" << pos.x << ", " << pos.y << ")" << std::endl;

    }
    // Install mobility model on mobile nodes
    mobilityEd.SetMobilityModel(
        "ns3::RandomWalk2dMobilityModel",
        "Bounds",
        RectangleValue(
            Rectangle(-sideLengthMeters, sideLengthMeters, -sideLengthMeters, sideLengthMeters)),
        "Distance",
        DoubleValue(1000),
        "Speed",
        PointerValue(CreateObjectWithAttributes<UniformRandomVariable>(
            "Min",
            DoubleValue(minSpeedMetersPerSecond),
            "Max",
            DoubleValue(maxSpeedMetersPerSecond))));
    for (int i = fixedPositionNodes; i < (int)endDevices.GetN(); ++i)
    {
        mobilityEd.Install(endDevices.Get(i));
    }

    // Create a LoraDeviceAddressGenerator
    uint8_t nwkId = 54;
    uint32_t nwkAddr = 1864;
    Ptr<LoraDeviceAddressGenerator> addrGen =
        CreateObject<LoraDeviceAddressGenerator>(nwkId, nwkAddr);

    // Create the LoraNetDevices of the end devices
    phyHelper.SetDeviceType(LoraPhyHelper::ED);
    macHelper.SetDeviceType(LorawanMacHelper::ED_A);
    macHelper.SetAddressGenerator(addrGen);
    macHelper.SetRegion(LorawanMacHelper::EU);
    helper.Install(phyHelper, macHelper, endDevices);

    // Install applications in end devices
    int appPeriodSeconds = timeBetweenPackets; // One packet every 20 minutes
    PeriodicSenderHelper appHelper = PeriodicSenderHelper();
    appHelper.SetPeriod(Seconds(appPeriodSeconds));
    ApplicationContainer appContainer = appHelper.Install(endDevices);

    // Do not set spreading factors up: we will wait for the network server to do this
    if (initializeSF)
    {
        LorawanMacHelper::SetSpreadingFactorsUp(endDevices, gateways, channel);
    }

    ////////////
    // Create network server
    ////////////

    Ptr<Node> networkServer = CreateObject<Node>();

    // PointToPoint links between gateways and server
    PointToPointHelper p2p;
    p2p.SetDeviceAttribute("DataRate", StringValue("5Mbps"));
    p2p.SetChannelAttribute("Delay", StringValue("2ms"));
    // Store network server app registration details for later
    P2PGwRegistration_t gwRegistration;
    for (auto gw = gateways.Begin(); gw != gateways.End(); ++gw)
    {
        auto container = p2p.Install(networkServer, *gw);
        auto serverP2PNetDev = DynamicCast<PointToPointNetDevice>(container.Get(0));
        gwRegistration.emplace_back(serverP2PNetDev, *gw);
    }

    // Install the NetworkServer application on the network server
    NetworkServerHelper networkServerHelper;
    networkServerHelper.EnableAdr(adrEnabled);
    networkServerHelper.SetAdr(adrType);
    networkServerHelper.SetGatewaysP2P(gwRegistration);
    networkServerHelper.SetEndDevices(endDevices);
    networkServerHelper.Install(networkServer);

    // Install the Forwarder application on the gateways
    ForwarderHelper forwarderHelper;
    forwarderHelper.Install(gateways);

    // Connect our traces
    Config::ConnectWithoutContext(
        "/NodeList/*/DeviceList/0/$ns3::LoraNetDevice/Mac/$ns3::EndDeviceLorawanMac/TxPower",
        MakeCallback(&OnTxPowerChange));
    Config::ConnectWithoutContext(
        "/NodeList/*/DeviceList/0/$ns3::LoraNetDevice/Mac/$ns3::EndDeviceLorawanMac/DataRate",
        MakeCallback(&OnDataRateChange));

    // Activate printing of end device MAC parameters
    Time stateSamplePeriod = Seconds(timeBetweenPackets);
    helper.EnablePeriodicDeviceStatusPrinting(endDevices,
                                              gateways,
                                              "nodeData.txt",
                                              stateSamplePeriod);
    helper.EnablePeriodicPhyPerformancePrinting(gateways, "phyPerformance.txt", stateSamplePeriod);
    helper.EnablePeriodicGlobalPerformancePrinting("globalPerformance.txt", stateSamplePeriod);

    LoraPacketTracker& tracker = helper.GetPacketTracker();

    // Start simulation
    Time simulationTime = Seconds(timeBetweenPackets * nPeriods);
    Simulator::Stop(simulationTime);

    Simulator::Run();
    Simulator::Destroy();

    std::cout << tracker.CountMacPacketsGlobally(Seconds(timeBetweenPackets * (nPeriods - 2)),
                                                 Seconds(timeBetweenPackets * (nPeriods - 1)))
              << std::endl;

    return 0;
}
