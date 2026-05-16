# Week 5 精准测试前端 — MappingManager.vue 测试用例

## 一、API 测试

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|--------|--------|--------|--------|--------|--------|--------|
| MAPPING_API_001 | 验证用例映射列表查询API | Django服务运行，存在映射记录 | GET /api/precision-testing/mappings/?page=1&page_size=20 | 返回200，results数组包含映射记录，每条包含function_name/file_path/testcase_name/mapping_type/confidence_score/created_at | P0 | API测试 | 用例映射 |
| MAPPING_API_002 | 验证用例映射列表-按mapping_type过滤manual | 存在manual类型的映射记录 | GET /api/precision-testing/mappings/?mapping_type=manual | 返回200，results中所有记录的mapping_type均为"manual" | P1 | API测试 | 用例映射 |
| MAPPING_API_003 | 验证用例映射列表-按mapping_type过滤auto | 存在auto类型的映射记录 | GET /api/precision-testing/mappings/?mapping_type=auto | 返回200，results中所有记录的mapping_type均为"auto" | P1 | API测试 | 用例映射 |
| MAPPING_API_004 | 验证用例映射列表-按mapping_type过滤ai | 存在ai类型的映射记录 | GET /api/precision-testing/mappings/?mapping_type=ai | 返回200，results中所有记录的mapping_type均为"ai" | P1 | API测试 | 用例映射 |
| MAPPING_API_005 | 验证用例映射列表-搜索function_name | 存在函数名包含"login"的映射记录 | GET /api/precision-testing/mappings/?search=login | 返回200，results中所有记录function_name包含"login" | P1 | API测试 | 用例映射 |
| MAPPING_API_006 | 验证用例映射列表-组合过滤 | 存在manual类型+关键词的记录 | GET /api/precision-testing/mappings/?mapping_type=manual&search=test | 返回200，同时满足mapping_type=manual和搜索关键词 | P1 | API测试 | 用例映射 |
| MAPPING_API_007 | 验证用例映射列表分页 | 映射记录超过20条 | GET /api/precision-testing/mappings/?page=2&page_size=10 | 返回200，results长度为10，count为总记录数 | P1 | API测试 | 用例映射 |
| MAPPING_API_008 | 验证新建用例映射API-必填字段完整 | 用户已登录 | POST /api/precision-testing/mappings/，body: {function_name:"apps.users.views:Login.post",file_path:"apps/users/views.py",testcase:1,mapping_type:"manual",confidence_score:1.0} | 返回201，响应体包含新建的映射记录，id字段有值 | P0 | API测试 | 用例映射 |
| MAPPING_API_009 | 验证新建用例映射API-function_name为空 | 用户已登录 | POST /api/precision-testing/mappings/，body: {file_path:"apps/users/views.py",testcase:1,mapping_type:"manual"} | 返回400，响应体包含function_name字段错误提示 | P0 | API测试 | 用例映射 |
| MAPPING_API_010 | 验证新建用例映射API-file_path为空 | 用户已登录 | POST /api/precision-testing/mappings/，body: {function_name:"Login.post",testcase:1,mapping_type:"manual"} | 返回400，响应体包含file_path字段错误提示 | P0 | API测试 | 用例映射 |
| MAPPING_API_011 | 验证新建用例映射API-testcase为空 | 用户已登录 | POST /api/precision-testing/mappings/，body: {function_name:"Login.post",file_path:"apps/users/views.py",mapping_type:"manual"} | 返回400，响应体包含testcase字段错误提示 | P0 | API测试 | 用例映射 |
| MAPPING_API_012 | 验证新建用例映射API-confidence_score边界值0 | 用户已登录 | POST /api/precision-testing/mappings/，body: {function_name:"Test.func",file_path:"test.py",testcase:1,mapping_type:"manual",confidence_score:0} | 返回201，confidence_score为0，页面进度环显示0% | P1 | API测试 | 用例映射 |
| MAPPING_API_013 | 验证新建用例映射API-confidence_score边界值1 | 用户已登录 | POST /api/precision-testing/mappings/，body: {function_name:"Test.func",file_path:"test.py",testcase:1,mapping_type:"manual",confidence_score:1.0} | 返回201，confidence_score为1.0，页面进度环显示100% | P1 | API测试 | 用例映射 |
| MAPPING_API_014 | 验证更新用例映射API | 存在id=1的映射记录 | PATCH /api/precision-testing/mappings/1/，body: {confidence_score:0.85} | 返回200，confidence_score更新为0.85 | P0 | API测试 | 用例映射 |
| MAPPING_API_015 | 验证更新用例映射API-mapping_type切换 | 存在mapping_type=manual的记录 | PATCH /api/precision-testing/mappings/{id}/，body: {mapping_type:"auto"} | 返回200，mapping_type更新为"auto"，页面标签颜色从绿色变为蓝色 | P0 | API测试 | 用例映射 |
| MAPPING_API_016 | 验证删除用例映射API | 存在id可删除的映射记录 | DELETE /api/precision-testing/mappings/{id}/ | 返回204，映射记录已删除，再次访问返回404 | P0 | API测试 | 用例映射 |
| MAPPING_API_017 | 验证自动构建映射API-指定repo_id | 用户已登录，存在id=1的仓库 | POST /api/precision-testing/mappings/auto-build/，body: {repo_id:1} | 返回200（任务已接受），后端开始异步构建任务 | P0 | API测试 | 用例映射 |
| MAPPING_API_018 | 验证自动构建映射API-全量构建 | 用户已登录，无repo_id | POST /api/precision-testing/mappings/auto-build/，body: {} | 返回200，后端开始对所有仓库进行全量构建 | P1 | API测试 | 用例映射 |
| MAPPING_API_019 | 验证用例映射列表API-未授权访问 | 不携带Token | GET /api/precision-testing/mappings/ | 返回401 Unauthorized | P0 | 安全测试 | 权限校验 |
| MAPPING_API_020 | 验证新建映射API-无效testcase_id | 用户已登录，testcase_id不存在 | POST /api/precision-testing/mappings/，body: {function_name:"Test.func",file_path:"test.py",testcase:99999,mapping_type:"manual"} | 返回400，响应体包含testcase字段错误提示（用例不存在） | P1 | API测试 | 用例映射 |

