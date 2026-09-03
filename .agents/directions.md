# Open directions

- Split `diagram.svg` at valve boundaries and wrap each continuously connected plumbing volume in a stable `zone-*` group without changing the existing valve, pump, or gauge IDs — owner work pending.
  Done when: every volume whose connectivity can change independently has one unambiguous group ID, so the application can derive connected components without guessing from path geometry.
