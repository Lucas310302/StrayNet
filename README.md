# StrayNet

![Straynet Screenshot](https://github.com/Lucas310302/StrayNet/blob/main/img.png)

## Introduction

StrayNet is a powerful remote administration tool (RAT) designed for remote control and management of client machines. With StrayNet, you can remotely execute commands, stream webcam and screen feeds, capture screenshots, conduct DDoS attacks, and more. Whether you're a system administrator needing to manage multiple machines remotely or a security professional conducting penetration testing, StrayNet provides the tools you need to efficiently and effectively control client systems.

## Features

- **Remote Command Execution**: Execute shell commands on client machines remotely.
- **Webcam Streaming**: Stream live webcam feed from client machines to the server.
- **Screen Streaming**: Stream live screen feed from client machines to the server.
- **Screenshot Capture**: Capture screenshots of client machines and send them to the server.
- **DDoS Attack**: Conduct SYN flood DDoS attacks on target IP addresses.
- **Persistence and Admin Privileges**: Automatically set up persistence and admin privileges on client machines for Windows and Unix systems.

### Installation

1. Clone the StrayNet repository to your local machine:
   ```git clone https://github.com/example/straynet.git```

2. Navigate to the cloned directory:
    ```cd straynet```

3. Install the required Python dependencies:
    ```pip install -r requirements.txt```

### Building the Client into an Executable

1. Install Pyinstaller:
    ```pip install pyinstaller```

2. Navigate to the directory containing the StrayNet client script (client.py).
3. Run PyInstaller to build the executable:
    ```pyinstaller --onefile client.py```
4. Once the process is complete, you'll find the executable file in the dist directory.

Now you have a standalone executable of the StrayNet client that you can distribute and run on target machines without requiring Python or additional dependencies.

---

Disclaimer: StrayNet is provided for educational purposes only. The author takes no responsibility for any misuse of this tool.
