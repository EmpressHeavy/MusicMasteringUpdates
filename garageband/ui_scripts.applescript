-- Run ON THE OWNER'S MAC only (osascript), with approval. Discovery helpers for UI scripting.
-- 1) Dump front window UI tree (use with Accessibility Inspector to find AX paths)
tell application "GarageBand" to activate
tell application "System Events" to tell process "GarageBand"
	set frontmost to true
	return entire contents of front window -- TODO: slow on big projects; narrow to groups once paths are known
end tell
