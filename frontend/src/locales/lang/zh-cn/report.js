export default {
  // 页面
  title: '测试报告',
  inDevelopment: '测试报告功能开发中...',

  // 筛选
  selectProject: '选择项目',
  timeRange: '时间范围',
  recentDays: '最近7天',
  recent14Days: '最近14天',
  recent30Days: '最近30天',
  customRange: '自定义范围',
  exportReport: '导出报告',

  // 统计卡片
  testPlan: '测试计划',
  activePlans: '活跃计划',
  progress: '进度',
  totalCases: '用例总数',
  passRate: '通过率',
  failedCases: '失败用例',
  defectsFound: '发现缺陷',

  // 图表标题
  executionStatusDistribution: '执行状态分布',
  dailyExecutionTrend: '每日执行趋势',
  failureDistribution: '失败用例优先级分布（缺陷分布）',
  failureTop10: '失败用例 TOP 10',
  aiEffectivenessAnalysis: 'AI生成效能分析',
  teamWorkload: '团队工作量统计',

  // 状态
  passed: '通过',
  failed: '失败',
  blocked: '阻塞',
  retest: '重测',
  untested: '未测',
  executionStatus: '执行状态',

  // AI效能指标
  adoptionRate: '生成采纳率',
  requirementCoverage: '需求覆盖率',
  savedHours: '节省工时估算',
  caseSource: '用例来源',
  aiGenerated: 'AI生成',
  manualCreated: '人工创建',

  // 团队工作量
  executionCount: '执行数量',
  executedCases: '执行用例',
  priorityDistribution: '优先级分布',

  // 其他
  noData: 'No Data',
  caseTitle: '用例标题',
  failureCount: '失败次数',
  exportInDevelopment: '报告导出功能开发中...',
  fetchProjectsFailed: '获取项目失败',
  fetchDashboardFailed: '获取概览数据失败',

  // 定时任务报告页面
  scheduleReport: {
    basicInfo: '基本信息',
    taskName: '任务名称',
    taskType: '任务类型',
    module: '模块',
    status: '状态',
    createdBy: '创建者',
    createdAt: '创建时间',
    executionHistory: '执行历史',
    executionDetail: '执行详情',
    allureReport: 'Allure 报告',
    viewReport: '查看报告',
    allureReportAvailable: 'Allure 测试报告已生成，点击上方按钮查看详细报告',
    noHistory: '暂无执行历史',
    fetchError: '获取执行详情失败',
    
    // 状态
    passed: '通过',
    failed: '失败',
    
    // API 请求详情
    requestName: '接口名称',
    requestMethod: '请求方法',
    requestUrl: '请求地址',
    statusCode: '状态码',
    responseTime: '响应时间',
    duration: '执行时长',
    environment: '执行环境',
    assertions: '断言结果',
    assertionName: '断言名称',
    assertionType: '断言类型',
    result: '执行结果',
    error: '错误信息',
    executionError: '执行错误',
    
    // 测试用例详情
    passedCases: '通过',
    skippedCases: '跳过',
    startTime: '开始时间',
    endTime: '结束时间',
    success: '成功',
    
    // 断言类型
    assertionTypes: {
      statusCode: '状态码',
      responseTime: '响应时间',
      contains: '包含',
      jsonPath: 'JSON路径',
      header: '响应头',
      equals: '相等',
      notEmpty: '非空',
      jsonSchema: 'JSON Schema'
    }
  }
}
