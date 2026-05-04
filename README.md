# Guy T Here for you

Cybersecurity-themed internal request portal for sanity testing fixes in Check Point.

## Features
- Branded page title: **Guy T Here for you**
- Request form fields:
  - Machine (Physical or VM)
  - Main version (R81.10 / R81.20 / R82 / R82.10)
  - JHF
  - SR number
  - TASK number
  - Path to fix
  - ETA
- Stores submitted requests in local SQLite database (`requests.db`)
- Listens on `0.0.0.0` so coworkers on the same LAN can access it

## Run locally
1. Open terminal in this folder.
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Start server:
   ```
   python app.py
   ```
4. Open from your machine:
   - `http://127.0.0.1:5000`
5. Open from other machines in same network:
   - `http://YOUR_LOCAL_IP:5000`

## Quick start scripts
- `start_portal.cmd` starts the portal in a visible terminal.
- `start_portal_hidden.vbs` starts it hidden in the background.

## Notes
- Allow inbound TCP port `5000` in Windows Firewall if needed.
- Change `SECRET_KEY` in `app.py` before production use.
- Tasks are deleted only by the manual **Delete Task** button in the Work Queue.
- For Render deployment, set `DB_PATH` to a persistent disk mount (example: `/var/data/requests.db`) so queue data survives idle/restart cycles.
