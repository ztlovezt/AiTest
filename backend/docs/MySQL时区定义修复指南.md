# MySQL 时区定义修复指南

本文档提供针对不同操作系统的 MySQL 时区定义修复方案，解决 Django Admin 中的时区错误：
```
Database returned an invalid datetime value. Are time zone definitions for your database installed?
```

---

## 方案概述

Django 使用 `USE_TZ = True` 时，需要 MySQL 数据库安装时区定义数据。如果没有安装，会导致时区转换失败。

---

## Windows 系统

### 方法 1：手动导入时区数据（推荐）

1. **下载 MySQL 时区数据**
   - 访问 MySQL 官方网站下载时区数据
   - 或使用已安装的 MySQL 时区数据文件

2. **使用命令行导入**
   ```cmd
   # 以管理员身份打开命令提示符
   cd "C:\Program Files\MySQL\MySQL Server 8.0\bin"
   
   # 导入时区数据到 MySQL
   mysql_tzinfo_to_sql "C:\Program Files\MySQL\MySQL Server 8.0\data\mysql" | mysql -u root -p mysql
   ```

3. **如果找不到 mysql_tzinfo_to_sql 工具**
   ```cmd
   # 直接从 MySQL 安装目录查找
   dir /s /b mysql_tzinfo_to_sql.exe
   
   # 或者使用在线时区数据
   # 下载后导入
   ```

### 方法 2：使用 MySQL Workbench

1. 打开 MySQL Workbench
2. 连接到 MySQL 服务器
3. 执行以下 SQL 脚本：

```sql
-- 检查时区表是否为空
SELECT COUNT(*) FROM mysql.time_zone;
SELECT COUNT(*) FROM mysql.time_zone_name;

-- 如果结果为 0，说明需要导入时区数据
```

### 方法 3：从 Linux 系统复制时区数据

如果你有 Linux 系统，可以从 Linux 导出时区数据：

```bash
# 在 Linux 系统上
mysql_tzinfo_to_sql /usr/share/zoneinfo > timezone_data.sql

# 将 timezone_data.sql 文件复制到 Windows
# 然后在 Windows 上导入
mysql -u root -p mysql < timezone_data.sql
```

---

## Linux 系统

### 快速操作（推荐）

```bash
# 1. 检查 zoneinfo 目录是否存在
ls /usr/share/zoneinfo

# 2. 导入时区数据（需要 root 权限）
sudo mysql_tzinfo_to_sql /usr/share/zoneinfo | sudo mysql -u root -p mysql

# 3. 验证导入是否成功
mysql -u root -p -e "SELECT COUNT(*) FROM mysql.time_zone_name;"
```

### Ubuntu/Debian

```bash
# 如果 mysql_tzinfo_to_sql 命令不存在，先确保 MySQL 客户端已安装
sudo apt-get update
sudo apt-get install mysql-client tzdata

# 导入时区数据到 MySQL
sudo mysql_tzinfo_to_sql /usr/share/zoneinfo | sudo mysql -u root -p mysql

# 验证导入
mysql -u root -p -e "SELECT COUNT(*) FROM mysql.time_zone_name;"
```

### CentOS/RHEL

```bash
# 安装必要的包
sudo yum install mysql tzdata

# 导入时区数据
sudo mysql_tzinfo_to_sql /usr/share/zoneinfo | sudo mysql -u root -p mysql

# 验证导入
mysql -u root -p -e "SELECT COUNT(*) FROM mysql.time_zone_name;"
```

### 通用 Linux 方法

```bash
# 1. 检查 zoneinfo 目录位置
ls /usr/share/zoneinfo

# 2. 导入时区数据
mysql_tzinfo_to_sql /usr/share/zoneinfo | mysql -u root -p mysql

# 3. 验证导入
mysql -u root -p -e "SELECT name FROM mysql.time_zone_name WHERE name LIKE 'Asia/Shanghai';"
```

### 如果 MySQL 使用 socket 连接

```bash
# 指定 socket 路径
sudo mysql_tzinfo_to_sql /usr/share/zoneinfo | sudo mysql -u root -p --socket=/var/run/mysqld/mysqld.sock mysql
```

### 验证命令执行结果

```bash
mysql -u root -p -e "
SELECT COUNT(*) AS total_time_zones FROM mysql.time_zone;
SELECT COUNT(*) AS total_time_zone_names FROM mysql.time_zone_name;
SELECT name FROM mysql.time_zone_name WHERE name = 'Asia/Shanghai';
"
```

预期结果：
- `total_time_zones` 应该 > 0（通常几百条）
- `total_time_zone_names` 应该 > 0（通常几百条）
- `Asia/Shanghai` 应该存在

### 如果命令找不到

如果系统提示 `mysql_tzinfo_to_sql: command not found`：

```bash
# 查找命令位置
which mysql_tzinfo_to_sql
# 或
whereis mysql_tzinfo_to_sql

# 如果找不到，尝试使用完整路径
# Ubuntu/Debian
sudo /usr/bin/mysql_tzinfo_to_sql /usr/share/zoneinfo | sudo mysql -u root -p mysql

# CentOS/RHEL
sudo /usr/bin/mysql_tzinfo_to_sql /usr/share/zoneinfo | sudo mysql -u root -p mysql
```

### 完成后重启服务

```bash
# 重启 MySQL 服务
sudo systemctl restart mysql
# 或
sudo systemctl restart mysqld
# 或
sudo service mysql restart
```

---

## macOS 系统

### 使用 Homebrew 安装的 MySQL

