## System Diagrams
### 1. Application Architecture (Django MTV)

![1. System Architecture - Django Model-Template-View (MTV)](diagrams/01_architecture_mtv.png)

*Source-level architecture depicting the active middleware stack (`Security`, `Session`, `Common`, `CsrfView`, `Authentication`, `Message`, `XFrameOptions`), root URL dispatch via `HomeLoginView` with role-based redirects, access guards (`basic_user_required`, `admin_required`, `administrator_required`), direct view queries, and the service layer. `update_reservation` handles approve, reject, admin cancel, check-in, complete, and no-show; `reschedule_reservation` handles date and time changes; `record_audit` writes audit entries. Owner cancellation by a Basic User is the exception: it runs in `reservations/views.py` with its own transaction and calls `record_audit` directly rather than going through the services. The diagram also shows the template layer and the SQLite backend.*

---

### 2. ERD — Facility Catalog, Amenities, and Closures

![2. ERD - Facility Catalog, Amenities, and Closures](diagrams/02_erd_catalog_closures.png)

*Data model representing facility categories, facilities, amenities, and closure blocks. Accurately reflects database-level nullability (`category_id` and `code` nullable in the schema, enforced non-empty by `Facility.clean()`), M:N table `facilities_facility_amenities`, and `PROTECT` foreign key constraints.*

---

### 3. ERD — Reservations, History, and Event Monitoring

![3. ERD - Reservations, History, and Event Monitoring](diagrams/03_erd_reservations_events.png)

*Core reservation data structures illustrating `Reservation` records, audit trail tracking in `ReservationChange` (`CASCADE`), 1:1 `EventRecord` with check-in/completion/no-show timestamps, and `EventIncident` logs linked via foreign keys with `PROTECT` actor references.*

---

### 4. ERD — Identity, User Profiles, Audit Logs, and System Settings

![4. ERD - Identity, User Profiles, Audit Logs, and System Settings](diagrams/04_erd_identity_audit_settings.png)

*Supporting data models for identity and administration. Emphasizes that `AuditLog.admin_user` is a required non-nullable foreign key (recording both admin actions and basic-user cancellations), `UserProfile` is 1:1 with `auth.User`, and `SystemSetting` operates as a convention singleton (`pk=1`) with nullable `updated_by` (`SET_NULL`).*

---

### 5. Workflow — Reservation Request Submission

![5. Workflow - Reservation Request Submission](diagrams/05_workflow_request_submission.png)

*Basic user booking process: input capture (`event_title`, `purpose`, `participant_count`, `start_time`, `end_time`), model validation (event title required, `start_time > now`, same local day in `Asia/Manila`, operating hours, duration limit, advance window, capacity, active category/facility, no closure conflicts), initial `Pending` status without reserving slots, and owner cancellation before start time. Database-lock handling for user reservation submission (F-06) is fixed;*

---

### 6. Workflow — Administrator Decision and Approval

![6. Workflow - Administrator Decision and Approval](diagrams/06_workflow_approval_decision.png)

*Administrative review flow: a mandatory rejection reason (the reservation must be Pending) with audit tracking, or approval within a database transaction. The service performs a Facility UPDATE using `F('is_active')`, retrieves the reservation using `select_for_update()`, re-checks that its status is still Pending, and revalidates through `full_clean()`. `select_for_update()` does not provide row-level locking on SQLite; the Facility UPDATE is what makes competing approvals queue on SQLite. If the database stays locked past SQLite's wait (about 5 seconds), the approval view catches the database error, shows "database conflict, please try again", and leaves the reservation Pending. In threaded tests on a file-based SQLite database, two simultaneous approvals of overlapping bookings produced exactly one approval in all 10 rounds. See [Testing](#testing) and [Limitations and Enhancements](#limitations-and-enhancements).*

---

### 7. Workflow — Reservation Lifecycle: Cancellation, Rescheduling, and Events

![7. Workflow - Reservation Lifecycle: Cancellation, Rescheduling, and Events](diagrams/07_workflow_reservation_lifecycle.png)

*Post-approval operational workflows: pre-start cancellation releasing timeslots (a Basic User may cancel their own Pending or Approved booking; an admin cancels an Approved booking with a required reason), administrative rescheduling with full conflict revalidation, check-in restricted to the scheduled time window (`start_time <= now < end_time`), event completion requiring valid check-in with `actual_end >= actual_start`, post-end no-show recording (`now >= end_time`), and optional incident logging for checked-in, completed, or no-show bookings. Each status change is recorded in `ReservationChange` and the audit log.*

---

### 8. Workflow — Facility Closure Management

![8. Workflow - Facility Closure Management](diagrams/08_workflow_closure_management.png)

*Closure maintenance lifecycle: form inputs (`facility`, `start_time`, `end_time`, `reason`), model validation where the future-start check (`start_time > now`) applies strictly to new closures, overlap checks with existing active closures and approved/checked-in bookings (excluding pending requests), and a dedicated POST action to archive active closures without deletion.*

---

