# Week 5 精准测试前端 — 跨页面与共享测试用例

## 一、导航与路由测试

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|--------|--------|--------|--------|--------|--------|--------|
| NAV_001 | 验证精准测试侧边栏菜单入口显示 | 用户已登录，侧边栏正常渲染 | 进入任意页面，查看侧边栏 | 侧边栏显示6个精准测试菜单入口：风险仪表盘/仓库绑定/变更分析/用例映射/影响图谱/执行记录 | P0 | 手动功能验证 | 路由导航 |
| NAV_002 | 验证精准测试侧边栏菜单-菜单项图标 | 侧边栏有精准测试菜单 | 查看精准测试菜单区域 | 每个菜单项左侧有对应图标：风险仪表盘=Odometer/仓库绑定=Connection/变更分析=DataAnalysis/用例映射=Link/影响图谱=Share/执行记录=Timer | P1 | 手动功能验证 | 路由导航 |
| NAV_003 | 验证精准测试侧边栏菜单-当前激活高亮 | 用户在仓库绑定页面 | 直接访问/precision-testing/repos | 左侧仓库绑定菜单项高亮（is-active），背景色为active状态色 | P0 | 手动功能验证 | 路由导航 |
| NAV_004 | 验证精准测试侧边栏菜单-切换高亮 | 用户在仓库绑定页面 | 1. 点击侧边栏"变更分析"菜单 | 页面切换到变更分析，对应菜单项高亮，原仓库绑定高亮取消 | P0 | 手动功能验证 | 路由导航 |
| NAV_005 | 验证精准测试面包屑-模块名显示 | 用户进入精准测试任意页面 | 查看顶部面包屑 | 面包屑显示"首页 > 精准测试"，其中"精准测试"为当前模块名 | P0 | 手动功能验证 | 路由导航 |
| NAV_006 | 验证精准测试面包屑-页面标题显示 | 用户进入仓库绑定页面 | 查看面包屑右侧或页面标题 | 显示"仓库绑定"作为当前页面标题 | P0 | 手动功能验证 | 路由导航 |
| NAV_007 | 验证精准测试面包屑-所有页面标题映射 | 依次访问6个页面 | 进入每个页面，查看面包屑或标题 | dashboard→风险仪表盘/repos→仓库绑定/analyses→变更分析/mappings→用例映射/graph→影响图谱/runs→执行记录 | P0 | 手动功能验证 | 路由导航 |
| NAV_008 | 验证6个页面均可通过URL直接访问 | 用户已登录 | 依次直接访问6个页面的URL | 每个页面正常加载，无404，无崩溃，菜单对应高亮 | P0 | 手动功能验证 | 路由导航 |
| NAV_009 | 验证从首页可导航到精准测试任意页面 | 用户在首页 | 1. 在首页侧边栏找到精准测试入口<br>2. 点击"仓库绑定" | 正确导航到/precision-testing/repos，页面完整加载 | P0 | 手动功能验证 | 路由导航 |
| NAV_010 | 验证侧边栏精准测试菜单切换不过页 | 连续快速切换不同菜单 | 1. 依次点击仓库绑定→变更分析→用例映射→影响图谱 | 页面正确切换，无路由混乱，无页面空白 | P1 | 手动功能验证 | 路由导航 |

