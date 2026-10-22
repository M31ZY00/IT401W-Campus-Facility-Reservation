# CFRS Screenshot Traceability Index and Requirement Mapping

This document provides a comprehensive mapping between Campus Facility Reservation System (CFRS) interface screenshots, project requirements, and their presentation within the project documentation.

---

## 1. Traceability and Mapping Table

| Original filename | Current filename | Requirement ID | Feature shown | README location | Evidence status |
|---|---|---|---|---|---|
| `Screenshot 2026-10-23 052524.png` | `public-facility-directory.png` | U2 | Unauthenticated public visitor facility catalog with search filters, facility details, and Login to Reserve action buttons | Figure 1 (Public Visitor section) | Interface demonstration |
| `Screenshot 2026-10-22 223646.png` | `basic-user-sign-in.png` | U1 | Unified authentication sign-in form with username/password inputs, Log In action, and registration link | Figure 2 (Basic User section) | Interface demonstration |
| `Screenshot 2026-10-22 215006.png` | `basic-user-registration-step1.png` | U1 | Multi-step registration wizard Step 1 (Personal details: First Name, Last Name, Next action) | Figure 3 (Basic User section) | Interface demonstration |
| `Screenshot 2026-10-23 051643.png` | `basic-user-registration-step2.png` | U1 | Multi-step registration wizard Step 2 (Contact details: Email Address, Contact Number, Back/Next actions) | Figure 4 (Basic User section) | Interface demonstration |
| `Screenshot 2026-10-23 051706.png` | `basic-user-registration-step3.png` | U1 | Multi-step registration wizard Step 3 (Account credentials: Username, Password, Confirm password, Create Account action) | Figure 5 (Basic User section) | Interface demonstration |
| `Screenshot 2026-10-22 215218.png` | `basic-user-dashboard.png` | U1 | Authenticated basic user portal dashboard with personalized greeting and primary action cards | Figure 6 (Basic User section) | Interface demonstration |
| `Screenshot 2026-10-22 215225.png` | `basic-user-profile.png` | U1 | Profile modal dialog displaying read-only username and editable contact details (name, email, phone) | Figure 7 (Basic User section) | Interface demonstration |
| `Screenshot 2026-10-22 215237.png` | `basic-user-facility-catalog.png` | U2 | Facility catalog browsing with search, capacity filter, facility details, and amenities checklist (authenticated Basic User session) | Figure 8 (Basic User section) | Interface demonstration |
| `Screenshot 2026-10-22 215302.png` | `basic-user-facility-availability.png` | U2 | Facility 30-minute availability schedule grid for Computer Lab B201 showing unavailable status badges | Figure 9 (Basic User section) | Interface demonstration |
| `Screenshot 2026-10-22 215318.png` | `basic-user-reservation-form.png` | U3 | Reservation request modal form showing booking policy constraints, event title, purpose, capacity, and datetime selectors | Figure 10 (Basic User section) | Interface demonstration |
| `Screenshot 2026-10-22 215339.png` | `basic-user-my-reservations.png` | U4 | My Reservations ticket cards displaying Pending, Approved, and Completed bookings with pre-start Cancel buttons | Figure 11 (Basic User section) | Interface demonstration |
| `Screenshot 2026-10-22 215451.png` | `basic-user-cancellation-modal.png` | U4 | Cancellation confirmation modal dialog for Ticket #10 warning that action cannot be undone | Figure 12 (Basic User section) | Interface demonstration |
| `Screenshot 2026-10-22 215404.png` | `basic-user-cancellation-result.png` | U4 | Post-cancellation confirmation banner and Ticket #18 updated to Cancelled status with actions disabled | Figure 13 (Basic User section) | Completed workflow |
| `admin-dashboard.png` | `admin-dashboard.png` | A7 | Administrator dashboard with KPI statistics cards and analytical charts (initial baseline state) | Figure 14 (Admin section) | Preserved Admin screenshot |
| `admin-dashboard-updated.png` | `admin-dashboard-updated.png` | A7 | Administrator dashboard reflecting updated live metrics following reservation processing | Figure 15 (Admin section) | Preserved Admin screenshot |
| `admin-account-management.png` | `admin-account-management.png` | A1 | Basic-user account management table with text search, role badges, activation controls, and View History | Figure 16 (Admin section) | Preserved Admin screenshot |
| `Screenshot 2026-10-22 215537.png` | `admin-user-reservation-history-modal.png` | A1 | Account management modal dialog showing reservation history records for basic user `andrea.reyes` | Figure 17 (Admin section) | Interface demonstration / Completed workflow |
| `admin-facility-management.png` | `admin-facility-management.png` | A2 | Facility catalog administration table with codes, operating hours, capacity, and edit controls | Figure 18 (Admin section) | Preserved Admin screenshot |
| `Screenshot 2026-10-22 215741.png` | `admin-facility-add-modal.png` | A2 | Add New Facility modal dialog with code, name, category, location, capacity, and operating hours | Figure 19 (Admin section) | Interface demonstration |
| `admin-category-management.png` | `admin-category-management.png` | A2 | Facility category administration table with descriptions, linked facility counts, and archive controls | Figure 20 (Admin section) | Preserved Admin screenshot |
| `Screenshot 2026-10-22 215847.png` | `admin-category-add-modal.png` | A2 | Add New Category modal dialog with category name and description fields | Figure 21 (Admin section) | Interface demonstration |
| `admin-amenity-management.png` | `admin-amenity-management.png` | A2 | Facility amenity administration table with active status badges and archive controls | Figure 22 (Admin section) | Preserved Admin screenshot |
| `Screenshot 2026-10-22 215856.png` | `admin-amenity-add-modal.png` | A2 | Add New Amenity modal dialog with amenity name and description fields | Figure 23 (Admin section) | Interface demonstration |
| `admin-reservation-queue.png` | `admin-reservation-queue.png` | A3 | Administrator reservation review queue with search, multi-status filters, and paginated records | Figure 24 (Admin section) | Preserved Admin screenshot |
| `Screenshot 2026-10-22 215925.png` | `admin-reservation-approve-modal.png` | A3 | Interactive approval decision modal dialog for Reservation #19 with approval reason textarea | Figure 25 (Admin section) | Interface demonstration |
| `Screenshot 2026-10-22 215937.png` | `admin-reservation-reject-modal.png` | A3 | Interactive rejection decision modal dialog for Reservation #17 with mandatory rejection reason textarea | Figure 26 (Admin section) | Interface demonstration |
| `admin-reservation-calendar.png` | `admin-reservation-calendar.png` | A4 | Weekly reservation calendar with facility availability timeline bars, approved bookings list, and Reschedule action buttons | Figure 27 (Admin section) | Preserved Admin screenshot |
| `Screenshot 2026-10-22 220039.png` | `admin-reschedule-modal.png` | A4 | Reservation rescheduling modal dialog for Ticket #9 with date/time pickers and reason input | Figure 28 (Admin section) | Interface demonstration |
| `admin-event-monitoring.png` | `admin-event-monitoring.png` | A5 | Daily event monitoring schedule table with View Event and Print Slip action buttons | Figure 29 (Admin section) | Preserved Admin screenshot |
| `admin-closure-management.png` | `admin-closure-management.png` | A6 | Facility closure management table with scheduled closure blocks, reasons, creator attribution, and archive controls | Figure 30 (Admin section) | Preserved Admin screenshot |
| `Screenshot 2026-10-22 223015.png` | `admin-closure-add-modal.png` | A6 | Add New Closure modal dialog with facility selector, datetime range, reason, and Preview Conflicts action | Figure 31 (Admin section) | Interface demonstration |
| `admin-reports-analytics.png` | `admin-reports-analytics.png` | A7 | Reservation reports and utilization analytics dashboard with filter controls and CSV export triggers | Figure 32 (Admin section) | Preserved Admin screenshot |
| `Screenshot 2026-10-22 223313.png` | `admin-reports-csv-spreadsheets.png` | A7 | Dual spreadsheet view of exported CSV reports (reservation report and facility utilization report) | Figure 33 (Admin section) | Completed workflow |
| `admin-audit-logs.png` | `admin-audit-logs.png` | A8 | Searchable and filterable administrative audit log tracking entity actions and state changes | Figure 34 (Admin section) | Preserved Admin screenshot |
| `admin-booking-settings.png` | `admin-booking-settings.png` | A8 | System settings configuration form for maximum booking duration and advance booking window | Figure 35 (Admin section) | Preserved Admin screenshot |
| `Screenshot 2026-10-22 215458.png` | `basic-user-cancellations-updated.png` | U4 | Post-cancellation reservation tracking showing multiple tickets (#18 and #10) in Cancelled status | Supplementary capture (omitted from README to avoid duplicate cancellation views) | Completed workflow |
| `Screenshot 2026-10-22 215803.png` | `admin-facility-edit-modal.png` | A2 | Edit Facility modal dialog for LAB-Z101 updating physical location | Supplementary capture (omitted from README to avoid redundant modal forms) | Interface demonstration |
| `Screenshot 2026-10-22 215811.png` | `admin-facility-saved-success.png` | A2 | Saved Successfully modal confirmation alert after facility update | Supplementary capture (omitted from README to avoid redundant modal popups) | Completed workflow |
| `Screenshot 2026-10-22 220659.png` | `admin-reservation-history-timeline.png` | A3, A8 | Reservation #21 history modal showing admin decision record and status change audit timeline table | Supplementary capture (omitted from README; provides granular status audit proof in index) | Completed workflow / Interface demonstration |
| *N/A (unresolved)* | `admin-event-actions.png` | A5 | Operational action views (check-in timestamp, completion timestamp, incident report, print slip) | Admin Event Monitoring placeholder | Placeholder |

---

## 2. Requirement Coverage Summary

### Basic User Requirements

- **U1 — Account and profile management:**
  - **Sign-in (`/` or `/auth/`):** Full coverage via `basic-user-sign-in.png` (Figure 2).
  - **Registration (`/auth/register/`):** Full coverage across all three wizard steps via `basic-user-registration-step1.png` (Figure 3, personal details), `basic-user-registration-step2.png` (Figure 4, contact details), and `basic-user-registration-step3.png` (Figure 5, account credentials).
  - **Portal Dashboard (`/portal/`):** Full coverage via `basic-user-dashboard.png` (Figure 6).
  - **Profile Management Modal:** Full coverage via `basic-user-profile.png` (Figure 7) showing read-only username and editable name/contact fields.

- **U2 — Facility browsing and availability:**
  - **Public Visitor Catalog (`/facilities/`):** Full coverage via `public-facility-directory.png` (Figure 1) demonstrating unauthenticated browsing with search filters, facility details, and public login action buttons.
  - **Authenticated Facility Catalog (`/facilities/`):** Full coverage via `basic-user-facility-catalog.png` (Figure 8) demonstrating keyword search, capacity filtering, facility details pane, and equipped amenities checklist within an authenticated Basic User session.
  - **Availability Schedule (`/facilities/`):** Full coverage via `basic-user-facility-availability.png` (Figure 9) depicting 30-minute slot visualization across operating hours with unavailable slots clearly identified.

- **U3 — Reservation request submission:**
  - **Reservation Form Modal:** Full coverage via `basic-user-reservation-form.png` (Figure 10) displaying system policy constraints (30-day window, 4-hour max duration, operating hours limits, mandatory admin approval) alongside event title, purpose description, participant count, and datetime pickers.

- **U4 — View and cancel own reservations:**
  - **My Reservations Ticket List (`/reservations/my-reservations/`):** Full coverage via `basic-user-my-reservations.png` (Figure 11) displaying individual ticket cards across Pending, Approved (with admin remarks), and Completed statuses, with pre-start cancellation buttons.
  - **Cancellation Confirmation Prompt:** Full coverage via `basic-user-cancellation-modal.png` (Figure 12) demonstrating the modal confirmation dialog for Ticket #10.
  - **Post-Cancellation Result:** Full coverage via `basic-user-cancellation-result.png` (Figure 13) showing top green success confirmation alert and Ticket #18 updated to Cancelled status with actions disabled. Additional multi-cancellation verification captured in `basic-user-cancellations-updated.png`.

---

### Administrator Requirements

- **A1 — Account management:** Full baseline coverage via `admin-account-management.png` (Figure 16) and modal history coverage via `admin-user-reservation-history-modal.png` (Figure 17).
- **A2 — Facility, category, and amenity management:** Full baseline coverage via `admin-facility-management.png` (Figure 18), `admin-category-management.png` (Figure 20), and `admin-amenity-management.png` (Figure 22). Add New Facility modal coverage via `admin-facility-add-modal.png` (Figure 19). Add New Category modal coverage via `admin-category-add-modal.png` (Figure 21). Add New Amenity modal coverage via `admin-amenity-add-modal.png` (Figure 23). Supplementary captures for facility editing and update alert are cataloged in the index.
- **A3 — Reservation review and approval:** Full baseline coverage via `admin-reservation-queue.png` (Figure 24). Interactive approval decision modal coverage via `admin-reservation-approve-modal.png` (Figure 25). Interactive rejection decision modal coverage via `admin-reservation-reject-modal.png` (Figure 26). Supplementary status change timeline is cataloged in the index.
- **A4 — Calendar and rescheduling:** Full baseline coverage via `admin-reservation-calendar.png` (Figure 27) and modal rescheduling form coverage via `admin-reschedule-modal.png` (Figure 28).
- **A5 — Event monitoring, check-in, completion, and incident reporting:** Partial baseline coverage via `admin-event-monitoring.png` (Figure 29) showing schedule table and styled action buttons. Operational views (check-in timestamp, completion timestamp, incident reporting, and printable slip) remain an unresolved placeholder (`admin-event-actions.png`), with verified findings on unstyled `event_detail.html` and print CSS in `event_slip.html`.
- **A6 — Closure management:** Full baseline coverage via `admin-closure-management.png` (Figure 30) and modal creation coverage via `admin-closure-add-modal.png` (Figure 31) with Preview Conflicts action.
- **A7 — Dashboard and reports:** Full baseline coverage via `admin-dashboard.png` (Figure 14), `admin-dashboard-updated.png` (Figure 15), and `admin-reports-analytics.png` (Figure 32). Exported CSV spreadsheet coverage via `admin-reports-csv-spreadsheets.png` (Figure 33).
- **A8 — Audit history and booking settings:** Full baseline coverage via `admin-audit-logs.png` (Figure 34) and `admin-booking-settings.png` (Figure 35), supplemented by the timeline audit log in `admin-reservation-history-timeline.png`.

---

## 3. Rationale for Supplementary Captures vs. README Embeds

Four captures are retained in this index as supplementary evidence rather than embedded directly into `README.md`:

1. **`basic-user-cancellations-updated.png` (U4):**
   - *Rationale:* Figure 13 (`basic-user-cancellation-result.png`) already proves the cancellation workflow result, the green success notification banner, and the ticket status update to Cancelled. Embedding this subsequent capture (showing Ticket #10 also cancelled) would provide redundant visual layout without adding new feature demonstration.
2. **`admin-facility-edit-modal.png` (A2):**
   - *Rationale:* Figure 19 (`admin-facility-add-modal.png`) already illustrates the facility configuration form controls. The edit modal repeats the same fields with pre-populated data.
3. **`admin-facility-saved-success.png` (A2):**
   - *Rationale:* Depicts a simple generic "Saved Successfully" popup dialog. Embedding it in the README would interrupt documentation flow for trivial confirmation feedback.
4. **`admin-reservation-history-timeline.png` (A3, A8):**
   - *Rationale:* Retained in the index to prove detailed status transition audit logging and admin decision recording without overcrowding the core reservation queue walkthrough.

---

## 4. Gap Analysis and Justification for Remaining Placeholders

Only one placeholder remains unresolved across the system documentation:

1. **`admin-event-actions.png` (A5 — Operational Event Actions and Print Slip):**
   - *Reason:* While the daily event monitoring schedule table is captured (`admin-event-monitoring.png`, Figure 29), the operational views for attendee check-in timestamps, completion timestamps, incident reporting notes, and printable reservation slip preview were not captured. 

