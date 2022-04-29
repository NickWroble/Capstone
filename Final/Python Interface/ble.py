import asyncio
#from asyncio.subprocess import PIPE
from signal import signal
import bleak #BLE client 
import subprocess
import sys
import os
import signal
import math
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide" #Shut up!!!
import pygame
import threading

stop_threads = False
EXIT_COMMAND = "EXIT"
DEADZONE_RADIUS = 0.5 #Radius of the deadzone at the center of the left joystick
PICTURE_BUTTON = 2 #X button on Xbox One
EXIT_BUTTON = 1 #B button on Xbox One
AUTO_BUTTON = 3 #A button on Xbox One
DISCOVER = False #uncomment this out if you're unsure of your device name
AUTO_COMMAND = "Auto"


device_name = "Helios1" #Change this to your board's name
write_characteristic = "12345678-1234-5678-1234-56789ABCDEF3"

ble_q = []

def get_joy_direction(x, y): #https://stackoverflow.com/questions/8958010/given-an-objects-coordinates-how-do-i-determine-on-which-quadrant-of-a-rotated
    #return string of the direction of the controller. The first if statement accounts for a deadzone in the center of the controller
    dir = ""
    if math.sqrt(x**2  + y**2) < DEADZONE_RADIUS:
        dir = "Stop"
    elif y > x and y < -x:
        dir = "Left"
    elif y < x and y < -x:
        dir = "Go"
    elif y < x and y > -x:
        dir = "Right"
    elif y > x and y > -x:
        dir = "Reverse"
    return dir

def controller_handler(): #push commands to the ble queue based off the Xbox controller inputs
    direction = None
    prev_direction = ""
    button = None
    prev_button = ""
    pygame.display.init()
    pygame.joystick.init()
    controller = pygame.joystick.Joystick(0)
    controller.init()
    global stop_threads
    while not stop_threads:
        pygame.event.get()
        if controller.get_button(EXIT_BUTTON):
            ble_q.append(EXIT_COMMAND)
            stop_threads = True
            break
        direction = get_joy_direction(controller.get_axis(0), controller.get_axis(1)) #get direction based on x y axes
        if direction != prev_direction: #check if direction is new. If add to ble command q
            ble_q.append(direction)
        prev_direction = direction

        button = controller.get_button(PICTURE_BUTTON) #similar process but for the X button. Only print when it is pressed down
        if button != prev_button and button == 1:
            ble_q.append(AUTO_COMMAND) #Send robot into auto mode

        prev_button = button

async def write(client, message): #write using the characteristic
    if client.is_connected:
        await client.write_gatt_char(write_characteristic, message.encode(), response=True)
    else:
        print("Error in ble write(): client disconnected.")
        sys.exit(-1)

async def ble_t():
    try:
        device_address = "NULL" #set to null to check if device_name could be discovered
        print("Scanning...")
        devices = await bleak.discover() #get all BLE devices
        if DISCOVER == True:
            print("Discovering BLE Devices...")
        for d in devices:
            if d.name != "" and DISCOVER == True: #print out all the discovered devices if in discover mode
                print("'" + d.name + "'")
            if d.name == device_name: #search for device_name
                device_address = d.address #set address, used to connect
                if DISCOVER == False:
                    break
        if device_address == "NULL":
            print("BLE device not found")
            return
        print("Connecting to BLE " + device_name + " on " + device_address + "...")
        client = bleak.BleakClient(device_address) #setup a bleak client 
        await client.connect() #connect to it
        print ("BLE connected")
        print("\nEnter Xbox Controls. Left joystick to control, B to exit.\n")
        command = None
        while command != EXIT_COMMAND:
            while len(ble_q) < 1:
                continue
            command = ble_q.pop() #pull things off the ble queue and write to the device
            #print(command)
            await write(client, command)
        
    except Exception as e:
        print("Exception caught:")
        print(e)
    finally:
        if "client" in locals() and client.is_connected:
            print("Disconnecting...")
            await client.disconnect()
        else:
            print("Error: lost BLE connection")

p_viewer = subprocess.Popen([sys.executable, "viewer.py"], stderr=subprocess.DEVNULL) #create the wifi viewer subprocess, ignore stderr this script sucks

controller_t = threading.Thread(target=controller_handler, args="") #make a thread to take in controller input
controller_t.start()

asyncio.run(ble_t()) #run the async ble main function

stop_threads = True #Stop controller thread if ble function exits
controller_t.join() #wait for controller thread to exit from 'B' button 
os.kill(p_viewer.pid, signal.SIGINT) #kill the wifi frame viewer process