## 二、手动功能验证

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|--------|--------|--------|--------|--------|--------|--------|
| MAPPING_UI_001 | 验证映射列表默认加载 | 用户已登录，进入映射管理页面 | 直接访问/precision-testing/mappings | 表格加载完成，显示映射列表，顶部有筛选选择器和搜索框 | P0 | 手动功能验证 | 用例映射 |
| MAPPING_UI_002 | 验证映射列表loading状态 | 网络较慢时进入页面 | 进入映射管理页面 | 表格区域显示el-loading遮罩，加载完成后消失 | P0 | 手动功能验证 | 用例映射 |
| MAPPING_UI_003 | 验证映射类型筛选-手工标注 | 映射列表已加载，包含多种类型 | 1. 选择映射类型下拉框<br>2. 选择"手工标注" | 列表立即刷新，仅显示mapping_type=manual的记录，标签为绿色 | P0 | 手动功能验证 | 用例映射 |
| MAPPING_UI_004 | 验证映射类型筛选-自动构建 | 映射列表已加载，包含多种类型 | 1. 选择映射类型下拉框<br>2. 选择"自动构建" | 列表刷新，仅显示mapping_type=auto的记录，标签为蓝色 | P0 | 手动功能验证 | 用例映射 |
| MAPPING_UI_005 | 验证映射类型筛选-AI推断 | 映射列表已加载，包含多种类型 | 1. 选择映射类型下拉框<br>2. 选择"AI推断" | 列表刷新，仅显示mapping_type=ai的记录，标签为橙色 | P0 | 手动功能验证 | 用例映射 |
| MAPPING_UI_006 | 验证映射类型筛选-清除筛选 | 筛选条件已应用 | 1. 已选择某个筛选条件<br>2. 点击筛选框的"清除"按钮 | 筛选条件重置，列表恢复显示全量数据 | P1 | 手动功能验证 | 用例映射 |
| MAPPING_UI_007 | 验证搜索功能-防抖400ms | 映射列表已加载 | 1. 在搜索框输入"login"<br>2. 等待400ms以上 | 触发搜索，列表显示function_name或testcase_name包含"login"的记录 | P0 | 手动功能验证 | 用例映射 |
| MAPPING_UI_008 | 验证搜索功能-清空搜索 | 搜索结果已显示 | 1. 输入关键词<br>2. 等待搜索完成<br>3. 点击搜索框清空按钮 | 搜索清除，列表恢复全量数据 | P1 | 手动功能验证 | 用例映射 |
| MAPPING_UI_009 | 验证手工标注弹窗打开 | 映射列表已加载 | 点击"手工标注"按钮 | 弹窗出现，标题为"手工标注映射"，表单包含function_name/file_path/testcase/mapping_type/confidence_score字段 | P0 | 手动功能验证 | 用例映射 |
| MAPPING_UI_010 | 验证编辑映射弹窗打开 | 映射列表存在记录 | 点击某行操作列"编辑"按钮 | 弹窗出现，标题为"编辑映射"，表单字段回填该行数据 | P0 | 手动功能验证 | 用例映射 |
| MAPPING_UI_011 | 验证编辑映射表单数据回填 | 映射记录存在 | 点击该记录的"编辑"按钮 | function_name/file_path/testcase(数字ID)/mapping_type回填正确，confidence_score滑块和输入框值一致 | P0 | 手动功能验证 | 用例映射 |
| MAPPING_UI_012 | 验证手工标注表单必填校验-空白提交 | 弹窗已打开 | 不填写任何字段，直接点击"保存" | 显示3条表单错误提示（function_name/file_path/testcase） | P0 | 手动功能验证 | 用例映射 |
| MAPPING_UI_013 | 验证手工标注表单必填校验-部分填写 | 弹窗已打开 | 仅填写function_name字段，点击"保存" | 显示剩余必填字段错误提示（file_path/testcase） | P1 | 手动功能验证 | 用例映射 |
| MAPPING_UI_014 | 验证手工标注表单成功提交 | 弹窗已打开，表单完整 | 填写所有必填字段，点击"保存" | 弹窗关闭，列表新增该记录，顶部显示"标注成功"消息提示 | P0 | 手动功能验证 | 用例映射 |
| MAPPING_UI_015 | 验证编辑映射保存成功 | 编辑弹窗已打开，数据已修改 | 修改confidence_score，点击"保存" | 弹窗关闭，列表该行confidence_score更新，圆形进度环值更新 | P0 | 手动功能验证 | 用例映射 |
| MAPPING_UI_016 | 验证删除映射确认取消 | 映射列表存在记录 | 1. 点击某行"删除"按钮<br>2. 在确认框点击"取消" | 确认框关闭，记录未被删除 | P0 | 手动功能验证 | 用例映射 |
| MAPPING_UI_017 | 验证删除映射确认删除 | 映射列表存在记录 | 1. 点击某行"删除"按钮<br>2. 在确认框点击"确定" | 确认框关闭，记录从列表移除，顶部显示"已删除" | P0 | 手动功能验证 | 用例映射 |
| MAPPING_UI_018 | 验证置信度圆形进度环显示0% | 某条映射confidence_score=0 | 查看该行置信度列 | 显示圆形进度环，百分比为0 | P1 | 手动功能验证 | 用例映射 |
| MAPPING_UI_019 | 验证置信度圆形进度环显示100% | 某条映射confidence_score=1.0 | 查看该行置信度列 | 显示圆形进度环，百分比为100，进度环为完成状态 | P1 | 手动功能验证 | 用例映射 |
| MAPPING_UI_020 | 验证置信度圆形进度环显示中间值 | 某条映射confidence_score=0.75 | 查看该行置信度列 | 显示圆形进度环，百分比为75 | P1 | 手动功能验证 | 用例映射 |
| MAPPING_UI_021 | 验证置信度为空时显示短横线 | 某条映射confidence_score=null | 查看该行置信度列 | 显示"-"而非进度环 | P1 | 手动功能验证 | 用例映射 |
| MAPPING_UI_022 | 验证映射类型标签manual颜色 | 存在mapping_type=manual的记录 | 查看该行映射类型列 | 显示绿色标签（el-tag type=success） | P1 | 手动功能验证 | 用例映射 |
| MAPPING_UI_023 | 验证映射类型标签auto颜色 | 存在mapping_type=auto的记录 | 查看该行映射类型列 | 显示蓝色标签（el-tag type=primary） | P1 | 手动功能验证 | 用例映射 |
| MAPPING_UI_024 | 验证映射类型标签ai颜色 | 存在mapping_type=ai的记录 | 查看该行映射类型列 | 显示橙色标签（el-tag type=warning） | P1 | 手动功能验证 | 用例映射 |
| MAPPING_UI_025 | 验证自动构建弹窗-idle状态 | 列表已加载 | 点击"自动构建"按钮 | 弹窗出现，显示"仓库ID"输入框（选填），"开始构建"和"关闭"按钮 | P0 | 手动功能验证 | 用例映射 |
| MAPPING_UI_026 | 验证自动构建-开始构建 | 自动构建弹窗已打开 | 1. 可选填写repo_id<br>2. 点击"开始构建" | 状态变为running，进度条出现，显示"正在自动构建映射关系..." | P0 | 手动功能验证 | 用例映射 |
| MAPPING_UI_027 | 验证自动构建-running状态动画 | 构建进行中 | 查看自动构建弹窗 | 进度条有striped动画，图标为Loading旋转动画 | P0 | 手动功能验证 | 用例映射 |
| MAPPING_UI_028 | 验证自动构建-完成状态 | 构建成功完成 | 等待构建完成 | 状态变为done，图标变为绿色勾选，进度条100%，消息为"自动构建完成！" | P0 | 手动功能验证 | 用例映射 |
| MAPPING_UI_029 | 验证自动构建-失败状态 | 构建执行失败 | 后端返回构建错误 | 状态变为error，图标变为红色叉号，消息为错误详情 | P0 | 手动功能验证 | 用例映射 |
| MAPPING_UI_030 | 验证自动构建-running时关闭按钮禁用 | 构建进行中 | 查看自动构建弹窗底部按钮 | "关闭"按钮处于disabled状态，不可点击 | P1 | 手动功能验证 | 用例映射 |
| MAPPING_UI_031 | 验证自动构建完成后自动刷新列表 | 构建进行中 | 等待构建完成 | 构建完成后，映射列表自动刷新，新构建的映射出现在列表中 | P0 | 手动功能验证 | 用例映射 |
| MAPPING_UI_032 | 验证自动构建-运行中不可重复点击 | 构建进行中 | 快速多次点击"开始构建" | 按钮已显示loading，防止重复提交，接口只被调用1次 | P0 | 手动功能验证 | 用例映射 |
| MAPPING_UI_033 | 验证映射列表分页 | 映射总数超过20条 | 切换到第2页 | 列表更新为第2页数据，分页器当前页为2 | P1 | 手动功能验证 | 用例映射 |
| MAPPING_UI_034 | 验证映射列表分页-切换每页条数 | 在第1页 | 将每页条数从20切换为50 | 列表刷新，显示前50条记录 | P1 | 手动功能验证 | 用例映射 |
| MAPPING_UI_035 | 验证映射列表空状态 | 无任何映射记录 | 进入映射管理页面（确认无数据） | 表格显示空状态"暂无数据" | P1 | 手动功能验证 | 用例映射 |
| MAPPING_UI_036 | 验证时间格式化显示 | 映射列表有数据 | 查看"创建时间"列 | 显示格式"YYYY-MM-DD HH:mm"，非空时间正确格式化 | P1 | 手动功能验证 | 用例映射 |

