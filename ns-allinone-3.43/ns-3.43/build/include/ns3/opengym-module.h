#ifdef NS3_MODULE_COMPILATION 
    error "Do not include ns3 module aggregator headers from other modules these are meant only for end user scripts." 
#endif 
#ifndef NS3_MODULE_OPENGYM
    // Module headers: 
    #include <ns3/opengym-helper.h>
    #include <ns3/container.h>
    #include <ns3/opengym_env.h>
    #include <ns3/opengym_interface.h>
    #include <ns3/spaces.h>
#endif 