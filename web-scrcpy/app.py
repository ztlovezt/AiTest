from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, send
from scrcpy import Scrcpy
import argparse
import queue
import os
import json
import subprocess
import uuid
import re
import socket

scpy_ctx = None
clients = {}  # 存储所有客户端
message_queue = queue.Queue()
video_bit_rate = "1024000"
video_task_started = False

# 邮箱配置文件路径
EMAIL_CONFIG_FILE = 'email_mapping.json'

# 存储待处理的重新连接请求
pending_requests = {}

# 服务器本机局域网IP
SERVER_IP = None

# 默认邮箱
DEFAULT_EMAIL = 'jack@openvision.cc'

# 获取本机局域网IP（优先获取真实内网IP，排除虚拟网卡/VPN等）
def get_local_ip():
    try:
        # 遍历所有网络接口
        import subprocess
        result = subprocess.run(['ipconfig'], capture_output=True, text=True, timeout=5)
        output = result.stdout

        # 提取所有IPv4地址
        ips = []
        lines = output.split('\n')
        for line in lines:
            # 同时匹配 IPv4、IPv4 地址、IP Address
            if 'IPv4' in line or 'IPv4 地址' in line or 'IP Address' in line:
                # 找到IP所在的行
                parts = line.split(':')
                if len(parts) >= 2:
                    ip = parts[1].strip()
                    # 过滤有效的内网IP（192.168.x.x, 10.x.x.x, 172.16-31.x.x）
                    if ip and (ip.startswith('192.168.') or ip.startswith('10.') or
                              (ip.startswith('172.') and 16 <= int(ip.split('.')[1]) <= 31)):
                        # 排除常见虚拟网卡段
                        if not ip.startswith('192.168.56.') and not ip.startswith('192.168.137.'):
                            ips.append(ip)

        # 如果找到内网IP
        if ips:
            print(f'Found local IPs: {ips}')
            # 优先返回 192.168.3.x 段（如果存在），因为用户说主服务机器是 192.168.3.46
            for ip in ips:
                if ip.startswith('192.168.3.'):
                    return ip
            # 否则返回第一个
            return ips[0]

        # 方法2：如果方法1失败，使用socket连接方式作为备选
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        print(f'Error getting local IP: {e}')
        return "127.0.0.1"

# 初始化服务器IP
SERVER_IP = get_local_ip()
print(f'Server local IP: {SERVER_IP}')

# 读取邮箱配置
def get_email_mapping():
    if os.path.exists(EMAIL_CONFIG_FILE):
        try:
            with open(EMAIL_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

# 保存邮箱配置
def save_email_mapping(mapping):
    try:
        with open(EMAIL_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f'Error saving email config: {e}')

# 获取当前已连接的客户端IP（从配置文件中读取）
def get_connected_ip():
    mapping = get_email_mapping()
    return mapping.get('_current_connection_ip')

# 设置当前已连接的客户端IP（保存到配置文件中）
def set_connected_ip(ip):
    mapping = get_email_mapping()
    mapping['_current_connection_ip'] = ip
    save_email_mapping(mapping)
    print(f'Set current connection IP: {ip}')

# 从邮箱提取英文名
def get_english_name(email):
    if '@' in email:
        return email.split('@')[0]
    return email

# 注意：不再自动清空配置文件，配置持久化
# 如果需要清空，可以手动删除 email_mapping.json 文件

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=None)

@app.route('/')
def index():
    return render_template('index.html')

def video_send_task():
    global clients, video_task_started
    print('video_send_task started')
    while len(clients) > 0:
        try:
            message = message_queue.get_nowait()
            # 向所有客户端发送视频
            for sid in list(clients.keys()):
                try:
                    socketio.emit('video_data', message, to=sid)
                except Exception as e:
                    print(f'Error sending to {sid}: {e}')
        except queue.Empty:
            pass
        except Exception as e:
            print(f"Error: {e}")
        socketio.sleep(0.001)
    video_task_started = False
    print('video_send_task stopped')

def send_video_data(data):
    message_queue.put(data)

