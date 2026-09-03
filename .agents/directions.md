# Open directions

- Split `diagram.svg` at valve boundaries and wrap each continuously connected plumbing volume in a stable `zone-*` group without changing the existing valve, pump, or gauge IDs — owner work pending.
  Done when: every volume whose connectivity can change independently has one unambiguous group ID, so the application can derive connected components without guessing from path geometry.
- Review and correct the prototype `Vent Plasma` and `Vent QMS` sequences in `static/operationGuides.json`, including exact valve names, ordering, and marker placement — owner guidance pending after hands-on use.
  Done when: each step matches the physical operating procedure and the owner accepts the diagram markers and rail wording.
