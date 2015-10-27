# vpngate-with-proxy
VPN GATE client for linux, be able to connect to open_vpn server through proxy
by using python script. Auto add DNS to fix DNS leak.
Work on debian based system. Tested on Ubuntu and Raspbian.

I will wrap SSL_vpn later when I have time, or you're welcomed to fork this and do it yourself.

![](http://s19.postimg.org/580s2qyo3/2connect_success.png)

# Dependency:
* **openvpn**: ```$ sudo apt-get install openvpn```
* **resolvconf**: ```$ sudo apt-get install resolvconf```   Only if you use the version in 'old' directory
* **python 2.7.x**: should already be shipped with your linux
* **python-requests**: ```$ sudo apt-get install python-requests```
* **python-urwid**: ```$ sudo apt-get install python-urwid```Only if you use `tui` version (terminal user interface)

Except *python 2.7.x*, all other dependencies should be automatically installed at first run.

# How to use:

### 0. Pre-installation
  * If you has just installed your os, please update your os for it to fetch packages list and know where to download
  other packages later.

  ```Shell
  $ sudo apt-get update && sudo apt-get upgrade
  ```
  If your network is behind a proxy
  ```Shell
    $ export http_proxy="http://your_proxy:your_port"
    $ export https_proxy="http://your_proxy:your_port"
    $ sudo -E apt-get update && sudo apt-get upgrade
  ```

  * Please check the os clock and calendar is correct for openvpn authentication works properly.

### 1. Installation:

  Using *git*:
  ```Shell
  $ sudo apt-get install git
  $ git clone https://github.com/Dragon2fly/vpngate-with-proxy.git
  ```
  
  **OR**
  
  Download: https://github.com/Dragon2fly/vpngate-with-proxy/archive/master.zip
  It contains the "vpngate-with-proxy" folder. Extract it into anywhere you want eg: `$HOME`.

  **If your network is behind a proxy**
  ```Shell
    $ export http_proxy="http://your_proxy:your_port"
    $ export https_proxy="http://your_proxy:your_port"
    $ sudo -E apt-get install git
    $ git clone https://github.com/Dragon2fly/vpngate-with-proxy.git
  ```

### 2. First run:
  If you have configured system wide proxy, it'd better to turn it off. After vpn tunnel is established,
  the programs that use system wide proxy may failed to connect to the internet using your proxy.

  Launch vpngate-with-proxy by

  ```Shell
  $ cd vpngate-with-proxy
  ~/vpngate-with-proxy$ ./vpnproxy_tui.py
  ```

  which will launch the terminal user interface version. If you don't want complicated, you can use **vpnproxy_cli.py**
  instead.

  Then the program will first setup a configuration file `config.ini` by asking you for
   - Do you need **proxy** to connect to the Internet
   - How to *sort* the result descending (by **speed** or **ping** or **score**) or ascending  ()**up time**)
   - Filter the result by what **country**
   - Do you want to fix dns leak, which **dns** you want to use

  With setting that has **default** option, you can just press Enter to choose it.

  If no thing goes wrong, the vpn server's list will show up.

  ![](http://s19.postimg.org/qgegk6d4z/1startup.png)

### 3. Interaction:
  * Connect to a specific vpn server by typing its *index* number (eg: 11) and then Enter.
  If nothing went wrong, a `successfully` message show up.
  ![](http://s19.postimg.org/603g1y2v7/4oldandnew.png)

  * Your currently chosen server will be highlighted with `dark blue` color.
  * All connected servers before the current one is show in `dark red` color.
  * Change your desire setting by press the `F#` key corresponding to that setting. Hit that `F#` key again to discard
  all changes and close setting popup. Setting will only be saved when you hit `<OK>` or Enter.
    * **F2**: **Proxy**, use http proxy? address? port?
    * **F3**: **DNS**, change DNS when connecting to vpn? which dns to change to?
    * **F4**: **Country**, looking for a specific country or all that available?
    * **F5**: **Sort by**, sort these servers by what parameter?

   ![](http://s19.postimg.org/xtyfwvmkj/6menu.png)

  * **Vpn command**: As you mentioned above, give an index of the server then hit Enter
  will open a vpn tunnel from your to that server. And there are still some more.
    * **r**, **refresh**: fetch new server's data from vpngate.net or mirrors
    * **restore**: will restore your system DNS back to original one
    * **kill**: send SIGTERM to all `openvpn` processes
    * **q**: terminate vpn tunnel, then quit the program
    * **log**: check if current season is logged or not. Log file is `vpn.log` and is in the same folder with this program. Every time you start the program, log file is rewritten (old content will be lost) if `log` is turned on.
      * **log on**: turn on logging
      * **log off**: turn off logging

  * Other keys and combinations:
    * **Up, Down, PgUp, PgDown**: scroll the server list
    * **F10**      : toggle logging on/off
    * **Esc**      : clear the text in any input form (*vpn command*, *Proxy*, *Country*)
    * **Ctrl + F5**: the same as *command* `r` or `refresh`
    * **Ctrl + r** : the same as *command* `restore`
    * **Ctrl + k** : the same as *command* `kill`
    * **Ctrl + c** : if connected to vpn server, terminate vpn tunnel, turn back to normal state.
      Else, quit the program

### 4. After VPN Tunnel is established successfully:
  A successful connection doesn't mean you have access to the Internet. If you can access the Internet through selected vpn
server, that doesn't mean you are totally safe.
  1. Check if you can access the Internet:
  * try browse some websites, if they are loaded, that's the good sign.
  * or type `r` then Enter to see if it can fetch the new server list. This time, it will fetch data directly through vpn
  and not using the configured proxy. If the server list is *refreshed* almost instantly, that's the good sign.

  If there is no good sign, choose another server.

  2. Check DNS leak:
  If you are serious about privacy, this is necessary. DNS server knows the web addresses that you connected to,
  unless you type IP address directly.
  * Turn on `DNS fix` by press `F3` before connecting to vpn server.
  Choose some good DNS from http://pcsupport.about.com/od/tipstricks/a/free-public-dns-servers.htm
  * Test if your dns provider is different from your local: https://www.dnsleaktest.com or https://ipleak.net

   If DNS is not changed, something when wrong! You should make an issue about this.

  * To view or change settings before the program fetches server's list:
  ```Shell
  ~/vpngate-with-proxy$ ./vpnproxy_tui.py config
  ```
  
  * To view or change settings at server's list: type **c** or **config** then Enter
  * For more commands, read **Commands**
  

# Commands:
* **c**, **config** : to view current settings about proxy, sorting parameter, country filter ...
* **number** : in *settings screen*, change each setting by enter its correspondent number. In *server's list*, choose the server you want to connect by its index
              
* **q**, **exit**: in *server's list*, quit the program
* **r**, **refresh** : in *server's list*, fetch new server's data from vpngate.net
* **Ctrl+c** : while openvpn is connecting, terminate current vpn connection and return to server's list

# Note:
* **Ctrl+z**: while openvpn is connecting will kill the program immediately and leave the vpn connection intact.
             If the server you are connecting to die, you won't be able to reconnect to the Internet.
             Restart your computer or try  **sudo iptables -F** to fix
