# vpngate-with-proxy
vpngate client for linux, be able to connect to open_vpn server through proxy
by using python script. Auto add DNS to fix DNS leak.

#How to use:
First time **$./vpnproxy.py** will ask you your *proxy* and how to *sort* the result descending (by **speed** or 
**ping** or **up time** or **score**).

Then it saves your config into config.ini and load it automatically from the second time. 

#Commands:
* **config** : to view current settings about proxy, sorting parameter, country filter ...
* **number** : in *settings screen*, change setting by enter its correspondent number
              in server's list, choose the server you want to connect by its index
              
* **q**,**exit**: in server's list, quit the program
* **r**,**refresh** : in server's list, fetch new server's data from vpngate.net
* **Ctrl+c** : while openvpn is connecting, terminate current vpn connection and return to server's list

#Note:
* **Ctrl+z**: while openvpn is connecting will kill the program immediately and leave the vpn connection intact.
             If the server you are connecting to die, you won't be able to reconnect to the Internet.
             Restart your computer or try  **sudo iptables -F** to fix