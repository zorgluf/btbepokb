# btbepokb

A bluetooth keyboard emulator and bepo to azerty keymap translator for Debian-based linux.

Why ? Because sometime you cannot install Bepo drivers or run external software on some computers. 

The bluetooth keyboard emulator part is a slight adaptation from the great work of "keef" avalaible at http://yetanotherpointlesstechblog.blogspot.com/2016/04/emulating-bluetooth-keyboard-with.html.

This program was tested on a raspberry pi 0 running raspbian buster. Should work on other raspberry or other debian-based devices with bluetooth adapter. You need to plug a real physical keyboard on the raspberry. It was mainly designed to be used on a windows computer, but it should work on other OSs too. 

## How it works

The bebo to azerty keymap translator works with the following logic :
* When a key is stroke on the keyboard, we use the bepo keymap to identify the character chosen by the user. This character is mapped to the corresponding keyboard scancodes on the azerty table and these scancodes are sent over the virtual bluetooth keyboard.
* If the character doesn't match any existing on an azerty keyboard (É, È, À,...), we try to type it using the windows "alt-combo" tricks (alt + win char code). Can be disabled in file kb_client.py.
* Ctrl and Meta shortcut are also translated from Bepo to Azerty. Can be disabled in file kb_client.py.

### How to install

On a rapsberry running buster, as user pi and in working directory /home/pi :

* Edit file */etc/systemd/system/bluetooth.target.wants/bluetooth.service* and replace line :
```ExecStart=/usr/lib/bluetooth/bluetoothd```
by :
```ExecStart=/usr/lib/bluetooth/bluetoothd -p time```
* Execute the following commands :
```git clone https://github.com/zorgluf/btbepokb.git
sudo cp btbepokb/systemd/* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable btkeyboard.service
sudo systemctl enable kbclient.service
sudo systemctl restart bluetooth.service
sudo systemctl start btkeyboard.service
sudo systemctl start kbclient.service
```
* It might be useful to disable the Ctrl+Alt+Del sequence on your raspberry to prevent reboot when trying to log in windows :
```sudo systemctl mask ctrl-alt-del.target
sudo systemctl daemon-reload
```
* Plug a keyboard on your Rasp, and you are ready !


## How to use

1. The bluetooth keyboard device can bind up to 4 bluetooth hosts. To switch between host, press Ctrl+Fn (n from 1 to 4) twice within a second.
2. To clear a host, press twice Ctrl+F12 within a second. It will clear the actual "slot" and switch to bluetooth pairing mode.
3. When no host is yet recorded on a slot, the bluetooth device enter in pairing mode. 



## What to improve

* Global efficiency of the software. Many ways to improve, but the actual bad performance doesn't impact the user experience... so far.
* Allow other keymaps to translate from/to. Should be an easy implementation as long as you have the windows klc keymap definition (a lot avalaible at http://kbdlayout.info/).
* My English level... hope the explanations are understandabled.