@socketio.on('connect')
def handle_connect():
    global scpy_ctx, clients, video_task_started
    client_ip = request.environ.get('REMOTE_ADDR', 'unknown')
    # 尝试获取真实IP（如果使用了代理）
    if request.environ.get('HTTP_X_FORWARDED_FOR'):
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR').split(',')[0].strip()
    
    # 如果客户端IP是回环地址，视为服务器本机
    if client_ip in ['127.0.0.1', '::1', '::ffff:127.0.0.1']:
        client_ip = SERVER_IP
    
    print(f'Client connected: {request.sid} from {client_ip}')
    print(f'Server IP (SERVER_IP): {SERVER_IP}')
    print(f'Is main device: {client_ip == SERVER_IP}')
    
    # 通知前端是否是主服务机器
    is_main_device = (client_ip == SERVER_IP)
    emit('device_type', {'is_admin': is_main_device})

    # 检查邮箱配置文件
    mapping = get_email_mapping()

    # 获取当前已连接的IP（从配置文件中读取）
    connected_ip = get_connected_ip()

    # 检查客户端IP是否已在配置文件中记录（已连接过）
    client_in_config = client_ip in mapping

    # 检查当前IP是否已经在clients中（刷新页面时）
    if client_ip in [clients[sid].get('ip') for sid in clients.keys()]:
        print(f'Client {client_ip} already connected, skipping...')
        # 更新sid映射
        old_sid = None
        for sid in clients.keys():
            if clients[sid].get('ip') == client_ip:
                old_sid = sid
                break
        if old_sid:
            clients.pop(old_sid, None)
        clients[request.sid] = {'ip': client_ip}
        emit('connection_accepted', {'message': '连接成功'})
        return

    # 如果没有客户端连接（首次启动或之前已有人连接过）
    if len(clients) == 0:
        if is_main_device:
            # 主服务机器：直接连接
            mapping[client_ip] = DEFAULT_EMAIL
            save_email_mapping(mapping)
            print(f'Main device connected directly: {client_ip}')
        elif not client_in_config:
            # 其他机器首次连接需要填写邮箱
            emit('need_email', {'ip': client_ip})
            print(f'New client needs email configuration: {client_ip}')
            return
        # 其他情况（已填写过邮箱的机器或主服务机器）：直接连接
        
        # 添加客户端
        clients[request.sid] = {'ip': client_ip}
        
        # 记录当前连接的IP到配置文件
        set_connected_ip(client_ip)
        
        # 广播当前连接的客户端
        emit_current_client()
        
        # 启动 scrcpy
        try:
            scpy_ctx = Scrcpy()
            scpy_ctx.scrcpy_start(send_video_data, video_bit_rate)
            print(f'Scrcpy started for {client_ip}')
        except Exception as e:
            print(f'Error starting scrcpy: {e}')
            clients.pop(request.sid, None)
            set_connected_ip('')
        
        # 启动视频发送任务
        if not video_task_started:
            video_task_started = True
            socketio.start_background_task(video_send_task)
        
        # 通知客户端连接成功
        emit('connection_accepted', {'message': '连接成功'})
        return
    else:
        print(f'Known client: {client_ip} ({mapping.get(client_ip, "unknown")})')

    # 如果已有客户端连接
    old_sid = list(clients.keys())[0]
    old_ip = clients[old_sid].get('ip', 'unknown')

    # 如果是主服务机器重新连接，强制踢掉其他所有客户端
    if is_main_device:
        print(f'Admin device connected, kicking other clients')
        # 通知其他客户端被踢掉
        for sid in list(clients.keys()):
            socketio.emit('connection_rejected', {
                'reason': 'admin_reclaimed',
                'message': '管理员已重新夺回操作权'
            }, to=sid)
            clients.pop(sid, None)

        # 清除客户端，添加主服务机器
        clients.clear()
        clients[request.sid] = {'ip': client_ip}
        
        # 记录当前连接的IP到配置文件
        set_connected_ip(client_ip)

        # 停止旧的scrcpy并重新启动
        if scpy_ctx is not None:
            try:
                scpy_ctx.scrcpy_stop()
            except:
                pass
            scpy_ctx = None

        # 广播当前连接的客户端
        emit_current_client()

        try:
            scpy_ctx = Scrcpy()
            scpy_ctx.scrcpy_start(send_video_data, video_bit_rate)
            print(f'Scrcpy started for admin client {request.sid}')
        except Exception as e:
            print(f'Error starting scrcpy: {e}')
            clients.pop(request.sid, None)
        
        # 启动视频发送任务
        if not video_task_started:
            video_task_started = True
            socketio.start_background_task(video_send_task)
        return

    # 如果是同一个客户端（同一个IP），直接切换
    if old_ip == client_ip:
        print(f'Same client reconnected: {client_ip}')
        # 清除旧客户端，添加新客户端
        clients.clear()
        clients[request.sid] = {'ip': client_ip}

        # 停止旧的scrcpy
        if scpy_ctx is not None:
            try:
                scpy_ctx.scrcpy_stop()
            except:
                pass
            scpy_ctx = None

        # 启动 scrcpy
        try:
            scpy_ctx = Scrcpy()
            scpy_ctx.scrcpy_start(send_video_data, video_bit_rate)
            print(f'Scrcpy restarted for client {request.sid}')
        except Exception as e:
            print(f'Error starting scrcpy: {e}')
            clients.pop(request.sid, None)
        
        # 启动视频发送任务
        if not video_task_started:
            video_task_started = True
            socketio.start_background_task(video_send_task)
        return

    # 不同客户端：发送请求给旧客户端，等待确认
    print(f'New client wants to connect: {client_ip}, asking {old_sid} ({old_ip})')
    request_id = str(uuid.uuid4())
    pending_connection_request = {
        'request_id': request_id,
        'new_ip': client_ip,
        'new_email': mapping.get(client_ip, 'unknown'),
        'new_english_name': get_english_name(mapping.get(client_ip, 'unknown')),
        'new_sid': request.sid
    }
    pending_requests[request_id] = pending_connection_request

    # 向旧客户端发送请求
    socketio.emit('connection_request', {
        'request_id': request_id,
        'email': mapping.get(client_ip, 'unknown'),
        'ip': client_ip,
        'english_name': get_english_name(mapping.get(client_ip, 'unknown'))
    }, to=old_sid)
    print(f'Sent connection_request to {old_sid}')

    # 暂时不添加新客户端，不启动scrcpy，等待确认
    # 新客户端等待连接请求结果
    emit('waiting_approval', {'message': '等待当前用户同意连接...'})
    return

    # 如果scrcpy已启动，先停止
    if scpy_ctx is not None:
        try:
            scpy_ctx.scrcpy_stop()
        except:
            pass
        scpy_ctx = None

    # 启动 scrcpy
    try:
        scpy_ctx = Scrcpy()
        scpy_ctx.scrcpy_start(send_video_data, video_bit_rate)
        print(f'Scrcpy started for client {request.sid}')
    except Exception as e:
        print(f'Error starting scrcpy: {e}')
        clients.pop(request.sid, None)
        emit_current_client()
        return False
    
    # 启动视频发送任务
    if not video_task_started:
        video_task_started = True
        socketio.start_background_task(video_send_task)
    
    # 通知当前客户端连接成功
    socketio.emit('connection_accepted', to=request.sid)
    print(f'Current client: {client_ip}')

