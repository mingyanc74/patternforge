# Clearflow reference UI implementation

Historical implementation record, 2026-10-20. The real frontend was rebuilt from the user's Clearflow history-demo HTML without modifying that reference. Subsequent Rulecraft styling and retained-dataset behavior are documented in [current design notes](UI_DESIGN.md) and [UI refresh evidence](../reports/UI_REFRESH.md); the historical descriptions below are not the current feature specification.

## Mapped design

- White header, Office blue, light-gray sidebar and Segoe UI, without external font downloads in this revision.
- Prepare data / Jobs / Connections navigation, moved to the top on narrow screens.
- Connect, Select file, Configure, Processing and Results steps.
- History table with search, status filters, five-row pages, creation/runtime columns, view and reuse actions.
- Preview alongside a transformation panel, three operations and an explicit delete-matches option.
- Confirmation before submission, cancellation, draft replacement on reuse and disconnect.
- Processing, failure, retry, cancellation, success, expiry, empty-history and no-search-results states.
- Visible keyboard focus, Escape dismissal, dialog focus trapping, reduced motion and mobile layout.

## Necessary differences from the prototype

1. No seeded jobs in the normal application. Django supplies session-owned history with server-side search/filtering/pagination, not search limited to the latest 50 entries.
2. At this revision, reuse created a new draft and required source reinspection, not reuse of an old inspection ID. Expired connections required fresh authorization; old keys were not restored. Later retained-snapshot support is described separately.
3. Original preview is bounded source data. Spark may reorder rows; do not fake aligned row-by-row diffs. Blue columns identify targets, not verified changed cells.
4. Large results use signed cursor pagination, not invented arbitrary page jumps or a fixed three pages.
5. Missing backend/model services produce explicit errors, never simulated processing success.
6. This revision displayed Clearflow while repository/services/deployment configuration retained `patternforge`. The current interface is Rulecraft.

## Validation entry points

- Normal application: start Django/Vite and open the displayed development URL.
- Dedicated UI fixture: `/test/fixture.html`, explicitly labelled Sample data only. It is not part of the default production build, calls no AWS/model and does not seed the database.
- Backend tests cover history queries, pagination, expiry and isolation. UI fixture success does not establish real AWS/Spark acceptance.

## Recorded checks on 2026-10-20

- UI implementation: `52758ed`.
- Local TypeScript/production build and five frontend state-display tests passed.
- Linux backend/real Java-Spark unit/integration tests: 52 passed in 46.34 seconds.
- Local history API checks: 19 passed, covering search, full-page traversal, filtering, expiry, safe summaries, session isolation and invalid parameters.
- Browser fixture: empty search, expired filter, details, reuse/reinspection, restored column choices, review/submit, results, next page, source-preview explanation and cancellation confirmation/state.
- Real local entry: empty history, missing-service information, connection form and help worked without fake jobs.
- At 375px, top navigation worked without whole-page horizontal overflow; Escape closed help and restored focus.
- [Associated CI run](https://github.com/mingyanc74/patternforge/actions/runs/39366328920): frontend/backend jobs passed; consult the actual final run for distributed-job status.

These are UI/development checks, not public deployment, AWS authorization or model-accuracy evidence. Later real-service results remain separately documented.
