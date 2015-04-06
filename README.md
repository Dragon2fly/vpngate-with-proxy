# vpngate-with-proxy
vpngate client for linux, be able to connect to open_vpn server through proxy
by using python script. Auto add DNS to fix DNS leak.

#Dependency:
* **openvpn**: ```$ sudo apt-get install openvpn```
* **python 2.7.x**

#How to use:
###1. Installation:

  Using *git*:
  ```
     $ sudo apt-get install git
     $ git clone https://github.com/Dragon2fly/vpngate-with-proxy.git
  ```
  
  **OR**
  
  Download: vpnproxy.py, config.py, update-resolv-conf.sh
  Put 3 files into the folder named eg. "vpngate-with-proxy"


###2. First run:
  ```
  $ cd vpngate-with-proxy
  ~/vpngate-with-proxy$ ./vpnproxy.py
  ```

  Then program will first setup a configuration by asking you for your *proxy* and how to *sort* the result          descending (by **speed** or **ping** or **up time** or **score**)...

  With setting that has default option, just Enter to use that default option 

  If no thing goes wrong, the vpn server's list will show up
 
###3. Next run:
  * Setting in config.ini will be loaded automatically from the second time.
  * To view or change settings before the program fetches server's list:
  ```
  ~/vpngate-with-proxy$ ./vpnproxy.py config
  ```
  
  * To view or change settings at server's list: type **c** or **config**
  * For more commands, read **Commands**
  

#Commands:
* **c**, **config** : to view current settings about proxy, sorting parameter, country filter ...
* **number** : in *settings screen*, change each setting by enter its correspondent number. In *server's list*, choose the server you want to connect by its index
              
* **q**, **exit**: in *server's list*, quit the program
* **r**, **refresh** : in *server's list*, fetch new server's data from vpngate.net
* **Ctrl+c** : while openvpn is connecting, terminate current vpn connection and return to server's list

#Note:
* **Ctrl+z**: while openvpn is connecting will kill the program immediately and leave the vpn connection intact.
             If the server you are connecting to die, you won't be able to reconnect to the Internet.
             Restart your computer or try  **sudo iptables -F** to fix