@socketio.on('disconnect')
def handle_disconnect():
    global scpy_ctx, clients, video_task_started
    
    if request.sid in clients:
        client_ip = clients[request.sid].get('ip', 'unknown')
        clients.pop(request.sid)
        print(f'Client disconnected: {request.sid} ({client_ip})')
        emit_current_client()
    
    # 所有客户端断开时停止 scrcpy 并清除连接记录
    if len(clients) == 0:
        set_connected_ip('')
        if scpy_ctx is not None:
            try:
                scpy_ctx.scrcpy_stop()
                print('Scrcpy stopped')
            except Exception as e:
                print(f'Error stopping scrcpy: {e}')
            scpy_ctx = None
            video_task_started = False

def emit_current_client():
    """向所有客户端发送当前连接的客户端"""
    if len(clients) > 0:
        sid = list(clients.keys())[0]
        info = clients[sid]
        mapping = get_email_mapping()
        client_email = mapping.get(info.get('ip', ''), '')
        client_english_name = get_english_name(client_email)
        client_data = {
            'sid': sid,
            'ip': info.get('ip', 'unknown'),
            'english_name': client_english_name
        }
    else:
        client_data = None
    socketio.emit('current_client', client_data)
    # 同时广播当前连接信息给所有连接的客户端
    socketio.emit('connection_info', {
        'current_client': client_data,
        'has_connection': len(clients) > 0
    })

