# Week 5 精准测试前端 — RepoBindings.vue 测试用例

## 一、API 测试

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|--------|--------|--------|--------|--------|--------|--------|
| REPOBIND_API_001 | 验证获取仓库绑定列表API | Django服务运行，已存在至少1条绑定记录 | GET /api/precision-testing/repos/?page=1&page_size=20 | 返回200，响应体包含results数组和count字段，列表数据完整 | P0 | API测试 | 仓库绑定 |
| REPOBIND_API_002 | 验证仓库绑定列表分页功能 | 绑定了超过20条仓库记录 | GET /api/precision-testing/repos/?page=2&page_size=10 | 返回200，results长度为10，count为总记录数 | P1 | API测试 | 仓库绑定 |
| REPOBIND_API_003 | 验证仓库绑定列表搜索功能 | 存在名称包含"backend"的仓库 | GET /api/precision-testing/repos/?search=backend | 返回200，results中所有仓库名称均包含"backend" | P1 | API测试 | 仓库绑定 |
| REPOBIND_API_004 | 验证新建仓库绑定API | 用户已登录，Django服务运行 | POST /api/precision-testing/repos/，body: {name:"test-repo",repo_url:"https://github.com/test/repo.git",branch:"main",local_path:"/tmp/repo",project:1,is_active:true} | 返回201，响应体包含新建的仓库绑定记录，id字段有值 | P0 | API测试 | 仓库绑定 |
| REPOBIND_API_005 | 验证新建仓库绑定必填字段校验-name为空 | 用户已登录 | POST /api/precision-testing/repos/，body: {repo_url:"https://github.com/test/repo.git",branch:"main",local_path:"/tmp/repo",project:1} | 返回400，响应体包含name字段错误提示 | P0 | API测试 | 仓库绑定 |
| REPOBIND_API_006 | 验证新建仓库绑定必填字段校验-repo_url为空 | 用户已登录 | POST /api/precision-testing/repos/，body: {name:"test-repo",branch:"main",local_path:"/tmp/repo",project:1} | 返回400，响应体包含repo_url字段错误提示 | P0 | API测试 | 仓库绑定 |
| REPOBIND_API_007 | 验证新建仓库绑定必填字段校验-branch为空 | 用户已登录 | POST /api/precision-testing/repos/，body: {name:"test-repo",repo_url:"https://github.com/test/repo.git",local_path:"/tmp/repo",project:1} | 返回400，响应体包含branch字段错误提示 | P0 | API测试 | 仓库绑定 |
| REPOBIND_API_008 | 验证新建仓库绑定必填字段校验-local_path为空 | 用户已登录 | POST /api/precision-testing/repos/，body: {name:"test-repo",repo_url:"https://github.com/test/repo.git",branch:"main",project:1} | 返回400，响应体包含local_path字段错误提示 | P0 | API测试 | 仓库绑定 |
| REPOBIND_API_009 | 验证获取单条仓库绑定详情API | 存在id=1的仓库绑定记录 | GET /api/precision-testing/repos/1/ | 返回200，响应体包含该仓库的全部字段（name,repo_url,branch,local_path,project,is_active,last_analyzed_at） | P1 | API测试 | 仓库绑定 |
| REPOBIND_API_010 | 验证获取不存在的仓库绑定详情 | 不存在id=99999的仓库绑定 | GET /api/precision-testing/repos/99999/ | 返回404，响应体包含NotFound错误 | P1 | API测试 | 仓库绑定 |
| REPOBIND_API_011 | 验证更新仓库绑定API | 存在id=1的仓库绑定记录 | PATCH /api/precision-testing/repos/1/，body: {name:"updated-repo-name"} | 返回200，响应体name字段已更新为"updated-repo-name" | P0 | API测试 | 仓库绑定 |
| REPOBIND_API_012 | 验证更新仓库绑定is_active字段 | 存在id=1的仓库绑定记录，is_active=true | PATCH /api/precision-testing/repos/1/，body: {is_active:false} | 返回200，is_active更新为false，页面状态标签变为"停用" | P0 | API测试 | 仓库绑定 |
| REPOBIND_API_013 | 验证删除仓库绑定API | 存在id可删除的仓库绑定记录 | DELETE /api/precision-testing/repos/{id}/ | 返回204，响应体为空，再次访问该id返回404 | P0 | API测试 | 仓库绑定 |
| REPOBIND_API_014 | 验证触发分析API-正常触发 | 存在id=1的仓库绑定记录，对应仓库有代码变更 | POST /api/precision-testing/repos/1/analyze/ | 返回200，响应体包含analysis_id字段，任务已创建 | P0 | API测试 | 仓库绑定 |
| REPOBIND_API_015 | 验证触发分析API-重复触发 | 仓库正在分析中（已有running状态的analysis） | POST /api/precision-testing/repos/1/analyze/ | 返回200（允许重复触发），新的analysis_id与正在运行的analysis_id不同 | P1 | API测试 | 仓库绑定 |
| REPOBIND_API_016 | 验证触发分析API-仓库不存在 | 不存在id=99999的仓库 | POST /api/precision-testing/repos/99999/analyze/ | 返回404，错误信息包含仓库不存在 | P1 | API测试 | 仓库绑定 |
| REPOBIND_API_017 | 验证触发分析API-未授权访问 | 用户未携带有效Token | POST /api/precision-testing/repos/1/analyze/（无Authorization头） | 返回401 Unauthorized | P0 | 安全测试 | 权限校验 |
| REPOBIND_API_018 | 验证仓库绑定列表API-未授权访问 | 用户未携带有效Token | GET /api/precision-testing/repos/（无Token） | 返回401 Unauthorized | P0 | 安全测试 | 权限校验 |
| REPOBIND_API_019 | 验证分析进度查询API-running状态 | 存在id=1的分析记录，状态为running | GET /api/precision-testing/analyses/1/progress/ | 返回200，status为"running"或"pending"，包含progress字段 | P1 | API测试 | 仓库绑定 |
| REPOBIND_API_020 | 验证分析进度查询API-completed状态 | 存在id=1的分析记录，状态为completed | GET /api/precision-testing/analyses/1/progress/ | 返回200，status为"completed"，progress为100 | P1 | API测试 | 仓库绑定 |
| REPOBIND_API_021 | 验证分析进度查询API-failed状态 | 存在id=1的分析记录，状态为failed | GET /api/precision-testing/analyses/1/progress/ | 返回200，status为"failed"，包含error_message字段 | P1 | API测试 | 仓库绑定 |

