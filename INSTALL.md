# CFRS Installation and Setup Guide

This guide explains how to set up the Campus Facility Reservation System (CFRS) for local development and demonstration.

> **Submission archive:** `IT401W_ProjectB_4GG2_Group2.zip`  
> **Development use only:** The supplied Django settings enable `DEBUG = True` and use SQLite with Django's development server. Do not expose this configuration as a production deployment.

## 1. Prerequisites

Install the following before starting:

- **Python:** 3.12, 3.14, or another version supported by the pinned Django 6.1.1 (Django 6.1 supports Python 3.12–3.14). The project has been tested on 3.12 and 3.14.
- **pip:** Included with standard Python installations.
- **Terminal:** Windows PowerShell or Command Prompt, macOS Terminal, or a Linux shell.
- **SQLite:** Used by the project as its development database. It is normally available through Python's `sqlite3` module.

Check your Python and pip installation:

```bash
python --version
python -m pip --version
python -c "import sqlite3; print(sqlite3.sqlite_version)"
```

On Windows, if `python` is not recognized, try `py` instead. Use the same Python launcher consistently for creating and activating the virtual environment and running Django commands.

## 2. Extract the Submission Archive and Locate the Django Project

1. Extract `IT401W_ProjectB_4GG2_Group2.zip` to a folder where you have permission to create files.
2. Open the extracted project in File Explorer or your preferred editor.
3. Locate the directory containing **both** `manage.py` and `requirements.txt`.
4. Open a terminal in that directory. Run all Django commands in this guide from that directory.

The exact folder name depends on how the submission archive is extracted. Do not assume a particular nested directory name; use the folder that actually contains `manage.py` and `requirements.txt`.

To confirm that the terminal is in the correct directory, run one of the following.

**Windows PowerShell:**

```powershell
Get-ChildItem manage.py, requirements.txt
```

**macOS/Linux:**

```bash
ls manage.py requirements.txt
```

Both files should be found. If either is missing, navigate to the directory containing the Django project before continuing.

## 3. Create a Virtual Environment

A virtual environment keeps the project's Python dependencies separate from other Python projects on your computer.

From the directory containing `manage.py` and `requirements.txt`, run:

```bash
python -m venv .venv
```

### Activate on Windows PowerShell

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation because of the execution policy, you can allow script execution for the current PowerShell process only and retry:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

This process-scoped change does not permanently change the machine's execution policy.

### Activate on Windows Command Prompt

```bat
.\.venv\Scripts\activate.bat
```

### Activate on macOS/Linux

```bash
source .venv/bin/activate
```

Once activated, your terminal may show `(.venv)`. Verify the selected interpreter:

```bash
python --version
python -m pip --version
```

## 4. Install the Pinned Dependencies

With the virtual environment active, install the packages specified by the project's `requirements.txt`:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The supplied requirements file pins these packages:

- `Django==6.1.1`
- `asgiref==3.12.1`
- `python-dotenv==1.2.4`
- `sqlparse==0.6.0`

If dependency installation fails, confirm that the virtual environment is active and that your Python version is compatible with the pinned Django release.

## 5. Create the Local Environment File

CFRS requires a Django secret key from the `DJANGO_SECRET_KEY` environment variable. The project settings load a local `.env` file from the same directory as `manage.py`.

The repository includes a template named `.env.example`. Copy it to `.env` in the directory containing `manage.py`:

**Windows PowerShell / Command Prompt:**

```powershell
copy .env.example .env
```

**macOS/Linux:**

```bash
cp .env.example .env
```

Generate a new key by running:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Open `.env` and replace the placeholder so the line reads (use your generated key):

```dotenv
DJANGO_SECRET_KEY=paste_your_generated_key_here
```

Save the file. Do not include angle brackets or leave the example text in place.

To edit the file, on Windows run `notepad .env`; on macOS/Linux open `.env` in your preferred text editor.

### Keep the secret key private

- Do not commit `.env` or share the secret key publicly.
- The repository's ignore rules are intended to exclude `.env` files; verify the file is ignored before committing.
- Do not put a real key in this guide, screenshots, public issues, or submission evidence.
- If a real key is exposed, generate a replacement.

## 6. Create the Database and Check the Project

With the virtual environment active and `.env` saved, run:

```bash
python manage.py migrate
python manage.py check
```

- `migrate` applies the migrations included with the project and creates the local SQLite database file if needed.
- `check` runs Django's system checks for configuration and common application issues.

Use the supplied migrations. `makemigrations` is not part of the normal installation procedure.

## 7. Load Fictional Demonstration Data

For a fresh local database, run:

```bash
python manage.py seed_demo
```

The command creates fictional demonstration records for facility categories, facilities, amenities, reservations, closure blocks, event records, reservation history, incidents, and audit entries. On a fresh database it creates 2 administrators, 8 basic users, 3 categories, 6 facilities, 8 amenities, 5 closures, 24 reservations, 8 event records, 2 incidents, and 37 audit entries; running it a second time leaves these counts unchanged. The exact created or updated records on a non-empty database depend on what already exists.

### Demo-account password

When the command needs to create sample accounts that do not already exist, it prompts you to choose a password with **at least 12 characters**. The password is entered without being displayed in the terminal. On a fresh database, the chosen password is used for the sample accounts created by the command.

