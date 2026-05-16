# Week 5 精准测试前端 — ChangeAnalyses.vue 测试用例

## 一、API 测试

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|--------|--------|--------|--------|--------|--------|--------|
| CHANGE_API_001 | 验证变更分析列表查询API | Django服务运行，存在分析记录 | GET /api/precision-testing/analyses/?page=1&page_size=20 | 返回200，results数组包含分析记录，每条包含id/commit_hash/branch/status/created_at字段 | P0 | API测试 | 变更分析 |
| CHANGE_API_002 | 验证变更分析列表搜索功能 | 存在commit_hash包含"abc"的记录 | GET /api/precision-testing/analyses/?search=abc | 返回200，results中所有记录commit_hash或branch包含"abc" | P1 | API测试 | 变更分析 |
| CHANGE_API_003 | 验证变更分析列表分页 | 分析记录超过20条 | GET /api/precision-testing/analyses/?page=2&page_size=10 | 返回200，results长度为10，count为总记录数 | P1 | API测试 | 变更分析 |
| CHANGE_API_004 | 验证单条变更分析详情API | 存在id=1的分析记录 | GET /api/precision-testing/analyses/1/ | 返回200，详情包含commit_hash/branch/commit_time/commit_message/changed_files数组 | P0 | API测试 | 变更分析 |
| CHANGE_API_005 | 验证变更分析详情-changed_files结构 | 分析记录包含变更文件 | GET /api/precision-testing/analyses/{id}/ | changed_files数组中每项包含path/added/removed/functions数组，functions包含name/change_type/start_line | P0 | API测试 | 变更分析 |
| CHANGE_API_006 | 验证变更分析详情-无变更文件 | 新建分析但无代码变更 | GET /api/precision-testing/analyses/{id}/ | changed_files为空数组[]，changed_files_count为0 | P1 | API测试 | 变更分析 |
| CHANGE_API_007 | 验证变更分析详情-不存在的ID | 不存在id=99999的分析 | GET /api/precision-testing/analyses/99999/ | 返回404 NotFound | P1 | API测试 | 变更分析 |
| CHANGE_API_008 | 验证分析进度查询-API running | 存在id=1的running状态分析 | GET /api/precision-testing/analyses/1/progress/ | 返回200，status为"running"，包含progress数值 | P0 | API测试 | 变更分析 |
| CHANGE_API_009 | 验证分析进度查询-API pending | 存在id=1的pending状态分析 | GET /api/precision-testing/analyses/1/progress/ | 返回200，status为"pending"，progress可能为0 | P1 | API测试 | 变更分析 |
| CHANGE_API_010 | 验证分析进度查询-API completed | 存在id=1的completed状态分析 | GET /api/precision-testing/analyses/1/progress/ | 返回200，status为"completed"，progress为100 | P0 | API测试 | 变更分析 |
| CHANGE_API_011 | 验证分析进度查询-API failed | 存在id=1的failed状态分析 | GET /api/precision-testing/analyses/1/progress/ | 返回200，status为"failed"，包含error_message字段 | P0 | API测试 | 变更分析 |
| CHANGE_API_012 | 验证变更分析列表API-未授权访问 | 不携带Token | GET /api/precision-testing/analyses/ | 返回401 Unauthorized | P0 | 安全测试 | 权限校验 |