## 二、手动功能验证

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|--------|--------|--------|--------|--------|--------|--------|
| REPOBIND_UI_001 | 验证仓库绑定页面默认加载列表 | 用户已登录，进入仓库绑定页面 | 直接访问/precision-testing/repos | 表格加载完成，显示仓库列表（最多20条），底部有分页控件 | P0 | 手动功能验证 | 仓库绑定 |
| REPOBIND_UI_002 | 验证仓库绑定列表loading状态 | 网络较慢时进入页面 | 访问/precision-testing/repos | 表格区域显示loading动画（el-loading），数据加载完成后动画消失 | P0 | 手动功能验证 | 仓库绑定 |
| REPOBIND_UI_003 | 验证仓库绑定搜索-防抖400ms | 在搜索框输入关键词 | 1. 清空搜索框<br>2. 输入"backend"<br>3. 等待400ms以上 | 接口被触发，列表数据更新为包含"backend"的结果 | P0 | 手动功能验证 | 仓库绑定 |
| REPOBIND_UI_004 | 验证仓库绑定搜索-即时清空 | 搜索结果存在时清空搜索框 | 1. 搜索"abc"得到结果<br>2. 点击搜索框清空按钮 | 列表数据恢复为全量数据，不再包含过滤条件 | P1 | 手动功能验证 | 仓库绑定 |
| REPOBIND_UI_005 | 验证新建仓库绑定弹窗打开 | 用户已登录，在仓库绑定页面 | 点击"绑定仓库"按钮 | 弹窗出现，标题为"绑定新仓库"，表单包含name/repo_url/branch/local_path/project/is_active字段 | P0 | 手动功能验证 | 仓库绑定 |
| REPOBIND_UI_006 | 验证新建仓库绑定表单必填校验-空白提交 | 弹窗已打开 | 1. 不填写任何字段<br>2. 直接点击"保存"按钮 | 页面显示4条表单错误提示，分别对应name/repo_url/branch/local_path字段 | P0 | 手动功能验证 | 仓库绑定 |
| REPOBIND_UI_007 | 验证新建仓库绑定表单必填校验-部分填写 | 弹窗已打开 | 1. 仅填写name字段<br>2. 点击"保存" | 显示剩余必填字段错误提示，name字段不报错 | P1 | 手动功能验证 | 仓库绑定 |
| REPOBIND_UI_008 | 验证新建仓库绑定表单成功提交 | 弹窗已打开，表单信息完整合法 | 1. 填写所有必填字段<br>2. 点击"保存"按钮 | 弹窗关闭，列表新增一条记录，顶部出现"绑定成功"消息提示 | P0 | 手动功能验证 | 仓库绑定 |
| REPOBIND_UI_009 | 验证新建仓库绑定表单取消操作 | 弹窗已打开 | 点击"取消"按钮 | 弹窗关闭，表单重置，列表数据不变 | P1 | 手动功能验证 | 仓库绑定 |
| REPOBIND_UI_010 | 验证新建仓库绑定表单提交失败错误提示 | 弹窗已打开，后端API返回错误 | 1. 填写表单<br>2. 点击"保存"<br>3. 模拟网络错误或后端异常 | 页面顶部出现"操作失败"错误提示（ElMessage.error），弹窗保持打开，表单数据保留 | P0 | 手动功能验证 | 仓库绑定 |
| REPOBIND_UI_011 | 验证编辑仓库绑定弹窗打开 | 仓库绑定列表存在数据 | 点击某行操作列的"编辑"按钮 | 弹窗出现，标题为"编辑仓库绑定"，表单字段回填该行数据 | P0 | 手动功能验证 | 仓库绑定 |
| REPOBIND_UI_012 | 验证编辑仓库绑定表单数据回填 | 某条仓库绑定记录存在 | 点击该记录的"编辑"按钮 | name/repo_url/branch/local_path/project字段值与该记录一致，is_active开关状态正确 | P0 | 手动功能验证 | 仓库绑定 |
| REPOBIND_UI_013 | 验证编辑仓库绑定保存成功 | 编辑弹窗已打开，数据已修改 | 修改name字段，点击"保存" | 弹窗关闭，列表中该行name已更新，顶部出现"更新成功"消息提示 | P0 | 手动功能验证 | 仓库绑定 |
| REPOBIND_UI_014 | 验证删除仓库绑定-确认取消 | 仓库绑定列表存在数据 | 1. 点击某行"删除"按钮<br>2. 在确认框中点击"取消" | 确认框关闭，列表数据不变，记录未被删除 | P0 | 手动功能验证 | 仓库绑定 |
| REPOBIND_UI_015 | 验证删除仓库绑定-确认删除 | 仓库绑定列表存在数据 | 1. 点击某行"删除"按钮<br>2. 在确认框中点击"确定" | 确认框关闭，记录从列表中移除，顶部出现"已删除"消息提示 | P0 | 手动功能验证 | 仓库绑定 |
| REPOBIND_UI_016 | 验证删除仓库绑定-删除失败提示 | 仓库绑定列表存在数据，但删除API返回错误 | 1. 点击某行"删除"按钮<br>2. 确认删除<br>3. 后端返回500错误 | 顶部出现"删除失败"错误提示，记录仍在列表中 | P1 | 手动功能验证 | 仓库绑定 |
| REPOBIND_UI_017 | 验证触发分析功能-进度弹窗出现 | 仓库绑定列表存在数据 | 点击某行的"触发分析"按钮 | 分析进度弹窗出现，显示"正在触发分析任务..."和进度条 | P0 | 手动功能验证 | 仓库绑定 |
| REPOBIND_UI_018 | 验证触发分析功能-进度轮询更新 | 分析任务已开始 | 在进度弹窗中等待2秒 | 进度百分比从10%变化到更高，状态文字从"正在触发..."变为"分析中（xxx）..." | P0 | 手动功能验证 | 仓库绑定 |
| REPOBIND_UI_019 | 验证触发分析功能-分析完成状态 | 分析任务已完成 | 进度弹窗中分析完成 | 进度条到达100%，图标变为绿色勾选，状态文字为"分析完成！"，点击"关闭"弹窗关闭 | P0 | 手动功能验证 | 仓库绑定 |
| REPOBIND_UI_020 | 验证触发分析功能-分析失败状态 | 分析任务已失败 | 进度弹窗中分析失败 | 图标变为红色叉号，状态文字包含"分析失败"及错误原因 | P0 | 手动功能验证 | 仓库绑定 |
| REPOBIND_UI_021 | 验证触发分析功能-轮询取消令牌 | 已打开进度弹窗，分析进行中 | 1. 等待进度轮询进行中<br>2. 点击"取消"按钮 | 弹窗关闭，进度轮询立即停止，不再发送progress请求 | P0 | 手动功能验证 | 仓库绑定 |
| REPOBIND_UI_022 | 验证触发分析功能-关闭弹窗重置令牌 | 已打开进度弹窗，分析进行中 | 点击弹窗的X关闭按钮或点击遮罩 | 弹窗关闭，进度轮询停止，pollingToken已更新，关闭后再次打开新弹窗正常 | P1 | 手动功能验证 | 仓库绑定 |
| REPOBIND_UI_023 | 验证仓库绑定列表分页-翻页 | 仓库绑定总数超过20条 | 点击分页控件的"下一页"按钮 | 列表切换到第2页数据，分页器当前页变为2 | P1 | 手动功能验证 | 仓库绑定 |
| REPOBIND_UI_024 | 验证仓库绑定列表分页-切换每页条数 | 在第1页 | 将每页条数从20切换为50 | 列表刷新，显示该仓库的前50条记录，分页器显示正确的total | P1 | 手动功能验证 | 仓库绑定 |
| REPOBIND_UI_025 | 验证仓库绑定列表空状态-无数据 | 仓库绑定表为空 | 访问/precision-testing/repos（确认无数据） | 表格显示空状态文案"暂无数据"或el-table__empty-text | P1 | 手动功能验证 | 仓库绑定 |
| REPOBIND_UI_026 | 验证仓库绑定列表状态标签-启用 | 存在is_active=true的仓库绑定 | 查看仓库绑定列表的状态列 | 显示绿色"启用"标签（el-tag type=success） | P1 | 手动功能验证 | 仓库绑定 |
| REPOBIND_UI_027 | 验证仓库绑定列表状态标签-停用 | 存在is_active=false的仓库绑定 | 查看仓库绑定列表的状态列 | 显示灰色"停用"标签（el-tag type=info） | P1 | 手动功能验证 | 仓库绑定 |
| REPOBIND_UI_028 | 验证仓库绑定列表最后分析时间-从未 | 存在从未分析的仓库绑定 | 查看某行"最近分析"列 | 显示"从未"文字 | P1 | 手动功能验证 | 仓库绑定 |
| REPOBIND_UI_029 | 验证仓库绑定列表最后分析时间-有记录 | 存在已分析过的仓库绑定 | 查看某行"最近分析"列 | 显示格式化时间，格式为"YYYY-MM-DD HH:mm" | P1 | 手动功能验证 | 仓库绑定 |
| REPOBIND_UI_030 | 验证仓库绑定列表超长文本截断 | 仓库名称超过15个字符 | 查看列表中长名称的仓库 | 名称显示被截断，鼠标悬停显示完整名称（show-overflow-tooltip） | P2 | 手动功能验证 | 仓库绑定 |

