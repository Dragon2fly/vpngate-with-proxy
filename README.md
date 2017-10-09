# vpngate-with-proxy
VPN GATE client for linux
* Be able to connect to open vpn servers at **http://www.vpngate.net/en/** directly or through proxy
* Auto add DNS to fix DNS leak.
* Auto filter out dead VPN servers.
* Can execute user defined script after vpn_tunnel is established or broken.
* Can disable IPv6 during VPN season.

If you have any trouble or request about the program, 
please make a new issue at https://github.com/Dragon2fly/vpngate-with-proxy/issues


Updated to __python 3.6+__
Allow automation so that you are almost always stay in a vpn connection

This branch is still in develop, clone it as below:

    git clone --branch vpnwp_v2 https://github.com/Dragon2fly/vpngate-with-proxy.git vpnwp_v2

then execute it as simple as:

    $ cd vpnwp_v2
    $ ./run

As usually, all dependencies should be automatically installed.

Currently possible vpn_commands are (__group__: commands):
 * __quit__: q | exit | quit
 * __refresh__: r | refresh
 * __config__: c | config
 * __next page__: . | >
 * __prev page__: , | <
 * __next vpn__: n | next
 * __prev vpn__: p | prev
 * __log__: log
 * __status__: status
 * __stop__: stop
 * __auto on__: auto on | aon
 * __auto off__: auto off | aoff
 * __list__: list | ls
 * __mode main__: mode main
 * __mode favorite__: mode fav | mode favorite
 * __add favorite__: save | add fav | add favorite
 * __del favorite__: remove | del | delete
 * __add local__: add local
 * __fav alive__: alive | check | check alive