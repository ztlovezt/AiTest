# Neo4j Windows 原生安装执行文档

> 适用范围：TestHub Platform — 精准测试模块 (Week 3 起依赖)
> 目标：将 Neo4j 2026.04.0 Community 作为 Windows 服务安装，与 Redis / MySQL 启动方式保持一致
> 维护者：TestHub 平台组
> 文档版本：1.0 (2026-05-09)

---

## 1. 背景与决策

TestHub 现有中间件全部以 Windows 服务方式运行：

| 组件 | 启动方式 | 服务名 |
|---|---|---|
| MySQL 8.4 | Windows Service | `MySQL84` |
| Redis 7.x | Windows Service | `Redis` |
| Neo4j 2026.04.0 | **此前 Docker，现切换为 Windows Service** | `neo4j` |

切换原因：
- **一致性**：所有中间件统一以 `net start <service>` 管理
- **启动速度**：原生启动 5–10 秒，Docker 30–60 秒（首次更慢）
- **资源占用**：去除 Docker Desktop 的常驻内存（~500 MB）
- **可观测性**：日志直接写到 `%NEO4J_HOME%\logs\`，无需 `docker logs`

`scripts/start_all.py` 已经更新为 **Windows 服务优先 → Docker 回退** 的启动顺序。

---

## 2. 前置条件

| 项 | 要求 | 验证命令 |
|---|---|---|
| 操作系统 | Windows 10/11 或 Server 2019+ | `winver` |
| 管理员权限 | 安装服务必需 | 右键 cmd → 以管理员身份运行 |
| JDK | **JDK 17 或 21**（Neo4j 5.x 强制） | `java -version` |
| 磁盘空间 | ≥ 2 GB（Neo4j + 数据） | — |
| 端口 7474/7687 | 未被占用 | `netstat -ano \| findstr ":7474 :7687"` |

> **JDK 8/11 无法运行 Neo4j 5.x**，启动会立即报 `UnsupportedClassVersionError`。

---

## 3. 安装步骤

### 步骤 1：安装 JDK 21

下载 Eclipse Temurin JDK 21（推荐 LTS）：

- 链接：<https://adoptium.net/temurin/releases/?version=21>
- 选择 **Windows x64 MSI**
- 安装时勾选 "Set JAVA_HOME variable" 和 "Add to PATH"

验证：

```cmd
java -version
:: 期望输出: openjdk version "21.0.x" ...

echo %JAVA_HOME%
:: 期望输出: C:\Program Files\Eclipse Adoptium\jdk-21.0.x-hotspot
```

### 步骤 2：下载并解压 Neo4j 5.28 Community

下载链接：<https://neo4j.com/deployment-center/?edition=community&flavour=winzip>

- 选择 **Neo4j 5.28.0 Community Edition - Windows ZIP**（约 220 MB）
- 解压到 `E:\neo4j-community-5.28.0`（推荐路径，下文以此为例）

> 解压路径**不要包含中文或空格**，否则 Windows 服务注册可能失败。

验证目录结构：

```
E:\neo4j-community-5.28.0\
├── bin\
│   ├── neo4j.bat
│   ├── neo4j-admin.bat
│   └── ...
├── conf\
│   └── neo4j.conf
├── data\          (空目录，首次启动后会创建数据库)
├── logs\
├── plugins\       (步骤 3 放 APOC jar 到这里)
└── ...
```

### 步骤 3：下载 APOC 插件

> APOC 是 Neo4j 的扩展过程库，**Week 3 图谱构建必需**（用于批量导入、路径分析、子图操作）。

- 链接：<https://github.com/neo4j/apoc/releases/tag/5.28.0>
- 下载 **`apoc-5.28.0-core.jar`**（约 5–20 MB）
- 放到 `E:\neo4j-community-5.28.0\plugins\` 目录

> 版本必须严格匹配 Neo4j 大版本（5.28.x ↔ apoc-5.28.x-core.jar）。版本错配启动会失败。

### 步骤 4：执行自动化安装脚本（**管理员 CMD**）

```cmd
:: 1. 以管理员身份打开 CMD（开始菜单 → 搜索 cmd → 右键"以管理员身份运行"）

:: 2. 切到项目目录
cd /d E:\testhub_platform

