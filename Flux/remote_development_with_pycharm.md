# Setting up Remote Development using pycharm

### Setup Instructions:

1. Launch PyCharm:

    - Open PyCharm on your local machine.
    - From File menu, select "Remote Development".
2. Start a New SSH Connection:

    - Under the "SSH Connection" section, click "New Connection".
3. Configure SSH Connection Details:

   - A dialog will appear for "SSH Configuration."
   - Host: Enter the IP address or hostname of your remote server.
   - Port: (Usually 22) Specify the SSH port if it's different from the default.
   - Username: Enter your username for logging into the remote server.
   - Password: Enter password for the host ip address you entered. You can choose to "Save password."
   - Click "Test Connection" to verify that PyCharm can connect to the remote server with the provided credentials.
   - Click "Check Connection and Continue" once the connection is successful.
4. Specify Remote IDE and Project Directory:

    - On the next window, you'll see options for setting up the remote IDE backend and your project.
    - IDE version:
      - PyCharm will typically suggest automatically fetching the IDE backend from JetBrains installers storage. This is usually the easiest option.
      - You can also choose "Other options" if you need to fetch from a custom download link or upload an installer file manually.
    - Project directory:
      - Existing project: If your project files are already on the remote server, enter the absolute path to the root directory of your project.
      - New project: If you want PyCharm to create a new project directory on the remote server, enter the desired absolute path for the new project (e.g., /home/youruser/new_remote_project). PyCharm will create this directory and initialize a new project there.
    - Click "Download and Start IDE" (or similar button, the wording might slightly vary depending on the PyCharm version).
5. PyCharm Backend Setup and Client Launch:

    - PyCharm (via JetBrains Gateway) will now:
      - Download the PyCharm IDE backend to your remote server (if not already present).
      - Install and configure the backend.
      - Launch the headless PyCharm backend on the remote server.
      - Launch the JetBrains Client on your local machine, which connects to the backend and displays the familiar PyCharm UI with your remote project.