The demonstration administrator usernames are:

- `admin_adrian`
- `admin_sofia`

The fictional Basic User usernames are:

- `miguel.santos`
- `andrea.reyes`
- `joshua.cruz`
- `sofia.garcia`
- `daniel.mendoza`
- `isabella.torres`
- `nathan.flores`
- `camille.ramos`

Use the password you selected when signing in to accounts created during this run. If a matching account already exists, the command preserves its existing password rather than resetting it; a password entered on a later run may therefore not apply to previously created accounts.

> **Important:** Use `seed_demo` only with a local demonstration database containing fictional data. It creates or updates matching sample records. Do not run it against a database containing real student information or records that must be preserved.

The seed command performs a sequential conflict check only. Simultaneous approvals are covered separately by the concurrency tests described in Section 10.

## 8. Start the Development Server

From the directory containing `manage.py`, with the virtual environment active, run:

```bash
python manage.py runserver
```

Open the site in a browser:

<http://127.0.0.1:8000/>

**Stopping the server:** Return focus to the terminal running the development server and press `Ctrl+C`. On some Windows setups, `Ctrl+Break` may also be used if `Ctrl+C` does not stop the process. IDEs may additionally provide a Stop or Terminate control for the running terminal task.

If port 8000 is already in use, run the server on another local port:

```bash
python manage.py runserver 8001
```

Then open <http://127.0.0.1:8001/>.

When finished, you can leave the virtual environment with:

```bash
deactivate
```

## 9. Main Application Routes

| Path | Purpose |
|---|---|
| `/` | Sign-in page and role-based redirect after authentication |
| `/auth/` | Authentication routes, including registration, login, logout, and profile operations |
| `/auth/register/`, `/auth/profile/`, `/auth/logout/` | Registration, profile, and logout |
| `/facilities/` | Public facility catalog (`/facilities/<id>/` for facility detail) |
| `/portal/` | Basic User portal; sign-in required |
| `/reservations/create/<facility_id>/` | Submit a reservation request; Basic User only |
| `/reservations/my-reservations/` | Signed-in user's reservations |
| `/reservations/cancel/<id>/` | Cancel own reservation (POST only) |
| `/manage/` | Custom Admin dashboard; administrator access required |
| `/manage/users/`, `/manage/facilities/`, `/manage/categories/`, `/manage/amenities/` | Account and master-data management |
| `/manage/reservations/` | Reservation review queue |
| `/manage/calendar/` | Administrator reservation calendar |
| `/manage/events/` | Event monitoring, check-in, completion, incidents, printable slips |
| `/manage/closures/` | Facility closure periods |
| `/manage/reports/` | Reports and CSV export |
| `/manage/audit-logs/` | Audit log |
| `/manage/settings/` | Booking policy settings |

CFRS uses its own Admin views, forms, templates, URLs, and ORM operations. The Django built-in Admin site is not the application's custom management interface.

## 10. Optional: Run the Existing Tests

Running the tests is optional for initial setup. From the directory containing `manage.py`, run:

```bash
python manage.py test
```
The latest recorded full run reported 160 tests: OK, 7 skipped (about 103 seconds on the tester's machine). Tests use a temporary in-memory database and do not touch `db.sqlite3`.

The simultaneous-booking and approval tests are separate: they run only with `--settings=config.settings_concurrency` on a temporary SQLite file, and skip themselves in a normal run.

```bash
python manage.py test reservations.test_concurrency --settings=config.settings_concurrency --noinput -v 2
```

Record the actual command and result if you use this output as project testing evidence. A successful `python manage.py check` does not mean the test suite passes.

## 11. Troubleshooting

### `KeyError: 'DJANGO_SECRET_KEY'`

Django could not find the required secret key. Confirm that:

- The file is named `.env`, not `.env.txt`.
- `.env` is in the same directory as `manage.py`.
- The file contains `DJANGO_SECRET_KEY=...` with a value after the equals sign.
- The commands are being run from the directory containing the intended `manage.py`.

### `python` is not recognized

On Windows, try `py` in place of `python`. Ensure Python is installed and available through the terminal.

### `No module named django`

Activate the virtual environment and install the requirements again:

```bash
python -m pip install -r requirements.txt
```

### `can't open file 'manage.py'`

The terminal is not in the Django project directory. Locate `manage.py` in the extracted submission and open the terminal in that directory. Do not rely on a hard-coded folder name.

### Database or migration problems

Confirm that you're using the intended local project directory and that the database file belongs to this local demonstration setup. Do not delete or reset a database containing records you need. For a fresh demonstration setup, use an empty local database and then run `python manage.py migrate` followed by `python manage.py seed_demo`.

## 12. Development and Security Notes

- This guide is for local development and classroom demonstration.
- The provided settings use `DEBUG = True`, `ALLOWED_HOSTS = []`, and Django's development server. Do not use these settings to expose the system publicly or as a production deployment.
- Keep `.env` and account passwords private.
- Use fictional demonstration data only.
- Concurrency evidence is limited to threaded tests on one machine against a file-based SQLite database (two simultaneous approvals, up to 30 simultaneous bookings). Do not extend those results to production load or other databases.

