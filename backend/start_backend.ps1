# TestHub 后端启动脚本
# 自动使用 config.yaml 中配置的端口

# 设置工作目录
Set-Location D:\platform\testhub_platform\backend

# 激活虚拟环境
& D:\ENV\testhub\Scripts\Activate.ps1

# 从 config.yaml 读取端口配置
$configPath = "..\config.yaml"
$configContent = Get-Content $configPath -Raw
$backendPort = ($configContent | Select-String "backend_port" | Select-String -Pattern ":\s*(\d+)" | ForEach-Object { $_.Matches[0].Groups[1].Value })

# 如果没有找到端口配置，使用默认端口
if ([string]::IsNullOrEmpty($backendPort)) {
    $backendPort = "8000"
}

Write-Host "正在启动后端服务器，端口: $backendPort" -ForegroundColor Green

# 启动服务器
python manage.py runserver 0.0.0.0:$backendPort