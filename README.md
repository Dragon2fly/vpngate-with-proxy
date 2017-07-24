# vpngate-with-proxy
VPN GATE client for linux
* Be able to connect to open vpn servers at **http://www.vpngate.net/en/** directly or through proxy
* Auto add DNS to fix DNS leak.
* Auto filter out dead VPN servers. (updated on August 16th)
* Can execute user defined script after vpn_tunnel is established or broken.

If you have any trouble or request about the program, 
please make a new issue at https://github.com/Dragon2fly/vpngate-with-proxy/issues


Updated to __python 3.5+__
Allow automation so that you are almost always stay in a vpn connection

This branch is still in develop, check it out as below:

    git clone --branch vpnwp_v2 https://github.com/Dragon2fly/vpngate-with-proxy.git vpnwp_v2

then execute it as simple as:

    $ cd vpnwp_v2
    $ ./run

As usually, all dependencies should be automatically installed.

Currently possible commands are (__group__: commands):
 * __quit__: q | exit | quit
 * __refresh__: r | refresh
 * __config__: c | config
 * __next page__: n | next | . | >
 * __prev page__: p | previous | , | , <
 * __log__: log
 * __status__: status
 * __stop__: stop
 * __auto on__: auto on | aon
 * __auto off__: auto off | aoff
 * __list__: list