@socketio.on('control_data')
def handle_control_data(data):
    global scpy_ctx, clients

    # 检查客户端是否已连接（只有当前连接的客户端才能发送控制指令）
    client_sid = request.sid
    if client_sid not in clients:
        print(f'Rejected control data from disconnected client: {client_sid}')
        return

    # 处理旋转命令
    try:
        if isinstance(data, (bytes, bytearray)) and len(data) >= 2:
            msg_type = data[0]
            if msg_type == 100:  # 旋转命令 - 使用scrcpy控制协议
                direction = data[1]  # 0=左/逆时针, 1=右/顺时针
                try:
                    # 通过scrcpy控制socket发送旋转命令
                    # Scrcpy旋转协议: msg_type=0x10 (16), 然后跟1个字节的旋转值
                    # 旋转值: 0=0°, 1=90°, 2=180°, 3=270°
                    if scpy_ctx and scpy_ctx.control_socket:
                        # 计算新旋转角度
                        # 0=左(逆时针90°), 1=右(顺时针90°)
                        rotation_value = 1 if direction == 1 else 3  # 90° or 270°
                        
                        # 构造scrcpy旋转命令包
                        rotation_cmd = bytes([0x10, rotation_value])
                        scpy_ctx.control_socket.send(rotation_cmd)
                        print(f'Sent rotation command to scrcpy: {rotation_value * 90} degrees')
                    else:
                        # 备用：使用ADB命令
                        device_id = ''
                        if hasattr(scpy_ctx, 'device_id') and scpy_ctx.device_id:
                            device_id = scpy_ctx.device_id
                        
                        # 使用surfaceflinger或wm命令旋转
                        cmd = ['adb']
                        if device_id:
                            cmd.extend(['-s', device_id])
                        
                        if direction == 0:  # 向左 - 逆时针
                            cmd.extend(['scrcpy', '-s', device_id, '--rotation', '1'])
                        else:  # 向右 - 顺时针
                            cmd.extend(['scrcpy', '-s', device_id, '--rotation', '3'])
                        
                        subprocess.run(cmd, capture_output=True, timeout=5)
                        print(f'Rotated screen via ADB: {"left" if direction == 0 else "right"}')
                except Exception as e:
                    print(f'Error rotating screen: {e}')
                return
    except Exception as e:
        print(f'Error processing control data: {e}')

    if scpy_ctx:
        scpy_ctx.scrcpy_send_control(data)

# 用户提交邮箱
@socketio.on('submit_email')
def handle_submit_email(data):
    email = data.get('email', '')
    client_ip = request.environ.get('REMOTE_ADDR', 'unknown')
    
    # 如果客户端IP是回环地址，视为服务器本机
    if client_ip in ['127.0.0.1', '::1', '::ffff:127.0.0.1']:
        client_ip = SERVER_IP

    # 验证邮箱格式
    if not email or not re.match(r'^[a-zA-Z0-9._%+-]+@openvision\.cc$', email):
        emit('email_result', {'success': False, 'message': '邮箱格式错误'})
        return

    # 更新邮箱配置
    mapping = get_email_mapping()
    
    # 检查邮箱是否已被其他IP使用
    old_ip = None
    for ip, bound_email in mapping.items():
        if ip.startswith('_'):  # 跳过系统字段
            continue
        if bound_email == email and ip != client_ip:
            old_ip = ip
            break
    
    # 如果邮箱已被其他IP使用，移除旧绑定
    if old_ip:
        del mapping[old_ip]
        print(f'Removed old binding: {old_ip} -> {email}')
    
    # 绑定邮箱到当前IP
    mapping[client_ip] = email
    save_email_mapping(mapping)

    # 提示用户点击刷新按钮发起请求（而不是自动发起）
    emit('email_result', {'success': True, 'message': '请点击刷新按钮发起连接请求'})
    print(f'Email set for {client_ip}: {email}' + (f' (replaced {old_ip})' if old_ip else ''))

# 获取本机IP
@socketio.on('get_my_ip')
def handle_get_my_ip():
    client_ip = request.environ.get('REMOTE_ADDR', 'unknown')
    # 如果客户端IP是回环地址，视为服务器本机
    if client_ip in ['127.0.0.1', '::1', '::ffff:127.0.0.1']:
        client_ip = SERVER_IP
    emit('my_ip', client_ip)

