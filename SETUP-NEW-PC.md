# Hidden Hire: setup on a new Windows PC

Run every command in **PowerShell**. Copy one block at a time.

---

## Step 0. On the OLD PC: collect your personal files

These are git-ignored, so they are NOT on GitHub. Copy them yourself.

| What | Path in the project | Why |
|---|---|---|
| Profile and CVs | `profile\` (whole folder) | Uploaded CV, profile, master CV |
| Database | `data\hidden_hire.db` | Saved/applied jobs, scores, recruiter views |
| Tailored CVs | `output\` (whole folder) | Generated PDFs (optional) |
| API keys | `.env` | Groq, Cloudflare, data repo URL |
| LLM settings | `config\settings.yaml` | Model chains |
| Tectonic | `tools\tectonic.exe` | CV PDF compiler (or download again) |

Put them in one zip on the old PC (run inside the project folder). The zip keeps the folder names, but `settings.yaml` and `hidden_hire.db` go to its top level; Step 5 puts them back.

```powershell
cd D:\Study\Projects\Hidden-Hire
$items = "profile", "output", "tools", ".env", "config\settings.yaml", "data\hidden_hire.db" | Where-Object { Test-Path $_ }
Compress-Archive -Force -DestinationPath "$env:USERPROFILE\Desktop\hidden-hire-personal.zip" -Path $items
```

Move `hidden-hire-personal.zip` with a USB drive or a **private** cloud folder (Google Drive, OneDrive).
Never upload it to GitHub, email it to others or share it in chat: it has your CV and API keys.

Do NOT copy: `data\repo`, `data\jobs`, `web\node_modules`, `web\dist`, `.venv`. They are created again.

---

## Step 1. On the NEW PC: check what is installed

```powershell
git --version
py -0
python --version
conda --version
node --version
npm --version
winget --version
```

What you need:

| Tool | Need | If missing |
|---|---|---|
| Git | any version | Step 2 |
| Python 3.12 | via `py -0` (shows `-V:3.12`) **or** conda | Step 2 |
| Node.js + npm | current LTS | Step 2 |
| winget | comes with Windows 10/11 | Update "App Installer" from Microsoft Store |

"is not recognized" means it is not installed.

---

## Step 2. Install what is missing

Install only the lines you need. Accept the prompts.

```powershell
winget install --id Git.Git -e
winget install --id Python.Python.3.12 -e
winget install --id OpenJS.NodeJS.LTS -e
```

Want conda instead of plain Python? Use this line instead of the Python one:

```powershell
winget install --id Anaconda.Miniconda3 -e
```

**Close PowerShell and open a new one**, then run Step 1 again to confirm.

---

## Step 3. Get the code

Pick a folder, for example `D:\Projects`:

```powershell
mkdir D:\Projects -Force
cd D:\Projects
git clone https://github.com/estkayon/hidden-hire.git Hidden-Hire
cd Hidden-Hire
```

---

## Step 4. Python environment (choose A or B)

### A. Plain Python (no conda)

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-ml.txt
```

### B. Conda

```powershell
conda create -n hidden-hire python=3.12 -y
conda activate hidden-hire
pip install -r requirements-ml.txt
```

If `conda activate` says "run conda init", run `conda init powershell`, reopen PowerShell, and try again.

The install downloads PyTorch and other libraries, so it takes a while.
`start.bat` finds both: a `.venv` folder in the project, or the `hidden-hire` conda environment.

---

## Step 5. Restore your personal files

Copy `hidden-hire-personal.zip` into the project folder, then:

```powershell
Expand-Archive -Force hidden-hire-personal.zip -DestinationPath .
Remove-Item hidden-hire-personal.zip
New-Item -ItemType Directory -Force data | Out-Null
if (Test-Path settings.yaml) { Move-Item -Force settings.yaml config\settings.yaml }
if (Test-Path hidden_hire.db) { Move-Item -Force hidden_hire.db data\hidden_hire.db }
```

Check that they landed in the right place:

```powershell
Test-Path profile\master_cv.yaml, data\hidden_hire.db, .env, config\settings.yaml, tools\tectonic.exe
```

All should print `True` (master CV and database only if you had them).

**New user, nothing to restore?** Do this instead:

```powershell
copy .env.example .env
copy config\settings.example.yaml config\settings.yaml
notepad .env
```

In `.env` set at least:

```ini
DATA_REPO_URL=https://github.com/estkayon/hidden-hire-data.git
```

Add your own `GROQ_API_KEY`, `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_KEY` if you want the recruiter view and tailored CVs.
For CV PDFs, download Tectonic for Windows from https://github.com/tectonic-typesetting/tectonic/releases and save it as `tools\tectonic.exe`.

---

## Step 6. Build the dashboard (once)

```powershell
cd web
npm install
npm run build
cd ..
```

---

## Step 7. Check that everything works

```powershell
python -c "import fastapi, sqlalchemy, httpx, pypdf, litellm, sentence_transformers; print('Python packages OK')"
python -m pytest -q
Test-Path web\dist\index.html
```

You should see `Python packages OK`, all tests passing, and `True`.

---

## Step 8. Start the app

Either double-click **`start.bat`** in the project folder, or:

```powershell
python -m app.main
```

Then open http://127.0.0.1:8000.
The first start pulls the job data and downloads a small embedding model, so it takes a minute.

Check the background sync from a second PowerShell window:

```powershell
curl.exe http://127.0.0.1:8000/api/sync
```

---

## Step 9. Desktop shortcut with the icon (optional)

```powershell
powershell -ExecutionPolicy Bypass -File create-shortcut.ps1
```

If the shortcut does not show on the desktop: right-click the desktop, View, Show desktop icons.

---

## Step 10. Only if you will commit code from this PC

```powershell
git config --global user.name "Md. Estiak Rahman Ayon"
git config --global user.email "estiakayon@gmail.com"
pip install pre-commit
pre-commit install
```

---

## Updating later

```powershell
cd D:\Projects\Hidden-Hire
git pull
pip install -r requirements-ml.txt
cd web; npm install; npm run build; cd ..
```

---

## Common problems

| Problem | Fix |
|---|---|
| `py` or `python` not recognized | Reinstall Python 3.12 (Step 2), reopen PowerShell |
| `.venv\Scripts\Activate.ps1 cannot be loaded` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `start.bat` says Python was not found | Create the environment in Step 4 first |
| Port 8000 already in use | The app is already running. Close its window, or `netstat -ano \| findstr :8000` then `taskkill /PID <number> /F` |
| Dashboard looks old after `git pull` | `cd web; npm run build; cd ..` |
| Generate CV fails | Check `tools\tectonic.exe` and the LLM keys in `.env` |
| No new jobs | Click Refresh. If the cloud fetch is old, the app fetches on your PC by itself |