## 三、E2E测试

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|--------|--------|--------|--------|--------|--------|--------|
| MAPPING_E2E_001 | 端到端新建手工标注流程 | 用户已登录，映射管理页面 | 1. 点击"手工标注"<br>2. 填写函数名"new_test_func"<br>3. 填写文件路径"new_test.py"<br>4. 填写用例ID 100<br>5. 选择类型"手工标注"<br>6. 设置置信度0.95<br>7. 点击保存 | 弹窗关闭，列表新增一条function_name="new_test_func"的记录 | P0 | E2E测试 | 用例映射 |
| MAPPING_E2E_002 | 端到端编辑映射流程 | 存在可编辑的映射记录 | 1. 点击某行"编辑"<br>2. 修改置信度到0.5<br>3. 保存 | 弹窗关闭，该行置信度进度环更新为50% | P0 | E2E测试 | 用例映射 |
| MAPPING_E2E_003 | 端到端删除映射流程 | 存在可删除的映射记录 | 1. 点击某行"删除"<br>2. 确认删除 | 记录从列表消失 | P0 | E2E测试 | 用例映射 |
| MAPPING_E2E_004 | 端到端自动构建流程 | 用户已登录，存在仓库 | 1. 点击"自动构建"<br>2. 不填repo_id（全量）<br>3. 点击"开始构建"<br>4. 等待完成（最多60s） | 进度完成，列表自动刷新显示新增的auto类型映射 | P0 | E2E测试 | 用例映射 |

