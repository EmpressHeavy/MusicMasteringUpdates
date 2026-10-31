-- Music Mastering for GarageBand v2: reference AppleScript snippets.
-- Run ON THE OWNER'S MAC only (osascript), each with the owner's approval. gb_control.py prints these same snippets
-- as one-line osascript commands; this file is the readable reference. Requires Accessibility permission for the app
-- that runs Grok Bot's commands (System Settings > Privacy & Security > Accessibility), and Screen Recording for screenshots.

-- 1) Accessibility check (errors -1719 / -25211 mean permission is missing)
tell application "System Events" to get name of first process

-- 2) Is the front window the COPY? (never edit or save anything else)
tell application "System Events" to tell process "GarageBand"
	set t to name of front window
	if t does not contain "master" then return "FRONT_NOT_COPY: " & t
	return "FRONT_OK: " & t
end tell

-- 3) Menu discovery (names change by version and language; match by prefix)
tell application "System Events" to tell process "GarageBand"
	set out to ""
	repeat with m in menu bar items of menu bar 1
		try
			set out to out & (name of m) & ": " & ((name of menu items of menu 1 of m) as text) & linefeed
		end try
	end repeat
	return out
end tell

-- 4) Show Master Track (same as Cmd-Shift-M)
tell application "GarageBand" to activate
tell application "System Events" to tell process "GarageBand"
	set mi to first menu item of menu 1 of menu bar item "Track" of menu bar 1 whose name starts with "Show Master Track"
	click mi
end tell

-- 5) Export Song to Disk: open the sheet, name it, export, confirm Replace only for the bot's own "- master vN" names
tell application "System Events" to tell process "GarageBand"
	click (first menu item of menu 1 of menu bar item "Share" of menu bar 1 whose name starts with "Export Song to Disk")
	delay 2
	set s to sheet 1 of front window
	set value of text field 1 of s to "Song - master v1"
	click (first button of s whose name is "Export")
end tell
