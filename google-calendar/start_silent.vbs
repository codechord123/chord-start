' 더블클릭하면 검은 창 없이 캘린더가 바로 실행됩니다
Dim fso, dir, ws
Set fso = CreateObject("Scripting.FileSystemObject")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
Set ws = CreateObject("WScript.Shell")
ws.CurrentDirectory = dir
ws.Run "pythonw """ & dir & "\desktop_app.py""", 0, False
