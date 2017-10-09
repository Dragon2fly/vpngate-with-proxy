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
if you don't have python3.6 then
if `sudo apt-get install python3.6` didn't work on your system, then

    sudo add-apt-repository ppa:jonathonf/python-3.6
    sudo apt-get update
    sudo apt-get install python3.6

This branch is still in develop, clone it as below:

    git clone --branch vpnwp_v2 https://github.com/Dragon2fly/vpngate-with-proxy.git vpnwp_v2

then execute it as simple as:

    $ cd vpnwp_v2
    $ ./run

As usually, all dependencies should be automatically installed.

The program is divided into 2 parts:
* __vpn_manager__ : run in the background like a service, you can make it to run at computer start up and
because of automation, no need to do anything else.
* __UI_client__: talk with the manager through tcp/ip, no need sudo. Make an alias for it is quite handy.
You could run the UI directly by `python3 UI.py $HOME`

### Argument for `./run [arg]`
* stop: kill the vpn_manager process
* log: show real time log
* restart: restart the vpn_manager process

You could add your own command by tweaking the `run` file and the `UI.py` file.

### Currently possible
__vpn_command__ are (__group__: commands):
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

### Favorite servers
* when you are connected to a vpn server, save it to _favorite_ by
__add favorite__ command without any extra argument.

* To add your own .ovpn files, simple put these files to `$HOME/.config/vpngate-with-proxy/favorites`
    then one of the following
     * `python3 base.py`: ask your permission to add new .ovpn one by one and its description
     * vpn_command: __add local__ command without any argument
     * Editing the file $HOME/.config/vpngate-with-proxy/favorites/database.json also works.


* To see the list of saved server, use __mode favorite__ command. (because the UI switch faster than
the manager so you will need to wait 1 sec and __list__ to show the list. Fix this later.)

* To remove a server out of this list: __del favorite__ index_num

* To check for alive servers in this list: __fav alive__
