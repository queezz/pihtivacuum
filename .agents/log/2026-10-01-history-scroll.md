# Fixed History navigation

Owner identified the calendar and new selector disappearing when the whole left rail scrolled. This predates the selector; the owner accepts scrolling the history list. Replaced whole-left-rail scrolling with an event-list scroller and redirected selection reveal to it. Calendar, selector, timeline heading and Find stay fixed. Removed timeline explanation and tightened spacing in short windows.

177 pytest and 9 History Node tests pass. Scratch Lab PID 37968 retained. Browser at 1280x700: event viewport 109px; event scroll changed to 230.67px, rail remained 0, card tops stayed 76/170.45/477.03px. Tall and mobile drawer checks confirmed event scrolling and no document horizontal overflow; screenshot local/history-fixed-navigation.png. 0.27.4 was a local preview; 0.27.5 refreshes assets after the short-window revision.
