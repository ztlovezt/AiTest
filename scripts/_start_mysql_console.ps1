$env:PATH = "C:\Program Files\MySQL\MySQL Server 8.4\bin;" + $env:PATH
& mysqld --defaults-file="C:\ProgramData\MySQL\MySQL Server 8.4\my.ini" --console
