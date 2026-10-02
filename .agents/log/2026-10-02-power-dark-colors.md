# Power dark-mode contrast

Owner requested a restrained colour improvement. Lifted cathode housing from charcoal to slate, fixed dark inline label overrides, and brightened target violet, cathode coral, preanode pink, anode teal and heater orange. Replaced each potential's colour consistently across direct connections and labels. Equipment pictograms retain their colours.

181 pytest tests pass. Comparison against HEAD proves SVG differs only in hex colour values; geometry is byte-identical after normalizing those values. Browser confirms label fill rgb(171,184,197), housing rgb(115,127,137), target violet rgb(173,145,237). Rails stay at 76px at rest/scroll and a second height; 390px viewport document width is 375px. No browser errors. Screenshot local/power-dark-colors.png. Managed scratch preview stopped after verification.
