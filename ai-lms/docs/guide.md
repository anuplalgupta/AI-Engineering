# Running AI-LMS on your own computer

This guide is for someone who is not a software engineer. It takes you from a Windows PC with nothing installed to the sample tutorial on screen. Notes for Mac and Linux are at the end.

**Version:** milestone M1 (walking skeleton). What you can show: enter as the demo student and read one tutorial with equations and a diagram.

Everything runs on your computer. Nothing is sent to the internet, there is no account to create, and nothing costs money.

## 1. What you need

- A PC with at least **8 GB of memory, 4 processor cores and 10 GB of free disk space**.
- **Windows 10 (version 22H2) or Windows 11**, with permission to install software.
- An internet connection for the first start only (to download the parts).

You will install **WSL 2** (Windows' built-in Linux) and **Docker** (which runs the parts of the product in "containers"). There are two ways to get Docker:

| Route | Cost | Notes |
|---|---|---|
| **Docker Engine inside WSL** (used in this guide) | Free | Typed commands only, no Docker window |
| Docker Desktop | Free for personal use, education and small companies; **a paid subscription is required at larger companies** (more than 250 employees or more than US$10 million a year in revenue) | Has a window with buttons. If you use it, skip step 3 and type the same commands in its WSL terminal |

## 2. Install WSL 2 and Ubuntu

1. Click **Start**, type `PowerShell`, right-click **Windows PowerShell** and choose **Run as administrator**.
2. Type this and press Enter:
   ```
   wsl --install -d Ubuntu
   ```
3. Restart the PC when asked.
4. After the restart an **Ubuntu** window opens. Choose a user name and a password (you will need this password later; nothing appears on screen while you type it).

From now on, every command in this guide is typed in the **Ubuntu** window. To open it again later: **Start**, type `Ubuntu`, press Enter.

## 3. Install Docker Engine inside Ubuntu

Type these commands one at a time. Enter your Ubuntu password if asked.

1. Install Docker:
   ```
   curl -fsSL https://get.docker.com | sudo sh
   ```
2. Allow your user to run Docker:
   ```
   sudo usermod -aG docker $USER
   ```
3. Close the Ubuntu window and open it again.
4. Check that Docker works:
   ```
   docker run --rm hello-world
   ```
   You should see "Hello from Docker!". If you see "Cannot connect to the Docker daemon", type `sudo service docker start` and try again.

## 4. Get AI-LMS

1. Download the code into your Ubuntu home folder (replace the address with the one you were given):
   ```
   cd ~
   git clone <repository address> ai-engineering
   cd ai-engineering
   ```
   Keep the code inside Ubuntu (as above), not on the Windows `C:` drive: it is much faster.

All the commands below are typed in this folder. If you open a new Ubuntu window, first type `cd ~/ai-engineering`.

## 5. Set up (once)

1. Create the settings file with new random passwords:
   ```
   sh ai-lms/deploy/setup.sh
   ```
   It writes `ai-lms/deploy/.env`. There are no default passwords: each computer gets its own. If the file already exists, the script changes nothing, except that it adds any setting a newer version needs (it says so when it does).

## 6. Start

1. Start everything:
   ```
   docker compose -p ailms -f ai-lms/deploy/compose.yaml up -d
   ```
   The **first start takes several minutes**: it downloads and builds the parts, creates the database and loads the sample course. Later starts take a few seconds.
2. Check that everything is running:
   ```
   docker compose -p ailms -f ai-lms/deploy/compose.yaml ps
   ```
   Wait until all six (`web`, `backend`, `worker`, `db`, `objectstore` and `mail`) say **(healthy)**. Run the command again if some still say "starting". This usually takes under a minute once the parts are downloaded.

## 7. Open the product and enter as the demo student

1. In your web browser on Windows, open **http://localhost:8080**
2. Under **Try the demo**, click **Enter as demo student**.
3. Open the course **Physics, Class 11 (sample): Vectors and Kinematics**.
4. Open the topic **Adding vectors and resolving them into components**. The tutorial shows text, equations and a diagram.

To see it as on a phone: press **F12**, click the phone-and-tablet icon at the top of the panel, and set the width to **360**.

The other demo accounts are **Enter as demo reviewer** and **Enter as demo admin**. In this version they see the same pages.

## 8. Sign in with an email code (optional)

Sign-in by email works without sending real email: messages are caught by a mail viewer on your computer.

1. Sign out, then under **Sign in with your email** enter `student@demo.example` (or any made-up address, which creates a new student account) and click **Send me a code**.
2. Open **http://localhost:8025** in another tab. The newest message holds a six-digit code.
3. Type the code and click **Sign in**. A code works once and expires after 10 minutes.

The email can take a few seconds to arrive: it is sent by the `worker` part, not straight away. To stop guessing, an address that gets 10 wrong codes in a day cannot sign in by email for 24 hours, and no more than 10 codes a day are sent to one address. Too many requests from one computer in an hour get the message *Too many requests from this address*; wait and try again.

## 9. Stop, and start again

- **Stop** (your data is kept):
  ```
  docker compose -p ailms -f ai-lms/deploy/compose.yaml stop
  ```
- **Start again**:
  ```
  docker compose -p ailms -f ai-lms/deploy/compose.yaml up -d
  ```

The containers also stop when Windows shuts down. After a restart, open Ubuntu, type `cd ~/ai-engineering` and start again. (With Docker Engine inside WSL, Docker itself may need `sudo service docker start` first.)

## 10. Where your data is kept

| What | Where |
|---|---|
| Database (accounts, courses, lessons) | Docker volume `ailms_db-data` |
| Files (diagrams) | Docker volume `ailms_object-data` |
| Passwords and settings | `ai-lms/deploy/.env` (keep it private; never share or commit it) |
| Sign-in emails | Only in the mail viewer's memory; they disappear when it stops |

Volumes live inside WSL, managed by Docker. Stopping, starting or restarting the PC keeps them. To list them: `docker volume ls --filter name=ailms`.

## 11. Wipe everything and start from nothing

This **deletes all data** (accounts, any changes, the database) and cannot be undone.

1. Stop and delete the containers and the data volumes:
   ```
   docker compose -p ailms -f ai-lms/deploy/compose.yaml down -v
   ```
2. Delete the settings file and write a new one:
   ```
   rm ai-lms/deploy/.env
   sh ai-lms/deploy/setup.sh
   ```
3. Start again as in step 6. The sample course is loaded afresh.

Only the `ailms` project is affected; other Docker containers on the computer are left alone.

## 12. If something goes wrong

| What you see | What to do |
|---|---|
| `Run the setup script first` | Do step 5, then start again |
| `Run the setup script first` after updating to a newer version | Run the setup script of step 5 again: it adds the new setting to your existing file and keeps your data |
| No email arrives in the mail viewer | Check that `worker` is (healthy) in the `ps` command of step 6, and wait a few seconds |
| `port is already allocated` for 8080 or 8025 | Another program uses that port. Stop it, or ask a developer to change the port in `ai-lms/deploy/compose.yaml` |
| The page at localhost:8080 does not load | Wait a minute after starting, then run the `ps` command of step 6. To see what went wrong: `docker compose -p ailms -f ai-lms/deploy/compose.yaml logs backend` |
| `CERTIFICATE_VERIFY_FAILED`, `UNABLE_TO_GET_ISSUER_CERT_LOCALLY` or `SELF_SIGNED_CERT_IN_CHAIN` while building, on a company network | The network inspects secure connections. Ask IT for the company's root certificate as a `.pem` file, add a line `AILMS_EXTRA_CA=/path/to/that.pem` to the end of `ai-lms/deploy/.env` (in Ubuntu a path such as `/home/you/company-root.pem`; in PowerShell a path such as `C:/Users/you/company-root.pem`, with forward slashes), and start again. Certificates are still checked; this only adds your company's one to the trusted list while building |
| `E401` or `Incorrect or missing password` while building the web part | Your computer's npm settings point at a private package mirror. The build does not use them; if you still see this, tell a developer |

## Notes for Mac and Linux

- **Mac:** install Docker Desktop (same licence rule as above), open **Terminal**, and follow steps 4 to 11. Docker Desktop must be running before step 6.
- **Linux:** install Docker Engine (step 3 works on Ubuntu and Debian), then follow steps 4 to 11 in a terminal.
- **Windows with Docker Desktop and PowerShell** instead of Ubuntu: run the setup with `powershell -ExecutionPolicy Bypass -File ai-lms\deploy\setup.ps1`; the `docker compose` commands are the same.

## For developers

- Run the tests (they use a throwaway database, not the demo data): `docker compose -p ailms -f ai-lms/deploy/compose.yaml run --rm backend pytest`
- More in `ai-lms/backend/README.md`.

## What it needs

Measured on the **development PC** (Windows 11, Docker Desktop, 32 GB of memory), not yet on an 8 GB, 4-core machine:

| What | Measured |
|---|---|
| Memory used by the idle system (all six containers, sample data loaded, `docker stats --no-stream`) | about **205 MB**: backend 77 MB, worker 51 MB, database 41 MB, web 14 MB, object store 12 MB, mail viewer 9 MB |
| Disk used by the parts (images) | about **1.2 GB**: database 622 MB, backend 354 MB, object store 121 MB, web 72 MB, mail viewer 51 MB. The data itself is small at first |
| Time from `up -d` to all six healthy | about **30 seconds** once the parts are downloaded and built, both on the first start (empty database, sample data loaded) and on later starts |
| First start including download and build | a few minutes, depending on the internet connection (about 80 seconds here with most downloads already cached) |