## 二、认证与会话测试

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|--------|--------|--------|--------|--------|--------|--------|
| AUTH_001 | 验证未登录直接访问精准测试页面 | 用户未登录，Cookie无Token | 直接访问/precision-testing/dashboard | 自动跳转到/login页面，显示登录表单 | P0 | 安全测试 | 权限校验 |
| AUTH_002 | 验证已登录可正常访问精准测试页面 | 用户已登录（Token有效） | 直接访问/precision-testing/repos | 页面正常加载，显示完整内容，无401/403 | P0 | 安全测试 | 权限校验 |
| AUTH_003 | 验证Token过期后访问精准测试页面 | 用户已登录，Token已过期 | 1. 持有过期Token<br>2. 访问/precision-testing/dashboard | Token过期拦截，跳转回/login，页面不显示内容 | P0 | 安全测试 | 权限校验 |
| AUTH_004 | 验证精准测试API统一鉴权-RepoBindings | 已登录用户带Token | 访问/precision-testing/repos，查看Network中API请求 | 所有/api/precision-testing/*请求均携带Authorization:Bearer {token}头 | P0 | 安全测试 | 权限校验 |
| AUTH_005 | 验证精准测试API统一鉴权-ChangeAnalyses | 已登录用户带Token | 访问/precision-testing/analyses，查看Network中API请求 | 所有API请求均携带Authorization头 | P0 | 安全测试 | 权限校验 |

## 三、API Shared Layer测试

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|--------|--------|--------|--------|--------|--------|--------|
| API_SHARE_001 | 验证Axios请求统一baseURL配置 | 精准测试API封装调用 | 访问/precision-testing/repos，查看Network | 所有请求baseURL为/api（代理到后端8000） | P0 | API测试 | API分层 |
| API_SHARE_002 | 验证Axios请求统一timeout=30s | 精准测试API封装调用 | 任意API请求发出 | 请求超时时间设置为30000ms | P1 | API测试 | API分层 |
| API_SHARE_003 | 验证所有精准测试API函数存在 | frontend/src/api/precision-testing.js已存在 | 导入并验证所有函数 | getRepoBindings/createRepoBinding/updateRepoBinding/deleteRepoBinding/triggerAnalysis/getChangeAnalyses/getChangeAnalysisDetail/getAnalysisProgress/getMappings/createMapping/updateMapping/deleteMapping/autoBuildMappings/getImpactAnalyses/queryImpact/getGraphData/getRiskPredictions/getRunRecords/getRunRecordDetail/getDashboard均已导出 | P0 | API测试 | API分层 |
| API_SHARE_004 | 验证列表API统一分页参数格式 | 调用任意列表API | 调用getRepoBindings，查看发出的请求URL | URL包含?page=1&page_size=20格式参数 | P1 | API测试 | API分层 |
| API_SHARE_005 | 验证任务型API返回格式统一 | 调用triggerAnalysis或autoBuildMappings | 查看响应体结构 | 返回体包含analysis_id或task_id，前端可轮询 | P0 | API测试 | API分层 |
| API_SHARE_006 | 验证请求拦截器自动注入Token | 用户已登录 | 进入任意精准测试页面，观察请求 | 所有请求自动在header中注入Authorization:Bearer {accessToken} | P0 | API测试 | API分层 |
| API_SHARE_007 | 验证401响应自动logout跳转 | API返回401 Unauthorized | 1. 已登录访问页面<br>2. 服务端使Token失效<br>3. 触发新API请求 | 当前页面跳转回/login，localStorage清理 | P0 | 安全测试 | 权限校验 |
| API_SHARE_008 | 验证错误消息统一使用ElMessage | API调用失败 | 1. 访问/precision-testing/repos<br>2. 切换Offline模式<br>3. 触发reload | 错误提示使用ElMessage.error()，显示中文用户友好消息 | P1 | 手动功能验证 | API分层 |

## 四、布局与响应式测试

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|--------|--------|--------|--------|--------|--------|--------|
| LAYOUT_001 | 验证精准测试模块使用Layout布局 | 用户进入精准测试页面 | 查看页面整体结构 | 包含侧边栏（el-aside）+主体内容（el-main）+顶部header，与其他模块一致 | P0 | 手动功能验证 | 布局结构 |
| LAYOUT_002 | 验证精准测试页面内容区域padding | 进入仓库绑定页面 | 查看主体内容区域样式 | 内容区有20px padding，页面不贴边 | P1 | 手动功能验证 | 布局结构 |
| LAYOUT_003 | 验证精准测试页面全宽布局 | 仓库绑定页面已加载 | 窗口宽度为1920px | 表格/工具栏占满内容区宽度，无溢出 | P1 | 手动功能验证 | 布局结构 |
| LAYOUT_004 | 验证精准测试页面1024px宽度响应式 | 调整窗口宽度至1024px | 进入仓库绑定页面 | 侧边栏收缩到160px，表格列宽自动调整，表格无溢出 | P1 | 手动功能验证 | 布局结构 |
| LAYOUT_005 | 验证精准测试页面1366px宽度正常 | 调整窗口宽度至1366px | 进入变更分析页面 | 左右分栏布局正常，左侧面板宽度固定，右侧详情区弹性填充 | P1 | 手动功能验证 | 布局结构 |

## 五、页面间跳转与数据一致性测试

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|--------|--------|--------|--------|--------|--------|--------|
| PAGE_001 | 端到端仓库绑定→变更分析数据关联 | 存在已分析的仓库绑定 | 1. 在仓库绑定页面触发分析<br>2. 等待分析完成<br>3. 进入变更分析页面<br>4. 查找对应分析记录 | 变更分析列表中应包含刚才触发的分析记录，commit_hash和分支一致 | P0 | E2E测试 | 跨页面数据流 |
| PAGE_002 | 端到端仓库绑定→触发分析→查看详情 | 存在可分析的仓库绑定 | 1. 点击"触发分析"<br>2. 等待完成<br>3. 点击该行查看"最近分析"时间 | 时间已更新为当前时间附近，证明分析记录已产生 | P0 | E2E测试 | 跨页面数据流 |
| PAGE_003 | 验证6个页面刷新后状态保持 | 在任意精准测试页面 | 1. 在页面上进行操作（如切换筛选条件）<br>2. 刷新浏览器 | 页面恢复到默认初始状态（非keep-alive），不保留筛选状态 | P1 | 手动功能验证 | 页面状态 |

## 六、安全测试

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|--------|--------|--------|--------|--------|--------|--------|
| SEC_001 | 验证RepoBindings列表API身份校验-无Token | 用户未登录 | GET /api/precision-testing/repos/（无Token） | 返回401 Unauthorized | P0 | 安全测试 | 权限校验 |
| SEC_002 | 验证ChangeAnalyses列表API身份校验-无Token | 用户未登录 | GET /api/precision-testing/analyses/（无Token） | 返回401 Unauthorized | P0 | 安全测试 | 权限校验 |
| SEC_003 | 验证Mappings列表API身份校验-无Token | 用户未登录 | GET /api/precision-testing/mappings/（无Token） | 返回401 Unauthorized | P0 | 安全测试 | 权限校验 |
| SEC_004 | 验证Graph图谱API身份校验-无Token | 用户未登录 | GET /api/precision-testing/graph/（无Token） | 返回401 Unauthorized | P0 | 安全测试 | 权限校验 |
| SEC_005 | 验证Dashboard API身份校验-无Token | 用户未登录 | GET /api/precision-testing/dashboard/（无Token） | 返回401 Unauthorized | P0 | 安全测试 | 权限校验 |
| SEC_006 | 验证RunHistory列表API身份校验-无Token | 用户未登录 | GET /api/precision-testing/runs/（无Token） | 返回401 Unauthorized | P0 | 安全测试 | 权限校验 |
| SEC_007 | 验证新建RepoBinding API身份校验-无Token | 用户未登录 | POST /api/precision-testing/repos/（无Token） | 返回401 Unauthorized，无数据被创建 | P0 | 安全测试 | 权限校验 |
| SEC_008 | 验证删除Mapping API身份校验-无Token | 用户未登录 | DELETE /api/precision-testing/mappings/1/（无Token） | 返回401 Unauthorized，映射记录未被删除 | P0 | 安全测试 | 权限校验 |
| SEC_009 | 验证POST impact/query API身份校验-无Token | 用户未登录 | POST /api/precision-testing/impact/query/（无Token） | 返回401 Unauthorized | P0 | 安全测试 | 权限校验 |
| SEC_010 | 验证TriggerAnalysis API身份校验-无Token | 用户未登录 | POST /api/precision-testing/repos/1/analyze/（无Token） | 返回401 Unauthorized，未触发分析 | P0 | 安全测试 | 权限校验 |

## 七、Week 5 完成标准验收测试

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|--------|--------|--------|--------|--------|--------|--------|
| ACC_001 | 验收标准1:6个页面均可从菜单访问 | 用户已登录 | 依次点击侧边栏6个精准测试菜单项 | 每个页面均可正常加载，无404，无崩溃，菜单高亮正确 | P0 | E2E测试 | Week5完成标准 |
| ACC_002 | 验收标准2:所有页面与后端API对接完成 | 后端API运行正常 | 在每个页面上触发至少一个数据加载操作（如列表加载/搜索/筛选） | 每个页面API请求成功，数据正确渲染，无API 500错误 | P0 | E2E测试 | Week5完成标准 |
| ACC_003 | 验收标准3:风险仪表盘与影响图谱可展示数据 | 后端有完整数据（仓库/分析/映射/图谱数据） | 1. 进入风险仪表盘<br>2. 进入影响图谱 | 仪表盘4个KPI卡片有数值，4个图表渲染；影响图谱显示全量图谱或可查询 | P0 | E2E测试 | Week5完成标准 |
| ACC_004 | 验收标准4:异步任务具备过程反馈-触发分析 | 仓库绑定页面 | 1. 点击"触发分析"<br>2. 观察进度弹窗 | 弹窗显示进度条，百分比递增，状态文字更新（running→completed） | P0 | E2E测试 | Week5完成标准 |
| ACC_005 | 验收标准4:异步任务具备过程反馈-自动构建映射 | 映射管理页面 | 1. 点击"自动构建"<br>2. 点击"开始构建" | 弹窗显示进度条，striped动画，完成后列表自动刷新 | P0 | E2E测试 | Week5完成标准 |
| ACC_006 | 验收标准5:执行历史支持查看缩减率与明细 | 存在至少1条执行记录 | 1. 进入执行记录页面<br>2. 点击某行"详情" | 抽屉显示缩减率数值（百分比格式）和选中用例列表（带风险分颜色） | P0 | E2E测试 | Week5完成标准 |