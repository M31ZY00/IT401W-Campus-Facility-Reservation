# Campus Facility Reservation System (CFRS)

> IT401W · Project B · Section 4GG2 · Group 2
> Submission package: `IT401W_ProjectB_4GG2_Group2.zip`

CFRS is a Python/Django web application that lets campus users request a facility for an event, while administrators manage facilities, availability, approvals, schedules, event completion, and operational reports. It prevents conflicting approved reservations and keeps an auditable schedule.

**Quick links:** [Installation](#installation-and-setup) · [Overview and features](#project-overview-and-feature-list) · [Business rules](#business-rules-summary) · [System diagrams](#system-diagrams) · [System Option Evaluation](#system-option-evaluation-and-recommendation) · [Maintenance Guide](#maintenance-guide) [Testing](#testing) · [Evidence index](#evidence-index) · [Limitations](#limitations-and-enhancements) · [Team](#project-team)

---

## Project Team

| Member | Role / responsibilities |
|---|---|
| CAASI, Humphrey A | `Database and Backend Testing` | 
| DE BELEN, Anne Gheela D | `Basic User UI` | 
| JACINTO, Joshua James E | `Documentation` | 
| ORTIZ, Ralth Jasper | `Backend Integration` | 
| PARAISO, Samantha Nicole B | `Admin UI` | 
| SANTOS, Mischa Mae | `Lead Coordinator/Developer` |

**Instructor:** DR. AARON PAUL M. DELA ROSA ·  **Presentation and Q&A:** Week 17

---
## Installation and Setup
```bash
# 1. Unzip IT401W_ProjectB_4GG2_Group2.zip to desired location
# 1. From the folder containing manage.py and requirements.txt
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1      macOS/Linux: source .venv/bin/activate

# 2. Install pinned dependencies
python -m pip install -r requirements.txt

# 3. Create .env next to manage.py from the supplied template (do NOT commit .env)
#    Windows: copy .env.example .env      macOS/Linux: cp .env.example .env
#    generate your own key with: python -c "import secrets; print(secrets.token_urlsafe(50))"
#    then replace the placeholder value:  DJANGO_SECRET_KEY=<generated key>

# 4. Create the database and check the project
python manage.py migrate
python manage.py check

# 5. Load fictional demonstration data (prompts for a 12+ character password)
python manage.py seed_demo

# 6. Run the server
python manage.py runserver     # http://127.0.0.1:8000/
```
---

## Maintenance Guide

This guide provides recommended maintenance procedures for the supplied local development configuration. It does not represent an existing institutional maintenance program.

### Routine Checks

- Review pending reservation requests and upcoming facility closures.
- Keep facility details, operating hours, capacity, and booking policy settings accurate.
- Review audit records when investigating unexpected reservation changes.
- Check that cancellations, event completion, and other supported status changes are recorded correctly.

### Database Backups and Recovery

CFRS uses SQLite in the supplied configuration, with its database stored in `db.sqlite3`.

- Make a protected backup before applying significant code changes, database migrations, or other operations that may affect stored data.
- Store backups outside publicly accessible locations and restrict access because they may contain personal and reservation information.
- Periodically verify that a backup can be restored into a separate test copy of the project.
- Protect `.env` and its Django secret key. Never commit secrets or sensitive database backups to version control.

### Application Updates

Before updating the application:

1. Review the proposed changes and back up important records.
2. Install the dependencies specified by `requirements.txt` when the dependency set changes.
3. Apply required database migrations.
4. Run `python manage.py check` and `python manage.py test`.
5. Verify affected features and review any test failures before using the updated application.

Keep migration files under version control. Do not delete migration files or reset a database simply to resolve an update problem without assessing the impact on existing records.

### Security and Deployment

The current configuration is intended for development and demonstration. Before deployment beyond a local environment, review the settings in `config/settings.py`, including `DEBUG`, `ALLOWED_HOSTS`, and secret management. Configure appropriate production protections and evaluate whether the database is suitable for the expected workload.

See Installation and Setup for initial configuration and Testing for the project's recorded test evidence.

## Project Overview and Feature List

CFRS has exactly two user levels: **Basic User** and **Admin**. The administrator interface is built entirely with the project's own views, forms, templates, URLs, and ORM operations; Django's built-in admin site is not used. Roles are determined from Django's user flags, and there is no separate Role model. Most development effort went into the admin side, which handles management, approval, operational workflows, reports, settings, and audit.


### Public Visitor

Public visitors can browse the active campus facility catalog at `/facilities/` without logging in, search facilities by keyword, and inspect facility details, operating hours, capacity, and 30-minute availability schedules. Submitting reservation requests or accessing personal bookings requires signing in or creating an account. In the unauthenticated state, the top navigation provides a direct "Log in" action, and facility cards prompt visitors with "Login to Reserve". The authenticated Basic User catalog interface is separately documented below in Figure 8.

![Public visitor campus facility catalog](documentation/screenshots/public-facility-directory.png)

*Figure 1. Public visitor facility catalog displaying search filters, facility details, and Login to Reserve actions.*

### Basic User Features

| ID | Feature | What it does |
|---|---|---|
| U1 | Account and profile | Register, sign in, sign out, and edit personal name and contact fields only. Role and activation status are never user-editable. |
| U2 | Browse facilities and availability | Search active facilities by category and capacity; view amenities and 30-minute availability slots. Unavailable slots do not reveal other users or event details. |
| U3 | Submit a reservation request | Request one facility with event title, purpose, participant count, start, and end. Submission creates a **Pending** request and does not reserve the slot. |
| U4 | Track and cancel own reservations | View only own bookings and statuses; cancel Pending or Approved bookings before their start time. |

#### Registration and Sign-In (U1)

Basic users authenticate via a unified sign-in page (`/` or `/auth/`). Authentication validates active credentials and redirects basic users to the user portal (`/portal/`). The sign-in interface also provides a direct navigation link to account registration (`/auth/register/`).

![Basic User sign-in interface](documentation/screenshots/basic-user-sign-in.png)

*Figure 2. Basic User sign-in interface.*

Account registration is implemented as a multi-step guided wizard. In Step 1, new users provide their first and last name.

![Basic User registration wizard Step 1](documentation/screenshots/basic-user-registration-step1.png)

*Figure 3. Account registration wizard (Step 1 — Personal Details).*

In Step 2, users enter their email address and optional contact phone number.

![Basic User registration wizard Step 2](documentation/screenshots/basic-user-registration-step2.png)

*Figure 4. Account registration wizard (Step 2 — Contact Details).*

In Step 3, users configure their account credentials by specifying a unique username, password, and password confirmation before submitting account registration.

![Basic User registration wizard Step 3](documentation/screenshots/basic-user-registration-step3.png)

*Figure 5. Account registration wizard (Step 3 — Account Credentials).*

#### User Portal Dashboard (U1)

Upon successful authentication, basic users land on the dedicated user portal dashboard (`/portal/`). The dashboard displays a personalized welcome greeting and provides primary action cards to explore the facility catalog or review existing reservations.

![Basic User portal dashboard](documentation/screenshots/basic-user-dashboard.png)

*Figure 6. Basic User portal dashboard.*

#### User Profile Management (U1)

Authenticated users can inspect and update their personal contact details through a modal profile dialog. In accordance with system security rules, the username is displayed as read-only, and role or account activation flags cannot be viewed or altered by the user. Only first name, last name, email address, and phone number can be edited.

![Basic User profile management](documentation/screenshots/basic-user-profile.png)

*Figure 7. Basic User profile management modal dialog.*

#### Facility Browsing and Availability (U2)

Basic users can browse the campus facility catalog at `/facilities/`, search by keyword (facility name, code, or location), and filter by minimum participant capacity or facility category. Selecting a facility displays its physical location, student capacity, operating hours, active status, and equipped amenities. The availability view visualizes 30-minute time slots across operating hours for a selected date, clearly identifying open slots without exposing private booking details or attendee identities.

![Basic User facility catalog](documentation/screenshots/basic-user-facility-catalog.png)

*Figure 8. Campus facility catalog and facility details pane (authenticated Basic User session).*

![Basic User facility availability](documentation/screenshots/basic-user-facility-availability.png)

*Figure 9. Facility 30-minute availability schedule grid displaying unavailable slots for Computer Laboratory B201.*

#### Reservation Request Submission (U3)

Basic users submit reservation requests by selecting an active facility and providing the event title, purpose description, anticipated participant count, start date/time, and end date/time. The request modal prominently displays policy constraints, including the 30-day advance booking window, maximum 4-hour reservation duration, facility operating hours limits, and mandatory administrator approval. Newly submitted requests enter **Pending** status and do not block the timeslot until approved by an administrator.

![Basic User reservation form](documentation/screenshots/basic-user-reservation-form.png)

*Figure 10. Reservation submission modal form for Computer Laboratory B201 displaying policy guidelines and input fields.*

#### My Reservations and Cancellation (U4)

Basic users view and track their own reservation requests on the "My Reservations" page (`/reservations/my-reservations/`). Bookings are presented as individual ticket cards displaying the ticket number, facility, event title, date, time window, location, participant count, purpose description, current status (**Pending**, **Approved**, or **Completed**), and administrator remarks. For pending or approved reservations whose start time is in the future, a "Cancel" action is available. Basic users can only access their own reservation records.

![Basic User my reservations](documentation/screenshots/basic-user-my-reservations.png)

*Figure 11. Basic User reservation tracking cards displaying Pending, Approved, and Completed tickets with pre-start cancellation buttons.*

Clicking "Cancel" on an eligible ticket opens an interactive confirmation dialog requiring user confirmation.

![Basic User cancellation confirmation modal](documentation/screenshots/basic-user-cancellation-modal.png)

*Figure 12. Reservation cancellation confirmation modal dialog prompt.*

Upon confirmation, the reservation is updated to **Cancelled** status, releasing the scheduled slot, and the user interface displays a green success confirmation banner.

![Basic User cancellation result](documentation/screenshots/basic-user-cancellation-result.png)

*Figure 13. Reservation cancellation workflow result displaying success confirmation banner and Ticket #18 in Cancelled status.*

Basic Users cannot approve requests, reschedule an Approved booking, create closures, check in events, or mark completion.

### Administrator Features

| ID | Feature | What it does |
|---|---|---|
| A1 | Account management | List, search, activate, and deactivate basic-user accounts; view reservation history. Deactivation blocks new sign-ins and transactions without deleting records. |
| A2 | Facilities and amenities | Create, view, update, and archive categories, facilities, and amenities (unique facility code, name, location, capacity, description, operating hours). Past reservations keep their facilities. |
| A3 | Request review and approval | Searchable, paginated queue; approve or reject with actor, timestamp, and reason. Approval rechecks conflicts atomically. |
| A4 | Calendar and rescheduling | Daily/weekly facility schedule with status labels; reschedule an Approved booking with a reason, retaining the original time in history. A failed reschedule leaves the original reservation intact. |
| A5 | Event monitoring and completion | Record check-in, actual start/end, completion, no-show, and incident notes; print a reservation slip. |
| A6 | Closure periods | Create, edit, and archive closure blocks per facility; closures cannot overlap Approved or Checked In bookings. |
| A7 | Dashboard and reports | Live cards (pending requests, upcoming bookings, completed events, active facilities, total booked hours), monthly booking and facility-usage charts, and date-filtered reservation and utilization reports with CSV export. |
| A8 | Audit history and booking settings | Searchable audit log of approvals, rejections, cancellations, rescheduling, check-in, completion, no-show, closures, and master-data changes; configurable maximum event duration and advance-booking window. |

#### Admin Dashboard and Analytics (A7)

The custom administrative dashboard (`/manage/`) provides operational visibility through real-time KPI statistic cards (Pending Requests, Upcoming Bookings, Completed Events, Active Facilities, Total Booked Hours) and analytical visualizations including a 6-month monthly reservations chart and a top-facility utilization breakdown. Metrics dynamically reflect database state changes as administrators approve, reject, or complete reservations.

![Admin dashboard](documentation/screenshots/admin-dashboard.png)

*Figure 14. Administrator dashboard with KPI statistics cards and analytical charts.*

![Admin dashboard updated state](documentation/screenshots/admin-dashboard-updated.png)

*Figure 15. Administrator dashboard reflecting updated live metrics following reservation processing.*

#### Account Management and Reservation History (A1)

Administrators manage basic-user accounts at `/manage/users/`. The interface provides a text search filter (by username, full name, or email) and displays account status badges. Administrators can deactivate accounts to prevent sign-ins and new bookings while preserving historical records, and navigate to individual user reservation histories via "View History".

![Admin account management](documentation/screenshots/admin-account-management.png)

*Figure 16. Administrator basic-user account management table and status controls.*

Administrators can inspect a specific user's complete booking history by clicking "View History" in the account table, which opens the Reservation History modal dialog displaying all past, active, and terminal reservation records for that account.

![Administrator user reservation history modal](documentation/screenshots/admin-user-reservation-history-modal.png)

*Figure 17. User reservation history modal dialog displaying past records for user andrea.reyes.*

#### Facility, Category, and Amenity Management (A2)

Administrators manage physical campus resources across three dedicated modules: facilities (`/manage/facilities/`), categories (`/manage/categories/`), and amenities (`/manage/amenities/`). Facilities track unique alphanumeric codes, categories, physical locations, capacities, operating hours, and active statuses. Categories and amenities feature descriptions, linked facility counts, and archive controls that preserve historical associations with past reservations without cascading deletions.

![Admin facility management](documentation/screenshots/admin-facility-management.png)

*Figure 18. Facility catalog administration table with codes, operating hours, capacity, and edit controls.*

Clicking "+ Add New Facility" opens a modal creation form to configure the facility code, name, category, physical location, capacity, and operating hours. Supplementary captures of the facility edit modal and update confirmation alert are cataloged in `documentation/screenshot-index.md`.

![Administrator add facility modal form](documentation/screenshots/admin-facility-add-modal.png)

*Figure 19. Add New Facility modal dialog with operating hours and capacity configuration.*

![Admin category management](documentation/screenshots/admin-category-management.png)

*Figure 20. Facility category administration table with descriptions, linked facility counts, and archive controls.*

Clicking "+ Add New Category" opens a modal creation dialog allowing administrators to define the category name and description before activating it for facility classification.

![Administrator add category modal form](documentation/screenshots/admin-category-add-modal.png)

*Figure 21. Add New Category modal dialog with name and description configuration.*

![Admin amenity management](documentation/screenshots/admin-amenity-management.png)

*Figure 22. Facility amenity administration table with active status badges and archive controls.*

Clicking "+ Add New Amenity" opens a modal creation dialog allowing administrators to define the amenity name and description before associating it with facilities.

![Administrator add amenity modal form](documentation/screenshots/admin-amenity-add-modal.png)

*Figure 23. Add New Amenity modal dialog with name and description configuration.*

#### Reservation Review Queue and Approval (A3)

The reservation management queue (`/manage/reservations/`) provides a centralized interface for reviewing submitted booking requests. The queue supports search by keyword, multi-status filtering (All Statuses, Pending, Approved, Rejected, Cancelled), facility filtering, date filtering, and pagination. Administrators can approve pending requests or reject them with a mandatory recorded rejection reason. Approval atomically re-validates schedule conflicts and capacity rules within a database transaction.

![Admin reservation queue](documentation/screenshots/admin-reservation-queue.png)

*Figure 24. Administrator reservation review queue with search, status filters, and paginated records.*

Selecting "Approve" opens an approval decision dialog prompting the administrator for an approval reason before committing the approval atomically. Supplementary captures of the status change audit timeline are cataloged in `documentation/screenshot-index.md`.

![Administrator reservation approval modal](documentation/screenshots/admin-reservation-approve-modal.png)

*Figure 25. Reservation approval decision modal dialog prompting for approval reason.*

Selecting "Reject" opens a rejection decision dialog requiring the administrator to record a mandatory rejection reason before confirming the terminal rejection.

![Administrator reservation rejection modal](documentation/screenshots/admin-reservation-reject-modal.png)

*Figure 26. Reservation rejection decision modal dialog with mandatory rejection reason textarea.*

#### Reservation Calendar and Rescheduling (A4)

The administrative calendar (`/manage/calendar/`) provides daily and weekly schedule views. The weekly interface visualizes facility availability through timeline bars indicating free vs. booked periods across operating hours. Below the timeline, scheduled reservations for the selected date are listed with facility, event title, reserving user, approved status, and action buttons for "Details" and "Reschedule". Rescheduling an approved booking requires a mandatory reason, revalidates conflicts atomically, and retains the original schedule in audit history.

![Admin reservation calendar](documentation/screenshots/admin-reservation-calendar.png)

*Figure 27. Weekly reservation calendar with facility availability timeline bars, approved bookings list, and Reschedule action buttons.*

Clicking "Reschedule" for an approved reservation on the calendar opens a dedicated modal dialog allowing administrators to adjust the start and end times with a mandatory recorded reason.

![Administrator reservation rescheduling modal](documentation/screenshots/admin-reschedule-modal.png)

*Figure 28. Approved reservation rescheduling modal form with datetime selectors and reason input.*

#### Event Monitoring, Check-In, and Completion (A5)

The event monitoring module (`/manage/events/`) supports operational tracking for approved bookings on the day of the event. The interface displays scheduled events with facility, event purpose, reserving user, start/end times, and status. Administrators can access event operations via "View Event" to record attendee check-in during the valid scheduled window (`start_time <= now < end_time`), log event completion with actual timestamps (`actual_end >= actual_start`), record no-shows after the scheduled end time (`now >= end_time`), log event incidents, or generate a printable reservation slip via "Print Slip".

![Admin event monitoring](documentation/screenshots/admin-event-monitoring.png)

*Figure 29. Administrator daily event monitoring schedule with View Event and Print Slip action buttons.*

![Admin event details](documentation/screenshots/admin-event-actions.png)

*Figure 29a. Administrator event details page (View Event) for an approved reservation.*


#### Facility Closure Management (A6)

Administrators manage maintenance shutdowns and institutional closures at `/manage/closures/`. The interface lists active closures displaying facility, start/end timestamps, maintenance reason (e.g., electrical servicing, equipment maintenance, safety inspection), creator attribution, and status. Closures cannot overlap approved or checked-in bookings. Active closures can be edited or archived via dedicated POST actions without permanently deleting historical records.

![Admin closure management](documentation/screenshots/admin-closure-management.png)

*Figure 30. Facility closure management table with scheduled closure blocks, reasons, creator attribution, and archive controls.*

Clicking "+ Add New Closure" opens a modal dialog to define the facility, start datetime, end datetime, and closure reason, with an interactive "Preview Conflicts" action to check against existing approved bookings before saving.

![Administrator add closure modal form](documentation/screenshots/admin-closure-add-modal.png)

*Figure 31. Add New Closure modal dialog with datetime range, reason, and conflict preview.*

#### Reports and Utilization Analytics (A7)

The reporting interface (`/manage/reports/`) delivers operational summaries and facility utilization analytics. Administrators can filter by date range, status, and facility. The report provides summary metric cards (Total Reservations, Approved Count, Completed Count, Booked Hours), a Facility Utilization Report table with booked hours and completed event counts, and a filtered reservation records table. Administrators can export reports via "Export Reservations CSV" and "Export Utilization CSV".

![Admin reports and analytics](documentation/screenshots/admin-reports-analytics.png)

*Figure 32. Reservation reports and utilization analytics dashboard with filter controls and CSV export triggers.*

Exported CSV files provide structured operational records for reservations and facility utilization, suitable for offline reporting and spreadsheet auditing.

![Exported reservation and utilization CSV spreadsheets](documentation/screenshots/admin-reports-csv-spreadsheets.png)

*Figure 33. Exported reservation report and facility utilization CSV spreadsheets viewed in an editor.*

#### Administrative Audit History (A8)

The audit log interface (`/manage/audit-logs/`) provides a searchable, filterable record of administrative actions and critical system state changes. Filters allow searching by keyword, action type, and date range. Recorded action types are Create, Update, Archive, Reactivate, Approve, Reject, Cancel, Check In, Complete, No Show, and Other. The table records log ID, timestamp, performing actor (`admin_user`), action verb, affected model (e.g., `FacilityClosure`, `Reservation`), object ID, and descriptive action summaries.

![Admin audit logs](documentation/screenshots/admin-audit-logs.png)

*Figure 34. Searchable and filterable administrative audit log tracking entity actions and state changes.*

#### Booking Policy Settings (A8)

Administrators configure reservation policies at `/manage/settings/`. The form allows updating the Maximum Booking Duration (in hours) and Advance Booking Window (in days). The interface displays the current active configuration, last updated timestamp, and the updating administrator attribution.

![Admin booking settings](documentation/screenshots/admin-booking-settings.png)

*Figure 35. System settings configuration form for maximum booking duration and advance booking window.*

### Access Rules

- One authentication system with role-based redirects: admins go to `/manage/`, basic users to `/portal/`.
- Registration cannot select the admin role; profile editing exposes name and contact fields only.
- Basic-user records are scoped to the signed-in owner; protected actions check that the account is active.
- State-changing actions use POST with CSRF protection.
- Admin accounts are identified by Django's `is_staff` flag. The sample administrators (`admin_adrian`, `admin_sofia`) are created by `python manage.py seed_demo`. Registration and the admin interface cannot create or promote administrators, and Django's admin site is not installed. To create an additional administrator, run `python manage.py createsuperuser` after migrations have been applied; the account signs in and is redirected to `/manage/`.

---
## System Option Evaluation and Recommendation

### Evaluation Basis

The system requirements are documented in the Project Overview and Feature List, while the applicable booking constraints are summarized in Business Rules Summary. The following comparison evaluates two possible approaches against those documented needs.

### Comparison of Suitable Options

| Criterion | Option 1: Spreadsheet-Based Reservation Process | Option 2: Custom Django Web Application |
|---|---|---|
| Reservation handling | Requests and schedules are maintained through a manual process. | Users submit requests through the application, and administrators process them through a dedicated workflow. |
| Booking validation | Administrators must consistently check facility capacity, operating hours, and scheduling conflicts. | The application validates reservation data and checks conflicts through its booking and approval logic. |
| Access control | Access depends on spreadsheet permissions and the surrounding manual process. | The application separates Basic User and Admin access through authentication and role checks. |
| Decision history | Approval decisions and changes must be recorded consistently through the manual process. | Reservation history and audit records provide traceability for supported actions. |
| Reporting | Reports require spreadsheet formulas, preparation, or manual consolidation. | Administrative reports and CSV exports are available within the application. |
| Maintenance | Requires maintaining the spreadsheet, its permissions, and the accuracy of manually entered records. | Requires maintaining application dependencies, configuration, database records, backups, and tests. |

### Recommendation

The custom Django application is the preferred option for the requirements addressed by CFRS because it brings reservation requests, validation, administrative decisions, scheduling, history, and reporting into one system.

A spreadsheet-based process may be simpler for a small operation with limited workflow requirements. However, the implemented application's dedicated access controls, booking rules, and administrative workflows better align with the stated project requirements.

This is a qualitative evaluation based on the documented requirements and implemented features. It is not a claim that a formal user study, performance comparison, or commercial product evaluation was conducted.

## Technology Stack

| Area | Technology |
|---|---|
| Language | Python (tested on 3.12 and 3.14; Django 6.1 supports 3.12–3.14) |
| Framework | Django 6.1.1 (pinned in `requirements.txt`) |
| Supporting packages | `asgiref`, `python-dotenv`, `sqlparse` |
| Database | SQLite (`db.sqlite3`) |
| UI | Django templates, HTML, CSS, vanilla JavaScript; Google Fonts and Font Awesome loaded from CDNs |
| Authentication | Django authentication with custom role checks |
| Time zone | `Asia/Manila` |
| Version control | Git / [GitHub repository](https://github.com/M31ZY00/IT401W-Campus-Facility-Reservation) |

### Third-Party Packages and Justification

| Package | Version | Why it is used |
|---|---|---|
| `Django` | 6.1.1 | Web framework, ORM, migrations, authentication. |
| `asgiref` | 3.12.1 | Django dependency. |
| `python-dotenv` | 1.2.4 | Loads `DJANGO_SECRET_KEY` from a local `.env` file so secrets stay out of source control. |
| `sqlparse` | 0.6.0 | Django dependency. |
| Font Awesome (CDN) | 6.4.0 | Interface icons, loaded from cdnjs; not installed through `requirements.txt`. |
| Google Fonts: Cinzel, Plus Jakarta Sans (CDN) | n/a | Display and body typefaces, loaded from Google Fonts; not installed through `requirements.txt`. |

None of these packages generate the custom admin side.

Django 6.1 supports Python 3.12, 3.13, and 3.14.

---



### Environment Variables

| Variable | Required | Purpose |
|---|---|---|
| `DJANGO_SECRET_KEY` | Yes | Django secret key. Read from the environment or a local `.env` file. Never commit it. |

### Demonstration Data

`python manage.py seed_demo` creates fictional records only. On a fresh database it creates 2 administrators (`admin_adrian`, `admin_sofia`), 8 basic users, 3 categories, 6 facilities, 8 amenities, 5 closure blocks, 24 reservations (6 approved, 5 completed, 5 pending, 3 no-show, 3 rejected, 2 cancelled), 8 event records, 2 incidents, 56 reservation-history entries, and 37 audit entries. Running it again does not change these counts. The seeded schedule includes one back-to-back pair of approved bookings at the same facility (09:00–10:00 and 10:00–11:00 on the day after seeding), and the command verifies that an overlapping duplicate approval is rejected. The command prompts for a password of at least 12 characters and reuses it for the sample accounts it creates; existing accounts keep their passwords.


### Main Routes

| Path | Purpose |
|---|---|
| `/` | Login page for visitors; signed-in users are redirected by role |
| `/auth/` | Authentication routes (`register/`, `profile/`, `logout/`) |
| `/facilities/` | Public facility catalog; `/facilities/<id>/` facility detail |
| `/portal/` | Basic User portal |
| `/reservations/create/<facility_id>/` | Submit a reservation request (Basic User) |
| `/reservations/my-reservations/` | Signed-in user's reservations |
| `/reservations/cancel/<id>/` | Cancel own reservation (POST only) |
| `/manage/` | Administrator dashboard |
| `/manage/users/` | Basic-user accounts and per-user reservation history |
| `/manage/facilities/`, `/manage/categories/`, `/manage/amenities/` | Master-data management (add, edit, toggle status) |
| `/manage/reservations/` | Review queue; status updates, history, and rescheduling per reservation |
| `/manage/calendar/` | Administrator reservation calendar |
| `/manage/events/` | Event monitoring; event detail, incident reporting, and printable slip per reservation |
| `/manage/closures/` | Closure periods (add, edit, archive) |
| `/manage/reports/` | Reports, with reservation and utilization CSV export |
| `/manage/audit-logs/` | Audit log |
| `/manage/settings/` | Booking policy settings |

---

## Business Rules Summary

1. Time intervals are half-open, `[start, end)`. Two intervals conflict when A starts before B ends and A ends after B starts; adjacent bookings may meet at the same endpoint.
2. Pending requests do **not** reserve a slot. Approved, Checked In, Completed, and No Show reservations block overlapping intervals, as do active closures. Cancelled and Rejected reservations release their slots.
3. Approval and rescheduling run inside a database transaction with a locking strategy and revalidate the booking rules.
4. A booking must fit within one local day and the facility's operating hours. The start must be in the future, the end after the start, and participants between 1 and the facility capacity.
5. Defaults: maximum event duration **4 hours**, advance-booking window **30 calendar days**, both configurable by an admin (allowed range: 1–24 hours and 1–365 days). Times use `Asia/Manila`.
6. No Show can be recorded only after the scheduled end for a booking with no check-in. Actual end cannot precede actual start.
7. A closure cannot overlap an Approved or Checked In booking; the booking must first be rescheduled or cancelled with a reason.
8. Out of scope: payments, deposits, catering, recurring bookings, overnight events, external organizer roles, and automated email/SMS notifications.

### Status Workflow

```
Pending  → Approved | Rejected | Cancelled
Approved → Checked In | No Show | Cancelled   (rescheduling keeps status Approved)
Checked In → Completed
```

Terminal states (Rejected, Cancelled, Completed, No Show) cannot be reopened. Administrator status changes follow a fixed transition table that requires a specific current status, re-checked inside the database transaction, and owner cancellation is limited to Pending or Approved bookings. No transition leads out of a terminal state, and rescheduling applies to Approved bookings only.

---

## System Diagrams

The diagrams describe the systems' entity relations, workflows and architecture.

| # | Diagram | Description | Image File |
|---|---|---|---|
| 1 | Application Architecture (Django MTV) | Request pipeline, active middleware, role guards, views, services, ORM, templates, and SQLite database | [`documentation/diagrams/01_architecture_mtv.png`](documentation/diagrams/01_architecture_mtv.png) |
| 2 | ERD — Facility Catalog, Amenities, and Closures | Facility categories, facilities (DB-level nullability vs model clean), amenities, M:N junction, and closures | [`documentation/diagrams/02_erd_catalog_closures.png`](documentation/diagrams/02_erd_catalog_closures.png) |
| 3 | ERD — Reservations, History, and Event Monitoring | Reservations, change history, 1:1 event records, event incident reporting, and actor associations | [`documentation/diagrams/03_erd_reservations_events.png`](documentation/diagrams/03_erd_reservations_events.png) |
| 4 | ERD — Identity, User Profiles, Audit Logs, and Settings | User accounts, 1:1 profile, required admin_user audit logs, and singleton system settings | [`documentation/diagrams/04_erd_identity_audit_settings.png`](documentation/diagrams/04_erd_identity_audit_settings.png) |
| 5 | Workflow — Reservation Request Submission | Form inputs, validation rules, non-blocking Pending status, and owner cancellation | [`documentation/diagrams/05_workflow_request_submission.png`](documentation/diagrams/05_workflow_request_submission.png) |
| 6 | Workflow — Administrator Decision and Approval | Decision paths, mandatory rejection reasons, transaction-based approval, revalidation, rollback, SQLite locking limitations, and database-conflict handling | [`documentation/diagrams/06_workflow_approval_decision.png`](documentation/diagrams/06_workflow_approval_decision.png) |
| 7 | Workflow — Reservation Lifecycle: Cancellation, Rescheduling, and Events | Pre-start cancellation, rescheduling validation, check-in window, completion, no-show, and incidents | [`documentation/diagrams/07_workflow_reservation_lifecycle.png`](documentation/diagrams/07_workflow_reservation_lifecycle.png) |
| 8 | Workflow — Facility Closure Management | Form fields, new-only future-start rule, conflict checks, and dedicated POST archive action | [`documentation/diagrams/08_workflow_closure_management.png`](documentation/diagrams/08_workflow_closure_management.png) |

---

### 1. Application Architecture (Django MTV)

![1. System Architecture - Django Model-Template-View (MTV)](documentation/diagrams/01_architecture_mtv.png)

*Source-level architecture depicting the active middleware stack (`Security`, `Session`, `Common`, `CsrfView`, `Authentication`, `Message`, `XFrameOptions`), root URL dispatch via `HomeLoginView` with role-based redirects, access guards (`basic_user_required`, `admin_required`, `administrator_required`), direct view queries, and the service layer. `update_reservation` handles approve, reject, admin cancel, check-in, complete, and no-show; `reschedule_reservation` handles date and time changes; `record_audit` writes audit entries. Owner cancellation by a Basic User is the exception: it runs in `reservations/views.py` with its own transaction and calls `record_audit` directly rather than going through the services. The diagram also shows the template layer and the SQLite backend.*

---

### 2. ERD — Facility Catalog, Amenities, and Closures

![2. ERD - Facility Catalog, Amenities, and Closures](documentation/diagrams/02_erd_catalog_closures.png)

*Data model representing facility categories, facilities, amenities, and closure blocks. Accurately reflects database-level nullability (`category_id` and `code` nullable in the schema, enforced non-empty by `Facility.clean()`), M:N table `facilities_facility_amenities`, and `PROTECT` foreign key constraints.*

---

### 3. ERD — Reservations, History, and Event Monitoring

![3. ERD - Reservations, History, and Event Monitoring](documentation/diagrams/03_erd_reservations_events.png)

*Core reservation data structures illustrating `Reservation` records, audit trail tracking in `ReservationChange` (`CASCADE`), 1:1 `EventRecord` with check-in/completion/no-show timestamps, and `EventIncident` logs linked via foreign keys with `PROTECT` actor references.*

---

### 4. ERD — Identity, User Profiles, Audit Logs, and System Settings

![4. ERD - Identity, User Profiles, Audit Logs, and System Settings](documentation/diagrams/04_erd_identity_audit_settings.png)

*Supporting data models for identity and administration. Emphasizes that `AuditLog.admin_user` is a required non-nullable foreign key (recording both admin actions and basic-user cancellations), `UserProfile` is 1:1 with `auth.User`, and `SystemSetting` operates as a convention singleton (`pk=1`) with nullable `updated_by` (`SET_NULL`).*

---

### 5. Workflow — Reservation Request Submission

![5. Workflow - Reservation Request Submission](documentation/diagrams/05_workflow_request_submission.png)

*Basic user booking process: input capture (`event_title`, `purpose`, `participant_count`, `start_time`, `end_time`), model validation (event title required, `start_time > now`, same local day in `Asia/Manila`, operating hours, duration limit, advance window, capacity, active category/facility, no closure conflicts), initial `Pending` status without reserving slots, and owner cancellation before start time. Database-lock handling for user reservation submission (F-06) is fixed;*

---

### 6. Workflow — Administrator Decision and Approval

![6. Workflow - Administrator Decision and Approval](documentation/diagrams/06_workflow_approval_decision.png)

*Administrative review flow: a mandatory rejection reason (the reservation must be Pending) with audit tracking, or approval within a database transaction. The service performs a Facility UPDATE using `F('is_active')`, retrieves the reservation using `select_for_update()`, re-checks that its status is still Pending, and revalidates through `full_clean()`. `select_for_update()` does not provide row-level locking on SQLite; the Facility UPDATE is what makes competing approvals queue on SQLite. If the database stays locked past SQLite's wait (about 5 seconds), the approval view catches the database error, shows "database conflict, please try again", and leaves the reservation Pending. In threaded tests on a file-based SQLite database, two simultaneous approvals of overlapping bookings produced exactly one approval in all 10 rounds. See [Testing](#testing) and [Limitations and Enhancements](#limitations-and-enhancements).*

---

### 7. Workflow — Reservation Lifecycle: Cancellation, Rescheduling, and Events

![7. Workflow - Reservation Lifecycle: Cancellation, Rescheduling, and Events](documentation/diagrams/07_workflow_reservation_lifecycle.png)

*Post-approval operational workflows: pre-start cancellation releasing timeslots (a Basic User may cancel their own Pending or Approved booking; an admin cancels an Approved booking with a required reason), administrative rescheduling with full conflict revalidation, check-in restricted to the scheduled time window (`start_time <= now < end_time`), event completion requiring valid check-in with `actual_end >= actual_start`, post-end no-show recording (`now >= end_time`), and optional incident logging for checked-in, completed, or no-show bookings. Each status change is recorded in `ReservationChange` and the audit log.*

---

### 8. Workflow — Facility Closure Management

![8. Workflow - Facility Closure Management](documentation/diagrams/08_workflow_closure_management.png)

*Closure maintenance lifecycle: form inputs (`facility`, `start_time`, `end_time`, `reason`), model validation where the future-start check (`start_time > now`) applies strictly to new closures, overlap checks with existing active closures and approved/checked-in bookings (excluding pending requests), and a dedicated POST action to archive active closures without deletion.*

---

## Testing

### Database / Backend Tests

Run the Django test suite with:

```bash
python manage.py test -v 2
```

The `main` branch contains **160 automated tests** across eight test modules. 153 run in a normal `python manage.py test`; the 7 concurrency tests (`reservations/test_concurrency.py`) skip themselves unless run with `--settings=config.settings_concurrency`, on a temporary SQLite file. The latest full run reported 161 tests in about 103 seconds: OK, 7 skipped, and the concurrency tests passed when run separately. After the F-06 fix, a full run reported 161 tests in about 104 seconds: OK, 7 skipped.

**Supplementary tests (pending merge into `main`):**
- Nine boundary-value tests (`test_supplementary_boundaries.py`) were recorded in the Boundary Value Test Results.

**Competing approvals (Business Rule 3):** On a file-based SQLite database, two admins approving overlapping bookings at the same moment resulted in exactly one approval in all 10 repeated rounds, with no database lock error, and up to 30 simultaneous bookings were saved without errors. These results come from threads on a single machine; they do not cover browsers, heavier load, simultaneous rescheduling, or PostgreSQL.

**F-06 — Fixed** `create_reservation` previously had no database-lock handling, so a user submitting a booking while SQLite stayed locked (about 5 seconds) saw an error page. TC_095 reproduced this. The fix shows "The reservation could not be saved due to a database conflict. Please try again." and saves nothing. TC_095, TC_098 and TC_099 pass. Keep the issue open until the branch is merged.

### Browser Behavior Tests

Browser behavior is evaluated through **manual testing**, rather than automated Playwright or Selenium tests. The test cases cover navigation, buttons, forms, reservation workflows, administrator actions, responsive layouts, printing, and exporting.

The recorded browser test report contains **13 test cases: 12 passed and 1 failed**. Its failed case, TC_110, documented the unstyled Admin Event Details page. The styling and Back-button navigation issues were subsequently addressed under **Issue #7** which was **Resolved and informally tested.** Because TC_110 has not been re-run in the attached report, the recorded 12/13 result remains historical and should not be treated as an updated regression result.

Screenshots provide supporting evidence where appropriate, but cannot independently prove every functional behavior.

These tests cover specified scenarios and do not exhaust all possible browser interactions or guarantee that the application is defect-free.

### Test Results

- [Boundary Value and Concurrency Test Results](documentation/testing/Boundary_Value_Test_Results.docx)
- [Browser Behavior Test Results](documentation/testing/Browser_Behavior_Test_Results.docx)
- [Database Backend Testing Results](documentation/testing/Database_Backend_Testing_Results.docx)
- [Following Database Backend Testing Results (Final)](documentation/testing/Database_Backend_Testing_Results3.docx)

> **Note:** The results above reflect the recorded test runs. Update the totals if subsequent executions produce different results.

**Test Case List:** [List of Documented Test Cases](documentation/testing/Master_Test_Case_List.xlsx)

## Evidence Index


| Area | Evidence | Location |
|---|---|---|
| User needs | Requirements and constraints | [Project Overview and Feature List](#project-overview-and-feature-list) · [Business Rules Summary](#business-rules-summary) |
| User needs | Two-option comparison and recommendation | [System Option Evaluation and Recommendation](#system-option-evaluation-and-recommendation) |
| User needs | Maintenance guidance | [Maintenance Guide](#maintenance-guide) |
| User needs | Enhancements made in response to feedback | Tester findings in [`Database_Backend_Testing_Results.docx`](documentation/testing/Database_Backend_Testing_Results.docx); [Enhancements](#limitations-and-enhancements) |
| User needs | Maintenance guidance | [`INSTALL.md`](INSTALL.md) 11–12 (setup troubleshooting and security notes only) |
| System | MTV, database, and workflow diagrams | [System Diagrams](#system-diagrams) · `documentation/diagrams/` |
| System | Requirements and constraints; limitations; resolved issues | [Business Rules](#business-rules-summary) · [Limitations](#limitations-and-enhancements) |
| System | Standards, legal compliance, and ethical issues | [Standards, Privacy, and Ethics](#standards-privacy-and-ethics) |
| Technology | Tool justification; Django, ORM, reusable components | [Technology Stack](#technology-stack) |
| Technology | Version control and configuration records | [GitHub repository](https://github.com/M31ZY00/IT401W-Campus-Facility-Reservation) · [PR #6](https://github.com/M31ZY00/IT401W-Campus-Facility-Reservation/pull/6) · `requirements.txt` · `.env.example` |
| Technology | Testing records | [Testing](#testing) · `documentation/testing/` ( result reports and the Master Test Case List) |
| Technology | Emerging-technology evaluation and adoption recommendation | — |
| Team | Allocations, collaboration records, individual contributions, peer feedback | [Project Team](#project-team) (roles filled; modules and documents pending) |
| Communication | Technical setup documentation | [`INSTALL.md`](INSTALL.md) |
| Communication | Basic User guide, Admin guide, and screenshot traceability | [`documentation/screenshot-index.md`](documentation/screenshot-index.md) |

---

## Limitations and Enhancements

### Known Limitations

- SQLite is configured. Simultaneous approvals and bookings passed threaded tests on a file-based SQLite database, but simultaneous rescheduling, more than two competing approvals, and real-browser load were not tested; a server database such as PostgreSQL would be more suitable for heavy concurrent use.
- A booking submitted while the database is locked (about 5 seconds) shows an error page rather than a message (open finding F-06, `create_reservation`).
- `DEBUG = True` and `ALLOWED_HOSTS = []` are hard-coded in `config/settings.py`; review them before any deployment beyond local development.
- Templates load Google Fonts and Font Awesome from external CDNs, so some visuals need an internet connection.
- No automated email or SMS notification delivery.
- Availability is displayed in 30-minute intervals, but reservation start and end times are not forced onto 30-minute boundaries.
- Registration shows no privacy notice, and there is no login lockout or password-reset feature.


### Resolved Issues and Pending Fix

| ID | Issue | Status |
|---|---|---|
| F-01 | Missing `.env.example` configuration template for local `DJANGO_SECRET_KEY` setup. | **Fixed** |
| F-02 | Misleading `seed_demo` output claiming existing passwords and linked records were preserved on a fresh database. | **Fixed** |
| F-03 | Unused/duplicate audit-log view function. | **Fixed** |
| F-04 | `dashboard/migrations/_init_.py` has single underscores, so the folder is not a Python package. | **No change needed**; the team confirmed it is harmless. |
| F-05 | Demo seed data could stop having upcoming reservations after the initial day. | **Fixed** |
| Issue #7 | Admin Event Details page styling and Back-button navigation. | **Fixed**; manual regression retest not reflected in the attached browser report |
| F-06 | User reservation submission could fail with an unhandled database-lock error. | **Fixed** re-tested (TC_095, TC_098, TC_099)|

The resolved statuses above reflect the project update.

---

## Standards, Privacy, and Ethics


**Standards.** CFRS was designed with reference to the Philippine Data Privacy Act of 2012 (RA 10173): transparency, legitimate purpose, proportionality, and reasonable security measures for personal data. It is a classroom prototype run with fictional demonstration data.

**Personal data.** CFRS collects only what reservations need: username, name, email, an optional phone number, and a password stored as a Django-hashed value. Reservation records hold the event details and decision reason. Administrators see a user's name, email, and reservation history; CSV exports contain usernames only and neutralize spreadsheet formula characters. Accounts are deactivated rather than deleted, so history and audit records stay intact.

**Access control.** Role checks use `is_staff`. Basic users see and cancel only their own reservations, public registration can only create basic users, and administrators cannot be created or promoted through the interface. State-changing actions use POST with CSRF protection, and administrative actions and user cancellations are recorded in an audit log with the acting account, record, and timestamp. The secret key is kept in a git-ignored `.env` file.

**Accessibility.** All pages declare `lang="en"`, a title, and a responsive viewport. Form fields have labels, dialogs and messages use ARIA roles, focus styles are defined, and animations respect `prefers-reduced-motion`.

**Ethics.** Approvals and rejections record who decided, when, and why, and conflicts are resolved by rule, not discretion. Deactivation and archiving preserve past records.

**Planned improvements.** A privacy notice on registration, login attempt limits, password reset, and deployment hardening (see [Known Limitations](#known-limitations)).

---

## Repository Layout

```
.env.example       template for the local .env file (DJANGO_SECRET_KEY)
main.py            unused IDE sample script (not part of the application)
config/            project settings and root URLs
authentication/    registration, login, profile, role guards
dashboard/         Basic User portal
facilities/        categories, facilities, amenities, closures, public catalog
reservations/      reservations, change history, event records, services, user booking views
management/        custom admin views, audit log, system settings, reports, seed command
static/            CSS used by the templates
documentation/     diagrams, screenshots, screenshot index, and documentation evidence
```

## Contributing and Version Control

#### Contributing

Contributions from project team members followed the existing project structure and coding conventions.

1. Obtain access to the project repository.
2. Create a working branch for the change.
3. Implement the change within the intended scope.
4. Run the relevant automated tests and verify affected functionality.
5. Review the changes before committing.
6. Submit the changes through a pull request for review and integration into the main branch.

Do not commit environment files containing secrets, local database files, virtual environments, or other generated development artifacts. Refer to `.gitignore` and the project setup instructions for the applicable exclusions.

#### Version Control

The project source code and related documentation are maintained in Git. The repository hosted on GitHub serves as the shared version-controlled source.

Changes should be committed with descriptive messages. Where applicable, use separate branches for individual features, fixes, and documentation updates. Changes intended for integration into the main branch should be reviewed before merging.

For the authoritative implementation and change history, refer to the project's GitHub repository `https://github.com/M31ZY00/IT401W-Campus-Facility-Reservation`.

> **Evidence basis:** The functional requirements and system constraints
> in this section are derived from the project scope, existing
> documentation, and the implemented application. The comparison of
> alternative approaches is a qualitative evaluation against these
> requirements, not a claim that a formal user study or product
> comparison was conducted. The maintenance guide provides recommended
> procedures for the current project configuration; it does not
> represent an existing institutional maintenance program.

## License and Acknowledgments

**Project license:** None specified. This project was produced as an academic submission for IT401W, and no permission is granted for reuse, modification, or redistribution beyond what the hosting platform's terms allow.

**Third-party assets:** No third-party images, fonts, scripts, or stylesheet files are bundled in the repository. Two external assets are loaded at runtime from CDNs:

- Font Awesome 6.4.0 (Free styles) for interface icons, loaded from cdnjs.
- Google Fonts (Cinzel and Plus Jakarta Sans) for typography.

The Python dependencies pinned in `requirements.txt` are listed under [Technology Stack](#technology-stack).