## 二、手动功能验证

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|--------|--------|--------|--------|--------|--------|--------|
| CHANGE_UI_001 | 验证变更分析页面默认加载左侧列表 | 用户已登录，进入变更分析页面 | 直接访问/precision-testing/analyses | 左侧列表加载完成，显示分析记录，右侧详情区显示"请选择左侧分析记录查看详情" | P0 | 手动功能验证 | 变更分析 |
| CHANGE_UI_002 | 验证变更分析左侧列表loading状态 | 列表加载中 | 进入变更分析页面，快速查看 | 左侧列表显示loading遮罩（el-loading），加载完成后消失 | P0 | 手动功能验证 | 变更分析 |
| CHANGE_UI_003 | 验证变更分析左侧列表搜索-防抖 | 列表已加载 | 1. 在搜索框输入"main"<br>2. 等待400ms | 接口被触发，列表更新为包含"main"的记录 | P0 | 手动功能验证 | 变更分析 |
| CHANGE_UI_004 | 验证点击左侧列表项选中高亮 | 列表存在至少2条记录 | 1. 点击第1条记录<br>2. 点击第2条记录 | 被点击项添加active背景色（el-color-primary-light-9），之前选中项取消高亮 | P0 | 手动功能验证 | 变更分析 |
| CHANGE_UI_005 | 验证选中分析记录后加载详情 | 列表存在completed状态记录 | 点击某条记录 | 右侧详情面板更新，detailLoading遮罩出现然后消失，显示该记录的完整详情 | P0 | 手动功能验证 | 变更分析 |
| CHANGE_UI_006 | 验证详情面板-基本信息展示 | 某条记录已选中 | 查看右侧详情面板 | 显示提交哈希/分支/提交时间/触发时间/变更文件数/变更函数数/提交信息 | P0 | 手动功能验证 | 变更分析 |
| CHANGE_UI_007 | 验证详情面板-提交哈希显示格式 | 某条记录已选中 | 查看提交哈希字段 | 显示完整40位commit_hash或截断显示前8位（el-text-overflow） | P1 | 手动功能验证 | 变更分析 |
| CHANGE_UI_008 | 验证详情面板-时间格式化 | 某条记录已选中，包含commit_time | 查看提交时间字段 | 显示格式为"YYYY-MM-DD HH:mm"，非空时间不显示"-" | P1 | 手动功能验证 | 变更分析 |
| CHANGE_UI_009 | 验证变更文件折叠列表-展开 | 某条记录已选中，changed_files有数据 | 1. 查看变更文件折叠面板<br>2. 点击某个折叠项 | 折叠面板展开，显示该文件的变更函数表格（函数名/变更类型/起始行） | P0 | 手动功能验证 | 变更分析 |
| CHANGE_UI_010 | 验证变更文件折叠列表-收起 | 某文件已展开 | 点击已展开文件标题栏 | 文件折叠，函数表格隐藏 | P1 | 手动功能验证 | 变更分析 |
| CHANGE_UI_011 | 验证变更文件折叠列表-多项折叠 | 某条记录有3个以上变更文件 | 展开第1个文件，依次展开其他文件 | 每个文件独立展开/收起，展开状态互不影响 | P1 | 手动功能验证 | 变更分析 |
| CHANGE_UI_012 | 验证变更类型标签颜色-added | 某条记录的函数change_type为added | 查看变更函数表格change_type列 | 显示绿色标签（el-tag type=success） | P1 | 手动功能验证 | 变更分析 |
| CHANGE_UI_013 | 验证变更类型标签颜色-modified | 某条记录的函数change_type为modified | 查看变更函数表格change_type列 | 显示橙色/黄色标签（el-tag type=warning） | P1 | 手动功能验证 | 变更分析 |
| CHANGE_UI_014 | 验证变更类型标签颜色-deleted | 某条记录的函数change_type为deleted | 查看变更函数表格change_type列 | 显示红色标签（el-tag type=danger） | P1 | 手动功能验证 | 变更分析 |
| CHANGE_UI_015 | 验证运行中状态进度轮询 | 存在running状态的记录 | 1. 点击该记录<br>2. 查看详情区进度卡片 | 显示el-progress条，进度百分比递增，状态文字更新 | P0 | 手动功能验证 | 变更分析 |
| CHANGE_UI_016 | 验证等待中状态进度显示 | 存在pending状态的记录 | 点击该记录 | 详情区显示进度条（progress为0或较低），状态文字为"pending"或"等待中" | P1 | 手动功能验证 | 变更分析 |
| CHANGE_UI_017 | 验证分析完成时自动刷新列表 | 某条running记录即将完成 | 1. 点击该记录查看进度<br>2. 等待进度变为completed | 状态更新后，轮询立即停止，左侧列表该记录状态自动变为"completed"绿色标签 | P0 | 手动功能验证 | 变更分析 |
| CHANGE_UI_018 | 验证分析失败时停止轮询 | 存在failed状态的记录 | 轮询进行中分析变为failed | 轮询停止，连续3次错误后顶部出现"进度查询失败，已停止轮询"警告提示 | P0 | 手动功能验证 | 变更分析 |
| CHANGE_UI_019 | 验证未选中记录时详情为空 | 列表已加载，未点击任何记录 | 不点击任何列表项，直接查看右侧 | 显示空状态文案"请选择左侧分析记录查看详情"（el-empty） | P0 | 手动功能验证 | 变更分析 |
| CHANGE_UI_020 | 验证切换记录时停止旧轮询 | 已有running状态记录在轮询中 | 1. 点击running记录开始轮询<br>2. 在轮询进行中立即点击另一条记录 | 旧记录的轮询立即停止（pollingToken自增），新记录开始自己的轮询 | P0 | 手动功能验证 | 变更分析 |
| CHANGE_UI_021 | 验证左侧列表空状态 | 无任何分析记录 | 访问/precision-testing/analyses（确认无数据） | 左侧列表显示"暂无分析记录"空状态提示 | P1 | 手动功能验证 | 变更分析 |
| CHANGE_UI_022 | 验证左侧列表分页 | 分析记录超过20条 | 点击分页"下一页" | 列表更新，显示第2页记录，分页器当前页为2 | P1 | 手动功能验证 | 变更分析 |
| CHANGE_UI_023 | 验证状态标签completed显示 | 某条completed记录 | 查看列表项状态标签 | 显示绿色"已完成"标签（el-tag type=success） | P1 | 手动功能验证 | 变更分析 |
| CHANGE_UI_024 | 验证状态标签failed显示 | 某条failed记录 | 查看列表项状态标签 | 显示红色"失败"标签（el-tag type=danger） | P1 | 手动功能验证 | 变更分析 |
| CHANGE_UI_025 | 验证状态标签running显示 | 某条running记录 | 查看列表项状态标签 | 显示蓝色"运行中"标签（el-tag type=primary） | P1 | 手动功能验证 | 变更分析 |
| CHANGE_UI_026 | 验证状态标签pending显示 | 某条pending记录 | 查看列表项状态标签 | 显示灰色"等待中"标签（el-tag type=info） | P1 | 手动功能验证 | 变更分析 |
| CHANGE_UI_027 | 验证详情加载失败错误提示 | 选中某条记录但详情API失败 | 点击列表某项，模拟详情API 500错误 | 顶部出现"加载详情失败"错误提示，详情区保持空或显示上次数据 | P1 | 手动功能验证 | 变更分析 |
| CHANGE_UI_028 | 验证详情加载超时处理 | 详情API响应超过30s | 点击列表某项，通过代理延迟响应至35秒 | 显示"加载详情失败"错误提示，不是长时间loading | P2 | 手动功能验证 | 变更分析 |

