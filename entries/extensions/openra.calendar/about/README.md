# Calendar

Research Calendar keeps local events, project milestones, shared Todos,
deadline points and preparation blocks together. Local planning is available
on Windows, Linux and macOS without a cloud calendar account.

On macOS, system-calendar reading is optional. The operating system asks
for full calendar access; OpenRA's own constraint is to use it only for
reading. Refusing or revoking access leaves local plans available. System
sync does not mean OpenRA connects directly to Google, Outlook or CalDAV;
those legacy optional connectors are not required for local planning.

**Delivery: bundled.** The code ships inside the OpenRA app. Installing this
entry from the Extension Hub records it as installed; open it and explicitly
enable it to run. Nothing is downloaded or run from this repository.
Installed, enabled, source visibility and reminder settings are separate
states. Uninstalling turns it off everywhere and keeps everything it saved,
so a later reinstall can use the existing records.

The entry's `version` must match the version the app ships; an app that
ships another version refuses the install and asks you to update the app or
pick the matching entry.

## What it does

- **Events.** Save manual events with stable IDs; concurrent saves are caught
  by revision conflicts. Original timezones, all-day and floating times stay
  distinct; ambiguous or unknown times are flagged for review instead of
  guessed.
- **Event details and repeats.** Events can carry a location and notes, and a
  daily, weekly, monthly or yearly repeat (interval, occurrence count or end
  date, weekday selection for weekly rules, per-date exceptions). Repeats
  expand only inside the requested window, a repeat needs a start, and a
  series that hits the expansion bound is reported as truncated, never
  guessed. Days and weeks stay honest the same way: busy checks include
  occurrences that start before the window, with their own truncation count.
- **Local calendars.** Events can carry an optional calendar label (up to
  sixteen local calendars, label at most sixty-four bytes); an event without a
  label stays on your primary calendar, and the editor offers the labels you
  already use.
- **Range search.** Read any explicit start-to-end range instead of a fixed
  day or week: the end date is exclusive, the span is bounded to 366 days,
  and the same honest placement, truncation and exclusion counts apply.
- **One window, several sources.** The unified day/week window reads your
  events, the deadlines source layer (below), and a read-only CCF conference
  deadline snapshot embedded from one pinned upstream commit, plus the
  projected rows of the subscribed feeds below that have a proven body. Each
  source keeps its own revision and status; disabling one degrades only that
  layer, and row counts are reported instead of silently truncated.
- **Deadline watches.** Optional personal reminder rules over both layers:
  bounded offsets, bindings pinned to a content signature, one audited
  transition per replan, and submitted state or private notes that source
  updates never overwrite. No precise reminder is generated for TBD or
  unresolved times. Due watches fire through the host's shared reminder
  engine: candidates pass the same quiet-hours, quota and snooze policy as
  personal reminders, delivery is at-least-once, rescheduling a stage lets
  its old reminder keys lapse naturally, and a disabled instance delivers
  nothing.
- **Deadline filtering.** The conference layer can be narrowed before the
  window budgets apply: a case-insensitive title query, a CCF rank
  selection and a direction (subfield) selection combine into one filter.
  Stages dropped by it are counted as filtered out rather than silently
  missing, and the active filter is echoed back with the read so the display
  always shows what was asked.
- **ICS preview.** A bounded read-only `ics.parse` previews untrusted
  iCalendar text: supported repeats expand within the requested window,
  unsupported rule parts degrade to the master occurrence with reported
  issues, and parsing imports nothing.
- **ICS subscriptions.** Store a bounded list of calendar addresses;
  `subscription.refresh` fetches one feed on demand with ETag/Last-Modified
  conditional requests, reports unchanged content as not-modified, keeps the
  last successful sync separate from failed attempts, and never imports
  fetched events automatically. Fetched events overlay the unified read as a
  separate read-only layer only after a fetch succeeded: each feed shows its
  own honest state (pending, stale, unavailable), rows come from the last
  stored proven body rather than the raw feed text, and nothing is imported
  into your manual events. The calendar panel manages the list — add, label,
  remove and refresh — and untrusted feed content never gains write access.
- **Preparation blocks.** Bounded work blocks linked to a deadline marker —
  they never modify the official deadline time. `busy` answers conflict
  checks by merging precise zoned intervals of records and blocks; entries
  without precise times are reported as excluded, never inferred, and
  deadlines themselves are due points, never busy time.
- **Legacy optional connected calendars (CalDAV).** Store a small list of CalDAV accounts;
  `connection.refresh` discovers the address book's principal and calendars
  on demand and keeps per-calendar receipts (change tags, content
  signatures, coverage) separate from failed attempts, the same honest
  pending/stale/unavailable states as subscriptions. Fetched events overlay
  the unified read as their own read-only layer only after a proven body,
  with a management editor for add, label, edit and remove. Provider
  interfaces (Google, Outlook) are frozen optional extensions; nothing here
  registers an account with any service.
- **Legacy optional connection writes.** `connection.event.save` and
  `connection.event.delete` propose one record at a time against the
  calendar that already holds it: the server's entity tag is the write token,
  a stale token is a revision conflict, never an overwrite, and every
  accepted write is auditable. Untrusted connection content never gains
  rights over your local events.
- **Single-record saves.** `event.save` is one create-or-replace call for one
  manual event: a new id creates only with no held signature, replacing an
  existing id needs the signature the last read handed you (the same
  single-record compare-and-set the connections use), and an identical
  re-save changes nothing. The reply returns the stored record and its new
  signature, so chained edits need no re-read.
- **Agent-friendly reads and writes.** The host may let a coding agent call a
  declared, audited subset of these actions — reads (list, agenda, search,
  busy, watches, milestones) and the two single-record saves. That
  declaration lives in the manifest; the host still gates every call through
  its own permission, approval and audit flow, and side-effect actions are
  refused outright from an agent channel until that wiring exists. Imports,
  exports and account management stay human-only.
- **System calendar (macOS).** On a Mac, the unified read also shows the
  events already in your system calendar as a read-only layer: a live
  fetch, never stored, never merged into your events. Access is asked for
  once through the `system.grant` action (the system prompt shows up at
  most once; an unanswered prompt is reported as pending, never assumed),
  and a denied or unavailable layer degrades alone. Select system calendars
  by their stable identities for the current time window; a fresh selection
  starts empty and new calendars are not silently added. This is a read
  filter, not a permission grant or a write path. Windows and Linux report
  this layer as unavailable and retain local planning.
- **Research focus.** Pin up to three research goals: a project with a
  concrete deadline point, either a labeled manual time or a stage from the
  read-only CCF snapshot. A TBD stage honestly stays "to be announced" —
  no countdown is invented — and a deadline whose time moved is reported as
  moved. Goals carry their own milestones (title, due point, done, note);
  marking a milestone done keeps its identity, and a preparation block can
  link to a pinned goal the same way it links to a deadline marker, without
  ever touching the official deadline.

## Deadlines

The [Deadlines extension](../openra.deadlines/about/README.md) keeps its own
id and remains the place to manage deadline sources directly. Calendar reads
those same records as its default deadline source layer, so your existing
data, deep links and permissions keep working; official deadline times are
read-only in the calendar, which offers preparation blocks instead of edits.
