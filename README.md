# vpngate-with-proxy
VPN GATE client for linux
* Be able to connect to open vpn servers at **http://www.vpngate.net/en/** directly or through proxy
* Auto add DNS to fix DNS leak.
* Auto filter out dead VPN servers. (updated on August 16th)
* Can execute user defined script after vpn_tunnel is established or broken.

Work on Debian and Redhat based system. 
Tested on **Ubuntu**, **Raspbian**, **Fedora**, **Bunsen**.

I will wrap SoftEther_vpn later when I have time. You are welcome to fork this repo and wrap SoftEther_vpn yourself.

**Indicator**: is optional.  

<img  align="right" src="https://s19.postimg.org/5l77q2q83/8indicator.png">

Tested on Ubuntu and is only enabled by default on Ubuntu.

For other unix os, you need to modify the `run` file and install packages below:

    sudo apt-get install gir1.2-appindicator3-0.1 gir1.2-notify-0.7 python-gobject


If you have any trouble or request about the program, 
please make a new issue at https://github.com/Dragon2fly/vpngate-with-proxy/issues



# Dependency:
* **python 2.7.x**: should already be shipped with your linux

Except *python 2.7.x*, all below dependencies should be automatically installed at first run.
* **openvpn**: ```$ sudo apt-get install openvpn```
* **python-requests**: ```$ sudo apt-get install python-requests```
* **python-urwid 1.3+**: ```$ sudo apt-get install python-urwid``` , for `tui` version (terminal user interface)
* **wmctrl**: ```$ sudo apt-get install wmctrl```, for `Indicator` of `tui` version, use for focusing window from indicator. 

# How to use:

### 0. Pre-installation
  * If your network is behind a proxy
  
  ```Shell
    $ export http_proxy="http://your_proxy:your_port"
    $ export https_proxy="http://your_proxy:your_port"
  ```
  * If you has just installed your os, please update your os for it to fetch packages list and know where to download
  other packages later.

  ```Shell
  $ sudo apt-get update && sudo apt-get upgrade
  ```

  * Please check the os clock and calendar if it is correct for openvpn **authentication** to work properly.

