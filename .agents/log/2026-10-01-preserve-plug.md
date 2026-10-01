# Preserve plug across power-off

Owner found CC Pi off revealing unplugged on SingleGauge. The read overlay could imply plugged while legacy Power history still held unplugged. Sync read the post-press overlay and lost that implied state. Capture Power state before Vacuum mutations (ordinary and Practice saves), preserve its plug when off, and explicitly record activation dependencies even if the read overlay already implied them. Direct Power-off preserves the plug too. Explicit unplug remains unchanged.

178 pytest tests pass, including regression with a legacy unplugged record underneath active CC Pi. Browser scratch: CC Pi off then Power shows SingleGauge power off and plug plugged. Screenshot local/cc-off-still-plugged.png. Scratch process PID 15000 stopped after verification; code does not rewrite existing logs.
