# Plan — #431

1. Add `driver` to the local run index (created `manual`, set `automated` on `POST :start`) and a
   `useRunDriver` hook that also recognises foreign automated runs via nine invoked stakeholders.
2. Render a persistent automated-run banner and manual/automated badge in the run shell (console and
   consensus inherit it), plus a consensus footnote and an "automatically set" label for `support = 1`.
3. Delete D-FE-003 and switch `useRunFeed` to `/runs/{id}/negotiation/stream` with polling fallback.
4. Extend Playwright axe coverage to console/consensus/brief via `HPS_E2E_RUN_ID`.
5. Component test for banner automated vs manual.