:: 3. 执行安装脚本，传入 Neo4j 解压目录
scripts\install_neo4j_native.bat E:\neo4j-community-5.28.0
```

脚本会自动完成：

| 步骤 | 内容 |
|---|---|
| 4.1 | 校验管理员权限、`JAVA_HOME`、APOC 插件 |
| 4.2 | 备份 `conf\neo4j.conf` 到 `neo4j.conf.bak` |
| 4.3 | 在 `neo4j.conf` 末尾追加 TestHub 配置块（监听地址、内存、APOC 授权） |
| 4.4 | 设置初始密码 `testhub123`（首次，Neo4j 5.x 最少 8 字符） |
| 4.5 | 执行 `neo4j.bat windows-service install` 注册服务 |
| 4.6 | `sc config neo4j start= auto` 设置开机自启 |
| 4.7 | `net start neo4j` 启动并轮询 Bolt 端口 7687 |

成功输出：

```
==================================================
  Neo4j 安装完成
==================================================
  Bolt:    bolt://localhost:7687
  Browser: http://localhost:7474/
  账号:    neo4j / testhub123
```

### 步骤 5：验证安装

```cmd
:: 1. 服务状态
sc query neo4j
:: 期望: STATE : 4 RUNNING

:: 2. 端口监听
netstat -ano | findstr ":7474 :7687"
:: 期望两个端口均 LISTENING

:: 3. Browser 访问
start http://localhost:7474/
:: 浏览器登录: neo4j / testhub

:: 4. Cypher 连通性测试
:: 在 Browser 中执行: RETURN "TestHub Neo4j is up" AS msg

:: 5. APOC 加载验证
:: 在 Browser 中执行: CALL apoc.help("apoc") YIELD name RETURN count(name)
:: 期望返回 > 0
```

### 步骤 6：与 `start_all.py` 集成验证

```cmd
cd /d E:\testhub_platform
scripts\启动所有服务.bat
```

期望日志：

```
  -> 检查 Neo4j...
  ✓ Neo4j 已在运行 (Bolt 端口 7687)
```

如果服务已运行，`start_all.py` 会在 `is_port_in_use(7687)` 第一关秒过，**不再调用 docker info（即不再有 10s 超时）**。

---

## 4. 配置详解

`install_neo4j_native.bat` 写入 `conf\neo4j.conf` 的配置块：

```properties
# TestHub-managed config (do not delete this line)
server.default_listen_address=0.0.0.0
server.bolt.listen_address=:7687
server.http.listen_address=:7474
server.memory.heap.initial_size=512m
server.memory.heap.max_size=2G
dbms.security.procedures.unrestricted=apoc.*
dbms.security.procedures.allowlist=apoc.*
```

| 配置项 | 含义 | 备注 |
|---|---|---|
| `server.default_listen_address` | 监听地址 | `0.0.0.0` 允许局域网访问，仅本机改 `127.0.0.1` |
| `server.bolt.listen_address` | Bolt 协议端口 | 后端 Python 驱动连接 |
| `server.http.listen_address` | HTTP/Browser 端口 | 浏览器管理界面 |
| `server.memory.heap.*` | JVM 堆内存 | 与 Docker 配置一致；如内存紧张可降低 max 到 1G |
| `dbms.security.procedures.unrestricted` | APOC 授权 | **缺失会导致 apoc.* 调用被拒** |
| `dbms.security.procedures.allowlist` | APOC 白名单 | 同上 |

### 调整堆内存

如机器内存有限（< 8 GB），编辑 `conf\neo4j.conf`：

```properties
server.memory.heap.initial_size=256m
server.memory.heap.max_size=1G
```

修改后：`net stop neo4j && net start neo4j`

---

## 5. 后端代码连接配置

**无需任何代码改动**。`backend/backend/settings.py` 已使用 `bolt://localhost:7687`，与启动方式无关。

```python
# backend/backend/settings.py 中的现有配置
NEO4J_BOLT_URL = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "testhub123"
```

如未来需要外部连接，将 `bolt://localhost:7687` 改为目标主机即可。

---

## 6. 日常运维命令

### 启停

```cmd
net start neo4j           :: 启动
net stop neo4j            :: 停止
sc query neo4j            :: 查询状态
```

### 查看日志