## 四、异常场景测试

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|--------|--------|--------|--------|--------|--------|--------|
| MAPPING_ERR_001 | 验证映射列表加载网络失败 | 已进入映射管理页面 | 1. 切换到Offline模式<br>2. 刷新页面 | 显示错误提示"加载映射列表失败"，表格区域显示空状态 | P0 | 容错测试 | 用例映射 |
| MAPPING_ERR_002 | 验证新建映射时后端返回500 | 后端模拟错误 | 1. 填写表单<br>2. 点击保存，后端返回500 | 显示"操作失败"错误提示，弹窗保持打开，数据保留 | P0 | 容错测试 | 用例映射 |
| MAPPING_ERR_003 | 验证自动构建失败错误显示 | 后端构建任务失败 | 1. 点击"自动构建"<br>2. 点击"开始构建"<br>3. 后端返回错误 | 弹窗状态变为error，显示错误消息内容 | P0 | 容错测试 | 用例映射 |
| MAPPING_ERR_004 | 验证保存时重复提交防护 | 网络较慢 | 1. 填写表单<br>2. 快速点击"保存"按钮2次 | 保存按钮显示loading，只发出1次请求，防止重复创建 | P0 | 容错测试 | 用例映射 |
| MAPPING_ERR_005 | 验证分页加载网络失败 | 在第2页时网络断开 | 1. 进入第2页<br>2. 切换到Offline模式<br>3. 切换每页条数触发reload | 显示"加载映射列表失败"，列表清空或保持上一页数据 | P1 | 容错测试 | 用例映射 |