## 三、E2E测试

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|--------|--------|--------|--------|--------|--------|--------|
| REPOBIND_E2E_001 | 端到端新建仓库绑定流程 | 用户已登录，后端API正常，仓库绑定列表页 | 1. 点击"绑定仓库"<br>2. 填写名称"e2e-test-repo"<br>3. 填写URL "https://github.com/e2e/test.git"<br>4. 填写分支"main"<br>5. 填写本地路径"/tmp/e2e-test"<br>6. 填写项目ID 1<br>7. 点击"保存" | 弹窗关闭，列表出现名称为"e2e-test-repo"的新记录 | P0 | E2E测试 | 仓库绑定 |
| REPOBIND_E2E_002 | 端到端编辑仓库绑定流程 | 存在可编辑的仓库绑定记录 | 1. 点击某行"编辑"<br>2. 修改名称<br>3. 点击"保存" | 弹窗关闭，列表该行名称已更新为新值 | P0 | E2E测试 | 仓库绑定 |
| REPOBIND_E2E_003 | 端到端删除仓库绑定流程 | 存在可删除的仓库绑定记录 | 1. 点击某行"删除"<br>2. 在确认框中点击"确定" | 记录从列表中消失，列表总条数减1 | P0 | E2E测试 | 仓库绑定 |
| REPOBIND_E2E_004 | 端到端触发分析并等待完成 | 存在可分析的仓库绑定，仓库有变更代码 | 1. 点击"触发分析"<br>2. 等待分析完成（进度到100%）<br>3. 关闭弹窗<br>4. 查看该行"最近分析"列 | 时间已更新为当前时间，不再显示"从未" | P0 | E2E测试 | 仓库绑定 |