```cmd
:: 标准日志（启动信息、错误）
type E:\neo4j-community-5.28.0\logs\neo4j.log

:: 详细调试日志
type E:\neo4j-community-5.28.0\logs\debug.log

:: 实时跟踪（PowerShell）
Get-Content E:\neo4j-community-5.28.0\logs\neo4j.log -Wait -Tail 50
```

### 清空数据库（开发环境重置）

```cmd
net stop neo4j
rmdir /S /Q E:\neo4j-community-5.28.0\data\databases
rmdir /S /Q E:\neo4j-community-5.28.0\data\transactions
net start neo4j
:: 数据已清空，密码不变
```

### 重置密码

```cmd
net stop neo4j
del E:\neo4j-community-5.28.0\data\dbms\auth
cd /d E:\neo4j-community-5.28.0
bin\neo4j-admin dbms set-initial-password <new_password>
net start neo4j
:: 同步更新 backend/backend/settings.py 中的 NEO4J_PASSWORD
```

---

## 7. 常见问题排查

### 7.1 服务启动失败：`UnsupportedClassVersionError`

**原因**：`JAVA_HOME` 指向 JDK 8/11，Neo4j 5.x 需要 17 或 21。

**解决**：
```cmd
:: 1. 确认 JDK 版本
java -version

:: 2. 重新设置 JAVA_HOME（系统属性 → 环境变量 → 系统变量）
set JAVA_HOME=C:\Program Files\Eclipse Adoptium\jdk-21.0.5-hotspot

:: 3. 重启服务
net stop neo4j
net start neo4j
```

### 7.2 服务启动失败：`Address already in use: bind`

**原因**：端口 7474 或 7687 被其他进程占用。

**解决**：
```cmd
netstat -ano | findstr ":7474"
:: 找到 PID
tasklist /FI "PID eq <pid>"
:: 决定是否结束该进程，或修改 neo4j.conf 端口
```

### 7.3 Browser 登录失败：`Unauthorized`

**原因**：密码错误或首次未初始化。

**解决**：见 §6 重置密码。

### 7.4 APOC 不可用：`There is no procedure with the name apoc.*`

**原因**：插件 jar 未放或版本错配。

**解决**：
```cmd
dir E:\neo4j-community-5.28.0\plugins\apoc-*.jar
:: 应有 apoc-5.28.0-core.jar
:: 不存在则按 §3 步骤 3 重新下载

:: 检查 neo4j.conf 是否包含授权
findstr "apoc" E:\neo4j-community-5.28.0\conf\neo4j.conf
:: 应见 dbms.security.procedures.unrestricted=apoc.*

net stop neo4j && net start neo4j
```

### 7.5 服务安装失败：`Access is denied`

**原因**：未以管理员身份运行 CMD。

**解决**：开始菜单搜索 cmd → 右键"以管理员身份运行"。

### 7.6 `start_all.py` 仍在调用 docker

**原因**：`scripts/start_all.py` 旧版本（未应用本次改动）。

**解决**：
```cmd
git log -1 -- scripts/start_all.py
:: 应包含 _start_neo4j_via_windows_service 的提交
```

---

## 8. 数据迁移：Docker → 原生

如此前已用 Docker 运行过 Neo4j 并写入数据，迁移步骤：

```cmd
:: 1. 停止 Docker 容器（不删除）
docker stop testhub-neo4j

:: 2. 备份 Docker 卷数据
docker run --rm ^
  -v testhub_neo4j_data:/data ^
  -v %CD%:/backup ^
  alpine tar czf /backup/neo4j-data.tar.gz -C /data .

:: 3. 解压到原生 data 目录（Neo4j 服务必须停止）
net stop neo4j
cd /d E:\neo4j-community-5.28.0\data
tar xzf E:\testhub_platform\neo4j-data.tar.gz

:: 4. 启动原生服务
net start neo4j

:: 5. 验证
:: 在 Browser 中查询既有数据：MATCH (n) RETURN count(n)

:: 6. 数据 OK 后，清理 Docker 资源
docker rm testhub-neo4j
docker volume rm testhub_neo4j_data testhub_neo4j_logs
```

> 若 Week 2 阶段未实际写入 Neo4j 数据（按当前评估也是如此），**可跳过本节，直接装原生**。

---

## 9. 卸载与回滚

### 卸载 Windows 服务