# 管理员夺回连接（点击按钮直接夺回，不需要对方同意）
@socketio.on('admin_reclaim')
def handle_admin_reclaim(data):
    global scpy_ctx, clients, video_task_started
    client_ip = request.environ.get('REMOTE_ADDR', 'unknown')
    
    # 如果客户端IP是回环地址，视为服务器本机
    if client_ip in ['127.0.0.1', '::1', '::ffff:127.0.0.1']:
        client_ip = SERVER_IP
    
    # 验证是否是主服务机器
    if client_ip != SERVER_IP:
        emit('admin_reclaim_result', {'success': False, 'message': '只有主服务机器才能执行此操作'})
        return
    
    print(f'Admin reclaiming connection, current clients: {list(clients.keys())}')
    
    # 通知其他客户端被踢掉
    for sid in list(clients.keys()):
        socketio.emit('connection_rejected', {
            'reason': 'admin_reclaimed',
            'message': '管理员已重新夺回操作权，请联系管理员获得使用权'
        }, to=sid)
        clients.pop(sid, None)
    
    # 清除并添加主服务机器
    clients.clear()
    clients[request.sid] = {'ip': client_ip}
    
    # 记录当前连接的IP到配置文件
    set_connected_ip(client_ip)
    
    # 停止旧的scrcpy并重新启动
    if scpy_ctx is not None:
        try:
            scpy_ctx.scrcpy_stop()
        except:
            pass
        scpy_ctx = None
    
    # 广播当前连接的客户端
    emit_current_client()
    
    # 启动 scrcpy
    try:
        scpy_ctx = Scrcpy()
        scpy_ctx.scrcpy_start(send_video_data, video_bit_rate)
        print(f'Scrcpy restarted for admin')
    except Exception as e:
        print(f'Error starting scrcpy: {e}')
        clients.pop(request.sid, None)
        set_connected_ip('')
    
    # 启动视频发送任务
    if not video_task_started:
        video_task_started = True
        socketio.start_background_task(video_send_task)
    
    # 通知管理员夺回成功
    emit('admin_reclaim_result', {'success': True, 'message': '已夺回连接权'})

# 重新连接请求（只有点击按钮才会触发）
@socketio.on('request_reconnect')
def handle_request_reconnect(data):
    global pending_requests, clients

    email = data.get('email', '')
    request_ip = data.get('ip', '')
    requester_sid = request.sid
    
    # 如果请求IP是回环地址，视为服务器本机
    if request_ip in ['127.0.0.1', '::1', '::ffff:127.0.0.1']:
        request_ip = SERVER_IP

    # 验证邮箱格式
    if not email or not re.match(r'^[a-zA-Z0-9._%+-]+@openvision\.cc$', email):
        emit('request_result', {'approved': False, 'message': '邮箱格式错误'})
        return

    # 检查当前IP是否已经连接（如果已连接则不需要再请求）
    if request_ip in [clients[sid].get('ip') for sid in clients.keys()]:
        print(f'Client {request_ip} already connected')
        emit('request_result', {'approved': False, 'message': '您已连接，请刷新页面'})
        return

    # 检查邮箱是否已在配置文件中配置（必须是当前IP绑定的邮箱）
    mapping = get_email_mapping()
    bound_email = mapping.get(request_ip)
    if not bound_email:
        # 当前IP未绑定邮箱，提示用户先填写邮箱
        emit('request_result', {'approved': False, 'message': '请先填写邮箱信息'})
        emit('need_email', {'ip': request_ip})
        return
    
    # 检查提交的邮箱是否与当前IP绑定的邮箱一致
    if bound_email != email:
        emit('request_result', {'approved': False, 'message': '当前IP绑定的邮箱不是您提交的邮箱，请重新填写'})
        emit('need_email', {'ip': request_ip})
        return

    # 如果没有客户端连接，直接允许连接
    if len(clients) == 0:
        print(f'No client connected, allowing {request_ip} to connect directly')
        
        # 添加客户端
        clients[requester_sid] = {'ip': request_ip}
        
        # 记录当前连接的IP到配置文件
        set_connected_ip(request_ip)
        
        # 广播当前连接的客户端
        emit_current_client()

        # 启动 scrcpy
        try:
            scpy_ctx = Scrcpy()
            scpy_ctx.scrcpy_start(send_video_data, video_bit_rate)
            print(f'Scrcpy started for new client {requester_sid}')
        except Exception as e:
            print(f'Error starting scrcpy: {e}')
            clients.pop(requester_sid, None)
            set_connected_ip('')
        
        # 启动视频发送任务
        global video_task_started
        if not video_task_started:
            video_task_started = True
            socketio.start_background_task(video_send_task)
        
        # 通知客户端连接成功
        emit('request_result', {'approved': True, 'message': '连接成功'})
        return

    # 向已连接的用户发送请求
    request_id = str(uuid.uuid4())
    pending_requests[request_id] = {
        'email': email,
        'ip': request_ip,
        'english_name': get_english_name(email),
        'timestamp': None,
        'requester_sid': requester_sid
    }

    # 向当前连接的其他客户端发送请求（排除自己）
    print(f'Sending connection_request from {requester_sid} to other clients: {list(clients.keys())}')
    for sid in clients:
        if sid == requester_sid:
            continue  # 跳过发起请求的客户端
        socketio.emit('connection_request', {
            'request_id': request_id,
            'email': email,
            'ip': request_ip,
            'english_name': get_english_name(email)
        }, to=sid)
        print(f'Sent connection_request to {sid}')