## 三、E2E测试

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|--------|--------|--------|--------|--------|--------|--------|
| CHANGE_E2E_001 | 端到端查看变更分析详情流程 | 存在至少1条completed状态的分析记录 | 1. 进入变更分析页面<br>2. 点击左侧某条记录<br>3. 等待详情加载<br>4. 展开某个变更文件 | 详情面板显示完整信息，折叠面板展开后显示函数名/变更类型/起始行 | P0 | E2E测试 | 变更分析 |
| CHANGE_E2E_002 | 端到端running状态进度跟踪 | 存在可触发分析的仓库 | 1. 进入仓库绑定页面<br>2. 触发一次分析<br>3. 进入变更分析页面<br>4. 找到对应记录查看进度 | 详情区实时显示分析进度，直到完成或失败 | P0 | E2E测试 | 变更分析 |
| CHANGE_E2E_003 | 端到端切换分析记录流程 | 存在至少2条分析记录 | 1. 点击第1条记录查看详情<br>2. 快速点击第2条记录<br>3. 查看详情面板 | 详情面板内容切换为第2条记录，旧轮询停止，无数据混乱 | P0 | E2E测试 | 变更分析 |

## 四、异常场景测试

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|--------|--------|--------|--------|--------|--------|--------|
| CHANGE_ERR_001 | 验证列表加载网络失败 | 列表加载中 | 1. 进入变更分析页面<br>2. 切换到Offline模式<br>3. 刷新页面 | 显示错误提示"加载分析记录失败"，左侧列表区域显示空状态 | P0 | 容错测试 | 变更分析 |
| CHANGE_ERR_002 | 验证详情加载网络失败 | 某条记录已选中 | 1. 点击列表某项<br>2. 切换到Offline模式<br>3. 等待详情请求发出 | 顶部显示"加载详情失败"错误提示 | P0 | 容错测试 | 变更分析 |
| CHANGE_ERR_003 | 验证进度轮询连续网络抖动 | 进度轮询进行中 | 连续3次网络抖动（每次请求失败） | 第3次失败后停止轮询，顶部出现"进度查询失败，已停止轮询"警告 | P0 | 容错测试 | 变更分析 |
| CHANGE_ERR_004 | 验证切换记录时旧轮询令牌失效 | running状态记录在轮询中 | 1. 点击running记录开始轮询<br>2. 立即切换到另一条running记录 | 旧轮询响应回来后不更新状态（token不匹配），新轮询正常进行 | P1 | 容错测试 | 变更分析 |
| CHANGE_ERR_005 | 验证页面卸载时清理轮询定时器 | running状态记录在轮询中 | 1. 开始进度轮询<br>2. 路由跳转离开页面<br>3. 用开发者工具确认仍有定时器 | 路由离开后定时器被清除（内存无泄漏），无未清理的setTimeout | P1 | 容错测试 | 变更分析 |