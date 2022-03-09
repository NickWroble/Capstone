import asyncio
from asyncio.subprocess import PIPE
from signal import signal
import bleak #BLE client 
import time
import subprocess
import sys
import os
import signal

device_name = "Nordic_UART_Service" #Change this to your board's name

DISCOVER = False #uncomment this out if you're unsure of your device name

RW_characteristic = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"

write_times = []

def avg(lst):
    return sum(lst) / len(lst)

async def write(client, message): #write using the RW characteristic
    if client.is_connected:
        await client.write_gatt_char(RW_characteristic, message.encode(), response=True)
    else:
        print("Error in ble write(): client disconnected.")
        sys.exit(-1)

async def main():
    try:
        device_address = "NULL" #set to null to check if device_name could be discovered
        print("Scanning...")
        start_discover = time.time()
        devices = await bleak.discover() #get all BLE devices
        if DISCOVER == True:
            print("Discovering BLE Devices...")
        for d in devices:
            if d.name != "" and DISCOVER == True:
                print("'" + d.name + "'")
            if d.name == device_name: #search for device_name
                device_address = d.address #set address, used to connect
                if DISCOVER == False:
                    break
        if device_address == "NULL":
            print("BLE device not found.")
            return
        print("Connecting to BLE " + device_name + " on " + device_address + "...")
        client = bleak.BleakClient(device_address) #setup a bleak client 
        start_connect = time.time()
        await client.connect()
        print ("BLE connected")

        await write(client, 'c')
        time.sleep(1)
        await write(client, 'c')

        print("\nEnter 'c' to take a picture or 'e' to exit.\n>", end='')
        command = input()
        while command != 'e':
            if command == 'c':
                start_send = time.time()
                await write(client, 'c')
                end_send = (time.time() - start_send) * 1000
                write_times.append(end_send)
                #print ("Send time:    " + "{:.4f}".format(end_send) + " ms.")
            print("\nEnter 'c' to take a picture or 'e' to exit.\n>", end='')
            command = input()
    except Exception as e:
        print("\nException caught:")
        print(e)
    finally:
        if client.is_connected:
            print("\nDisconnecting...")
            start_disconnect = time.time()
            await client.disconnect()
            #print ("Disconnect time: " + "{:.4f}".format(time.time() - start_disconnect) + " seconds.\n")

        else:
            print("Error: lost BLE connection\n")
        time.sleep(0.5)

    #if(len(write_times) > 0):
        #print("Average write time: " + "{:.4f}".format(avg(write_times)) + " ms.")

p_viewer = subprocess.Popen([sys.executable, "viewer.py"], stderr=subprocess.DEVNULL)

asyncio.run(main())

os.kill(p_viewer.pid, signal.SIGINT)
