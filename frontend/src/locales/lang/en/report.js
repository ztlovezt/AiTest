export default {
  // Page
  title: 'Test Report',
  inDevelopment: 'Test report feature under development...',

  // Filters
  selectProject: 'Select Project',
  timeRange: 'Time Range',
  recentDays: 'Last 7 Days',
  recent14Days: 'Last 14 Days',
  recent30Days: 'Last 30 Days',
  customRange: 'Custom Range',
  exportReport: 'Export Report',

  // Stats Cards
  testPlan: 'Test Plan',
  activePlans: 'Active Plans',
  progress: 'Progress',
  totalCases: 'Total Cases',
  passRate: 'Pass Rate',
  failedCases: 'Failed Cases',
  defectsFound: 'Defects Found',

  // Chart Titles
  executionStatusDistribution: 'Execution Status Distribution',
  dailyExecutionTrend: 'Daily Execution Trend',
  failureDistribution: 'Failed Cases Priority Distribution (Defect Distribution)',
  failureTop10: 'Failed Cases TOP 10',
  aiEffectivenessAnalysis: 'AI Generation Effectiveness Analysis',
  teamWorkload: 'Team Workload Statistics',

  // Status
  passed: 'Passed',
  failed: 'Failed',
  blocked: 'Blocked',
  retest: 'Retest',
  untested: 'Untested',
  executionStatus: 'Execution Status',

  // AI Effectiveness Metrics
  adoptionRate: 'Adoption Rate',
  requirementCoverage: 'Requirement Coverage',
  savedHours: 'Saved Hours',
  caseSource: 'Case Source',
  aiGenerated: 'AI Generated',
  manualCreated: 'Manual Created',

  // Team Workload
  executionCount: 'Execution Count',
  executedCases: 'Executed Cases',
  priorityDistribution: 'Priority Distribution',

  // Others
  noData: 'No Data',
  caseTitle: 'Case Title',
  failureCount: 'Failure Count',
  exportInDevelopment: 'Report export feature under development...',
  fetchProjectsFailed: 'Failed to fetch projects',
  fetchDashboardFailed: 'Failed to fetch dashboard data',

  // Schedule Report Page
  scheduleReport: {
    basicInfo: 'Basic Info',
    taskName: 'Task Name',
    taskType: 'Task Type',
    module: 'Module',
    status: 'Status',
    createdBy: 'Created By',
    createdAt: 'Created At',
    executionHistory: 'Execution History',
    executionDetail: 'Execution Detail',
    allureReport: 'Allure Report',
    viewReport: 'View Report',
    allureReportAvailable: 'Allure test report has been generated, click the button above to view the detailed report',
    noHistory: 'No execution history',
    fetchError: 'Failed to fetch execution detail',
    
    // Status
    passed: 'Passed',
    failed: 'Failed',
    
    // API Request Detail
    requestName: 'Request Name',
    requestMethod: 'Request Method',
    requestUrl: 'Request URL',
    statusCode: 'Status Code',
    responseTime: 'Response Time',
    duration: 'Duration',
    environment: 'Environment',
    assertions: 'Assertions',
    assertionName: 'Assertion Name',
    assertionType: 'Assertion Type',
    result: 'Result',
    error: 'Error',
    executionError: 'Execution Error',
    
    // Test Case Detail
    passedCases: 'Passed',
    skippedCases: 'Skipped',
    startTime: 'Start Time',
    endTime: 'End Time',
    success: 'Success',
    
    // Assertion Types
    assertionTypes: {
      statusCode: 'Status Code',
      responseTime: 'Response Time',
      contains: 'Contains',
      jsonPath: 'JSON Path',
      header: 'Header',
      equals: 'Equals',
      notEmpty: 'Not Empty',
      jsonSchema: 'JSON Schema'
    }
  }
}