## 四、异常场景测试

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|--------|--------|--------|--------|--------|--------|--------|
| REPOBIND_ERR_001 | 验证仓库绑定列表加载网络失败 | 已进入仓库绑定列表页 | 1. 浏览器开发者工具切换到Offline模式<br>2. 刷新页面 | 显示错误消息提示"加载仓库列表失败"，表格区域显示空状态 | P0 | 容错测试 | 仓库绑定 |
| REPOBIND_ERR_002 | 验证仓库绑定列表加载超时 | 后端API响应超过30s | 1. 通过代理延迟API响应至35秒<br>2. 刷新页面 | 显示错误消息提示"加载仓库列表失败"或请求超时 | P1 | 容错测试 | 仓库绑定 |
| REPOBIND_ERR_003 | 验证新建仓库绑定时后端返回500 | 后端模拟500错误 | 1. 填写表单<br>2. 点击保存，后端返回500 | 页面显示"操作失败"错误提示，弹窗保持打开，用户可修改重试 | P0 | 容错测试 | 仓库绑定 |
| REPOBIND_ERR_004 | 验证触发分析时后端返回500 | 后端分析任务异常 | 1. 点击"触发分析"<br>2. 等待错误返回 | 进度弹窗显示error状态，图标变红，消息为后端返回的detail错误信息 | P0 | 容错测试 | 仓库绑定 |
| REPOBIND_ERR_005 | 验证触发分析时网络中断 | 进度弹窗已打开 | 1. 将浏览器设为Offline模式<br>2. 等待轮询请求发出 | 进度弹窗显示error状态，消息为"进度查询失败"，轮询停止 | P1 | 容错测试 | 仓库绑定 |
| REPOBIND_ERR_006 | 验证新建仓库绑定表单重复提交 | 网络较慢，用户双击保存 | 1. 填写表单<br>2. 快速连续点击"保存"按钮2次 | 防止重复提交，接口只被调用1次，保存按钮显示loading状态 | P0 | 容错测试 | 仓库绑定 |