### 1. Installation:

  Using *git*:
  
  ```Shell
  $ sudo apt-get install git
  $ git clone https://github.com/Dragon2fly/vpngate-with-proxy.git
  ```
  
  If your network is behind a proxy:
  ```Shell
  $ sudo -E apt-get install git
  $ git clone https://github.com/Dragon2fly/vpngate-with-proxy.git
  ```
  
  You can also download [the zip file](https://github.com/Dragon2fly/vpngate-with-proxy/archive/master.zip)
  It contains the "vpngate-with-proxy" folder. Extract it into anywhere you want eg: `$HOME`.
  
  
  **user_script:**
  
  Within this folder, there should be a file `user_script.sh`. 
  This file allow you to run extra commands to fit your need. 
  You have to manually edit this file and don't change the file name.
  Commands are divided into 2 groups:
  - **up**: execute after vpn tunnel is established successfully.
  - **down**: execute after vpn tunnel is broken/terminated.

### 2. First run:
  If you have configured **system wide proxy** or proxy in firefox, it'd better to **turn** it **off**. After vpn tunnel is established,
  the programs that use system wide proxy may failed to connect to the internet using your proxy.

  Launch vpngate-with-proxy by

  ```Shell
  $ cd vpngate-with-proxy
  $ ./run [arg]
  ```
   - **arg** could be either none or **tui** or **cli**.
   - **vpnproxy_tui.py** has better UI, colorful and easier to use. Run when `arg` is none or **tui**
   - **vpnproxy_cli.py** is normal terminal application, lightweight and is aim to run on server (RaspberryPi ?). 
   Run when `arg` is **cli**

Then the program will first setup a configuration file `config.ini` by asking you for **proxy** if needed to 
connect to the Internet. After that it will show the default configuration of the program. 
Change any parameter to suit you and press **Enter** to continue. 
Next time launching this program, you won't see this configuration again. Either modify `config.ini` or check **5. Some notes**

  If no thing goes wrong, the vpn server's list will show up.

   ![](https://s19.postimg.org/tg0eofvwj/1startup.png)

### 3. Interaction:
  * Connect to a specific vpn server by typing its *index* number (eg: 3) and then Enter.
  If nothing went wrong, a `successfully` message show up.
  
    ![](https://s19.postimg.org/m3uyiwdoj/4oldandnew.png)

  * Your currently chosen server will be highlighted with `dark blue` color.
  * All connected servers before the current one is show in `dark red` color.
  * Change your desire setting by press the `F#` key corresponding to that setting. Hit that `F#` key again to discard all changes and close setting popup. Setting will only be saved when you hit `<OK>` or Enter.
    * **F2**: **Proxy**, use http proxy? address? port?
    * **F3**: **DNS**, change DNS when connecting to vpn? which dns to change to?
    * **F4**: **Country**, looking for a specific country or all that available?
    * **F5**: **Sort by**, sort these servers by what parameter?

    ![](https://s19.postimg.org/q2s61q2bn/6menu.png)

  * **Vpn command**: As you mentioned above, give an index of the server then hit Enter will open a vpn tunnel from your to that server. And there are still some more.

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
    * **Ctrl + F5**: the same as `r` or `refresh` *command*
    * **Ctrl + r** : the same as `restore` *command*
    * **Ctrl + k** : the same as `kill` *command*
    * **Ctrl + c** : if connected to vpn server, terminate vpn tunnel, turn back to normal state.
      Else, quit the program

### 4. After VPN Tunnel is established successfully:
  A successful connection doesn't mean you have access to the Internet. If you can access the Internet through selected vpn
server, that doesn't mean you are totally safe.
  1. _Check if you can access the Internet_:
    * try browse some websites. Low *score* VPN servers tend to block you out of the Internet  

  2. _Check DNS leak_:
  
   If you are serious about privacy, this is necessary. DNS server knows the web addresses that you connected to,
   unless you type IP address directly.

   To know your current DNS provider, https://www.dnsleaktest.com or https://ipleak.net

   * Turn on `DNS fix` by press `F3` before connecting to vpn server. Choose some good DNS from http://pcsupport.about.com/od/tipstricks/a/free-public-dns-servers.htm
   * Connect to any VPN server and test if your dns provider is changed.
  
  If DNS is not changed, make sure that you have turned off your system wide proxy and try again.
  While using the ethernet for vpn, connected to wifi may reset your DNS.  
  
You could also use below command in Ubuntu to see trace route:
  ```Shell
  $ mtr -rw google.com
  ```

### 5. Some notes:
  * To view or change settings before the program fetches server's list, use one of below:
  ```Shell
  $ ./run config
  ```
  ```Shell
  $ ./run cli config
  ```
  ```Shell
  $ ./run tui config
  ```
  
  * (vpnproxy_cli.py only) To view or change settings at server's list: type *Vpn command* **c** or **config** then Enter

  * **Ctrl+z**: Try not to press this combination while program is running. It will not terminate the vpn tunnel nor kill the program properly.
   Which means iptable may be left messed up, DNS won't reset to original, you may be **still in vpn**.

  * The program only shows the last log line at the bottom of terminal. In fact, there is 20 last lines of the log.
   To view these lines, you just need to extend the high of the terminal window.
   ![log](https://s19.postimg.org/a5te509xf/7loglines.png)
   The log is shown up side down so the latest information will be in the highest place

  * If your terminal looks weird after program crashed or `Ctrtl+z`, `$ reset` would help


# Troubleshoot:
  If the program is unable to fetch new server data nor connect to any vpn server, your networking is not back to normal.

  That is when `restore`, `kill` and `log on` *command* come in handy. 
  
  You will need to reset your network setting by:

  1. **kill** all openvpn processes
  2. `$ sudo service network-manager restart`

  Restart your system or reconnect to wifi or ethernet will also help.
  If it still doesn't, your proxy may be offline or `\etc\resolv.conf`'s content is incorrect.
  Ping your proxy from another computer to test. And double check `\etc\resolv.conf`
  
  If your network is behind a proxy, there is a chance that your ip will be blocked. 
  Testing if OpenVPN servers are dead or alive requires spamming many socket connection.
  Although the program has limited the number of socket connection per second, the proxy may think it is being DDoS. 
  Search in the source code for **test_interval** and increase it a little bit. 
  
  If vpn_indicator is unresponsive, kill it by:
      
      $ kill -9 `pgrep -f vpn_indicator`
      
      
  For other problems and bugs, please make an issue at https://github.com/Dragon2fly/vpngate-with-proxy/issues. 
  State clearly the OS and what steps that you have taken that lead to the bug.