```cmd
:: 管理员 CMD
cd /d E:\testhub_platform
scripts\uninstall_neo4j_native.bat E:\neo4j-community-5.28.0
```

脚本会：
1. `net stop neo4j` 停止服务
2. `neo4j.bat windows-service uninstall` 卸载
3. 询问是否清理 `data\` 目录

### 回滚到 Docker 模式

1. 卸载 Windows 服务（上一步）
2. `start_all.py` 自动回退到 `_start_neo4j_via_docker()` 路径
3. 启动 Docker Desktop
4. `scripts\启动所有服务.bat` 即可

---

## 10. 配套文件清单

本次切换涉及的文件（按目录）：

```
E:\testhub_platform\
├── scripts\
│   ├── start_all.py                  (修改：Neo4j 启动优先级调整)
│   ├── install_neo4j_native.bat      (新增：自动化安装)
│   ├── uninstall_neo4j_native.bat    (新增:卸载)
│   ├── 启动所有服务.bat               (无需修改)
│   └── 停止所有服务.bat               (无需修改)
├── docker-compose.neo4j.yml           (保留:Docker 回退方案)
└── notes\
    └── Neo4j-Windows原生安装文档.md   (本文档)
```

---

## 11. 常见问题与故障排查

### 问题 1：console 模式提示 "Neo4j is already running"（服务已删除但 lock 残留）

**现象**：
- `sc delete neo4j` 删除服务后，执行 `neo4j.bat console` 仍报 `Neo4j is already running`
- 无 Java 进程在运行，但端口也未监听

**根因**：
Windows Service 异常退出时，`data/databases/` 下的 `database_lock` 和 `store_lock` 未被清理。

**修复**：
```cmd
:: 管理员 CMD
taskkill /F /IM java.exe
cd /d E:\neo4j-community-2026.04.0
for /r data %%i in (*lock*) do del "%%i"
```

---

### 问题 2：权限警告 "Owner differs, potentially resulting in a file permission problem"

**现象**：
启动日志出现：
```
Owner 'BUILTIN\Administrators' of 'E:\neo4j-community-2026.04.0' and user running this process differs
```

**根因**：
解压 ZIP 后的目录所有者是 `BUILTIN\Administrators`，而当前用户账户 SID 不同，Neo4j 5.x 会拒绝写入。

**修复**（管理员 CMD）：
```cmd
takeown /F E:\neo4j-community-2026.04.0 /R /D Y
icacls E:\neo4j-community-2026.04.0 /grant %USERNAME%:F /T
```

---

### 问题 3：密码设置失败 "Password must be at least 8 characters"

**现象**：
```
neo4j-admin dbms set-initial-password testhub
Command Failed: Password must be at least 8 characters.
```

**根因**：
Neo4j 5.x 强制密码策略要求最少 8 字符。

**修复**：
使用 `testhub123` 或其他 ≥8 字符的密码，并同步更新 `config.yaml`：
```yaml
neo4j:
  password: testhub123
```

---

## 12. 安装快速核对清单

完成后逐项确认：

- [ ] JDK 21 已安装，`java -version` 显示 21.x
- [ ] `JAVA_HOME` 指向 JDK 21 安装目录
- [ ] Neo4j 2026.04.0 解压到无中文/空格路径
- [ ] `apoc-2026.04.0-core.jar` 在 `plugins\` 目录
- [ ] 以管理员 CMD 执行 `install_neo4j_native.bat <path>`
- [ ] `sc query neo4j` 显示 `STATE : 4 RUNNING`
- [ ] `netstat -ano | findstr ":7687"` 显示 LISTENING
- [ ] Browser <http://localhost:7474/> 能登录（neo4j / testhub）
- [ ] APOC 验证：`RETURN apoc.version()` 有返回
- [ ] `scripts\启动所有服务.bat` 在"检查 Neo4j"步骤秒过

全部勾选 → 可以推进 Week 3：Neo4j 图谱构建 + Cypher 查询。

---

## 12. 参考链接

- Neo4j 5.28 官方文档：<https://neo4j.com/docs/operations-manual/5.28/>
- Windows 服务安装：<https://neo4j.com/docs/operations-manual/5.28/installation/windows/>
- APOC 5.28：<https://neo4j.com/labs/apoc/5/installation/>
- Eclipse Temurin JDK 21：<https://adoptium.net/temurin/releases/?version=21>
