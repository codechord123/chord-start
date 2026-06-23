' Double-click to start the calendar silently (no console window)
CreateObject("WScript.Shell").Run "pythonw """ & Replace(WScript.ScriptFullName, "start_silent.vbs", "desktop_app.py") & """", 0, False