```bash
# 导入时区数据
mysql_tzinfo_to_sql /usr/share/zoneinfo | mysql -u root -p mysql

# 验证导入
mysql -u root -p -e "SELECT COUNT(*) FROM mysql.time_zone_name;"
```

### 使用官方安装包的 MySQL

```bash
# 查找 zoneinfo 目录
ls /usr/share/zoneinfo

# 导入时区数据
mysql_tzinfo_to_sql /usr/share/zoneinfo | mysql -u root -p mysql
```

---

## Docker 环境

### 使用 Docker Compose

在 `docker-compose.yml` 中添加时区数据导入：

```yaml
services:
  db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: your_password
    volumes:
      - ./init-timezone.sql:/docker-entrypoint-initdb.d/init-timezone.sql
```

创建 `init-timezone.sql` 文件：

```sql
-- 在宿主机上生成时区数据
-- mysql_tzinfo_to_sql /usr/share/zoneinfo > init-timezone.sql
```

### 手动导入到 Docker 容器

```bash
# 进入容器
docker exec -it <container_name> bash

# 导入时区数据
mysql_tzinfo_to_sql /usr/share/zoneinfo | mysql -u root -p mysql

# 退出容器
exit
```

---

## 验证时区数据安装

执行以下 SQL 命令验证时区数据是否正确安装：

```sql
-- 1. 检查时区表是否有数据
SELECT COUNT(*) AS total_time_zones FROM mysql.time_zone;
SELECT COUNT(*) AS total_time_zone_names FROM mysql.time_zone_name;

-- 2. 检查特定时区是否存在
SELECT * FROM mysql.time_zone_name WHERE name = 'Asia/Shanghai';

-- 3. 测试时区转换
SELECT CONVERT_TZ(NOW(), 'UTC', 'Asia/Shanghai') AS shanghai_time;

-- 4. 查看所有可用的时区
SELECT name FROM mysql.time_zone_name ORDER BY name LIMIT 20;
```

预期结果：
- `total_time_zones` 应该 > 0（通常几百条）
- `total_time_zone_names` 应该 > 0（通常几百条）
- `Asia/Shanghai` 应该存在
- `CONVERT_TZ` 应该返回正确的时间，而不是 NULL

---

## 常见问题解决

### 问题 1：找不到 mysql_tzinfo_to_sql 命令

**解决方案：**
```bash
# 查找命令位置
which mysql_tzinfo_to_sql
# 或
whereis mysql_tzinfo_to_sql

# 如果找不到，从 MySQL 官网下载
```

### 问题 2：权限不足

**解决方案：**
```bash
# 使用 sudo
sudo mysql_tzinfo_to_sql /usr/share/zoneinfo | sudo mysql -u root -p mysql
```

### 问题 3：导入后仍然报错

**解决方案：**
```sql
-- 重启 MySQL 服务
-- Linux
sudo systemctl restart mysql

-- Windows
# 在服务管理器中重启 MySQL 服务

-- macOS
brew services restart mysql
```

### 问题 4：Windows 上找不到 zoneinfo 目录

**解决方案：**
```cmd
# 1. 下载 MySQL 时区数据
# 从 https://dev.mysql.com/downloads/timezones/ 下载

# 2. 解压并导入
mysql -u root -p mysql < timezone_data.sql
```

---

## 替代方案（如果无法修复 MySQL 时区）

如果无法修复 MySQL 时区定义，可以使用以下替代方案：

### 方案 A：禁用 Django 时区支持

修改 `settings.py`：
```python
USE_TZ = False
```

**缺点：** 失去时区转换功能，所有时间以服务器本地时间存储。

### 方案 B：移除 Admin 中的 date_hierarchy

从所有 Admin 类中移除 `date_hierarchy` 配置。

**缺点：** 失去时间分层导航功能。

---

## 推荐操作步骤

### 对于 Windows 用户

1. **优先尝试方法 1**：使用 `mysql_tzinfo_to_sql` 导入时区数据
2. **如果失败**：从 Linux 系统导出时区数据，然后导入到 Windows
3. **最后选择**：禁用 `USE_TZ` 或移除 `date_hierarchy`

### 对于 Linux/macOS 用户

1. **直接执行**：`mysql_tzinfo_to_sql /usr/share/zoneinfo | mysql -u root -p mysql`
2. **验证安装**：执行验证 SQL 命令
3. **重启服务**：重启 MySQL 和 Django 服务

---

## 完成后的验证

修复完成后，执行以下步骤验证：

1. **验证 MySQL 时区数据**
   ```sql
   SELECT COUNT(*) FROM mysql.time_zone_name;
   ```

2. **重启 Django 服务**
   ```bash
   python manage.py runserver
   ```

3. **访问 Admin 页面**
   - 访问之前报错的 Admin 页面
   - 确认不再出现时区错误

4. **测试时区功能**
   - 创建包含时间字段的记录
   - 确认时间正确显示和存储

---

## 相关资源

- [MySQL 官方文档 - 时区](https://dev.mysql.com/doc/refman/8.0/en/time-zone-support.html)
- [Django 文档 - 时区](https://docs.djangoproject.com/en/stable/topics/i18n/timezones/)
- [MySQL 时区数据下载](https://dev.mysql.com/downloads/timezones/)

---

## 联系支持

如果按照以上步骤仍然无法解决问题，请检查：
1. MySQL 版本是否支持时区功能
2. 是否有足够的权限导入时区数据
3. MySQL 配置文件中是否有相关限制