# 重新连接响应
@socketio.on('reconnect_response')
def handle_reconnect_response(data):
    global pending_requests, clients, scpy_ctx

    request_id = data.get('request_id')
    approved = data.get('approved', False)
    responder_email = data.get('email', '')

    print(f'Reconnect response: request_id={request_id}, approved={approved}')

    if request_id not in pending_requests:
        return

    request_info = pending_requests[request_id]

    if approved:
        # 允许连接：踢掉当前所有客户端（包括管理员）
        old_clients = list(clients.keys())
        # 获取新用户的英文名
        new_english_name = request_info.get('new_english_name', '新用户')
        for sid in old_clients:
            # 通知旧客户端（管理员）已让出连接
            socketio.emit('request_result', {
                'approved': True,
                'message': f'已让出连接权限，{new_english_name}将接管设备'
            }, to=sid)
            clients.pop(sid, None)

        # 停止当前的scrcpy
        if scpy_ctx is not None:
            try:
                scpy_ctx.scrcpy_stop()
            except:
                pass
            scpy_ctx = None

        # 添加新客户端到clients
        new_sid = request_info.get('new_sid')
        new_ip = request_info.get('new_ip')
        if new_sid:
            clients[new_sid] = {'ip': new_ip}
            # 记录当前连接的IP到配置文件
            set_connected_ip(new_ip)
            print(f'Added new client: {new_sid} ({new_ip})')

        # 广播当前连接的客户端
        emit_current_client()

        # 通知请求者可以连接了
        socketio.emit('request_result', {
            'approved': True,
            'english_name': request_info.get('new_english_name', ''),
            'ip': request_info.get('new_ip', '')
        }, to=new_sid)

        # 启动 scrcpy 给新客户端
        try:
            scpy_ctx = Scrcpy()
            scpy_ctx.scrcpy_start(send_video_data, video_bit_rate)
            print(f'Scrcpy started for new client {new_sid}')
        except Exception as e:
            print(f'Error starting scrcpy: {e}')
            if new_sid:
                clients.pop(new_sid, None)
                # 清除当前连接IP记录
                set_connected_ip('')
        
        # 启动视频发送任务
        global video_task_started
        if not video_task_started:
            video_task_started = True
            socketio.start_background_task(video_send_task)
    else:
        # 拒绝连接时，清除当前连接IP记录（如果没有其他客户端连接）
        if len(clients) == 0:
            set_connected_ip('')
        # 不允许连接：通知请求者（发送拒绝者的英文名和邮箱）
        new_sid = request_info.get('new_sid')
        responder_english_name = get_english_name(responder_email) if responder_email else '未知'
        if new_sid:
            socketio.emit('request_result', {
                'approved': False,
                'english_name': responder_english_name,
                'email': responder_email,
                'denied_by': True  # 标记是被拒绝
            }, to=new_sid)

    # 清理请求
    pending_requests.pop(request_id, None)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Web server for scrcpy')
    parser.add_argument('--video_bit_rate', default="1024000", help='scrcpy video bit rate')
    args = parser.parse_args()
    video_bit_rate = args.video_bit_rate
    socketio.run(app, host='0.0.0.0', port=6899)
