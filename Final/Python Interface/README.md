# Python Interface

We used a computer with Bluetooth and Linux along with an Xbox controller to control the robot. Plug in the controller to the Linux machine and run the user interface with `python3 ble.py`. 

## Notes
`viewer.py` is used to gather the image buffer from the ESP32. Make sure to have it in the same directory as `ble.py`

The following libraries may need to be installed: 

````bash
pip3 install asyncio bleak pygame
````