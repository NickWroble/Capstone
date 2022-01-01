import asyncio 
import bleak #BLE client 
import time

device_name = "PCBees BLE" #Change this to your board's name

DISCOVER = False #uncomment this out if you're unsure of your device name

RW_characteristic = "12345678-1234-5678-1234-56789abcdef3"

data_to_send = [
                "Hello World!",
                "abcdefghijklmnopqrstuvwxyz",
                "PCBees",
                "NoCapStone",
                "Go",
                "IT'S THE POLICE OPEN UP WE HAVE THE BUILDING SURROUNDED.",
                "We're trying to contact you about your car's extended warranty.",
                "Simon says repeat after me.",
                "Stop",
                "ECHO Echo echo",
                "1234567890",
                ]

read_times = []
write_times = []

def avg(lst):
    return sum(lst) / len(lst)

async def write(client, message): #write using the RW characteristic
    print("Sending: " + message)
    if client.is_connected:
        await client.write_gatt_char(RW_characteristic, message.encode(), response=True)
        ret = True
    else:
        print("Error in write(): client not connected.")
        ret = False
    return ret    

async def read(client):
    if client.is_connected:
        text = (await client.read_gatt_char(RW_characteristic, response=True)).decode() #read using the RW characteristic and decode it
        print("Read:    " + text)
    else:
        text = None
    return text


async def main():
    incorect_messages = 0
    try:
        read_success    = [0] * len(data_to_send)
        write_success   = [0] * len(data_to_send)
        device_address = "NULL" #set to null to check if device_name could be discovered
        start_discover = time.time()
        devices = await bleak.discover() #get all BLE devices
        for d in devices:
            if d.name != "" and DISCOVER == True:
                print("." + d.name + ".")
            if d.name == device_name: #search for device_name
                device_address = d.address #set address, used to connect
                if DISCOVER == False:
                    break
        if device_address == "NULL":
            print("BLE device not found.")
            return
        print("Found " + device_name + " at " + device_address + " in " + "{:.4f}".format(time.time() - start_discover) + " seconds\n")
        client = bleak.BleakClient(device_address) #setup a bleak client 
        start_connect = time.time()
        await client.connect()
        print ("Connect time: " + "{:.4f}".format(time.time() - start_connect) + " seconds.\n")

        print("Press enter key to turn the LED on.")
        input()
        await client.write_gatt_char(RW_characteristic, "Go".encode(), response=True)
        
        print("Press enter key to turn the LED off.")
        input()
        await client.write_gatt_char(RW_characteristic, "Stop".encode(), response=True)
        
        for i in range(len(data_to_send)):
            start_send = time.time()
            ret = await write(client, data_to_send[i])
            write_success[i] = 0
            if ret: #write success
                write_success[i] = 1
                end_send = (time.time() - start_send) * 1000
            write_times.append(end_send)
            print ("Send time:    " + "{:.4f}".format(end_send) + " ms.")

            start_read = time.time()
            txt = await read(client)
                     
            if txt != data_to_send[i]:
                print("Sent/received do not match!")
                
            elif not txt:
                print("Could not read from device.")
            else:
                read_success[i] = 1
            
            end_read = (time.time() - start_read) * 1000
            read_times.append(end_read)
            print ("Read time:    " + "{:.4f}".format(end_read) + " ms.\n")
            time.sleep(0.5)
    except Exception as e:
        print(e)
    finally:
        if client.is_connected:
            start_disconnect = time.time()
            await client.disconnect()
            print ("Disconnect time: " + "{:.4f}".format(time.time() - start_disconnect) + " seconds.\n")

        else:
            print("Could not disconnect: already disconnected\n")
        time.sleep(0.5)

    if(len(read_times) > 0):
        print("Average read time:  " + "{:.4f}".format(avg(read_times)) + " ms.")
        print("Average write time: " + "{:.4f}".format(avg(write_times)) + " ms.")
        print("Successful reads: " + str(sum(read_success)) + "/" + str(len(data_to_send)))
        print("Successful writes: " + str(sum(write_success)) + "/" + str(len(data_to_send)))

asyncio.run(main())