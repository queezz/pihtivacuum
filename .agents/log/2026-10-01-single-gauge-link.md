# Link CC Pi and SingleGauge

0.27.3 links upstream-single-gauge to single-gauge-power using the existing shared-gauge path. Unlike ULVAC controllers this device has no filament control. Vacuum on implies power and plug; Power unplug/off clears Vacuum. Practice saves synchronize only after recording. Histories remain separate.

177 pytest tests pass, including both directions, unplug, both Practice save routes and per-diagram history identities. Scratch Lab restarted as PID 16620. Browser: unplugged SingleGauge, navigated to Vacuum and observed CC Pi grey; pressed CC Pi and returned to Power, where SingleGauge power/plug were green and card green. No new layout geometry. Screenshot local/single-gauge-linked.png. Preview retained for owner review.
