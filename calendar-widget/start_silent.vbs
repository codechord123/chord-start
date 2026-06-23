' 이 파일을 더블클릭하면 검은 창 없이 캘린더만 실행됩니다
Dim fso, dir, ws
Set fso = CreateObject("Scripting.FileSystemObject")
dir = fso.GetParentFolderName(WScript.ScriptFullName)

Set ws = CreateObject("WScript.Shell")
ws.CurrentDirectory = dir
ws.Run "pythonw """ & dir & "\main.py""", 0, False

Set ws = Nothing
Set fso = Nothing
