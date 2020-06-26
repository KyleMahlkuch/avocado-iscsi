Tests the network driver and interface with 'ethtool' command.
Different parameters are specified in Parameters section of multiplexer file.
Interfaces are specified in Interfaces section of multiplexer file.

This test needs to be run as root.

Requirements:
-------------
For all specified interfaces, configuration file for that interface needs
to be updated, so that setting 'up / down <interface>' configures the interface.

Input Needed (in multiplexer file):
-----------------------------------
Interfaces     -   Specify the interface for which the test needs to be run.
arg            -   Specify the argument that needs to be tested.
action_elapse  -   Specify action elapse for those arguments that need it.
host-IP        -   Specify host-IP for ip configuration.
netmask        -   specify netmask for ip configuration.

Input example:
------
interface: enP24p1s0f0
peer_ip: 10.0.0.200
host_ip: 10.0.0.50
netmask: 255.255.255.0
args: !mux
    PrivateFlag:
        privflag_test: True
    Driver:
        arg: -i
    Autonegotiation:
        arg: -r
    PauseParameter:
        arg: -a
    Coalescing:
        arg: -c
    RegisterDump:
        arg: -d
    EEPROMDump:
       arg: -e
    RingParameter:
        arg: -g
    ShowOffloadProtocolFeature:
        arg: -k
    AdapterInitiate:
        arg: -p
        action_elapse: 3
    Statistics:
        arg: -S
    SelfTest:
        arg: -t
    Show-permaddr:
        arg: -P
    Get-dump:
        arg: -w
    Show-time-stamping:
        arg: -T
