<template>
  <div class="layout">
    <el-container>
      <!-- 侧边栏 -->
      <el-aside width="240px" v-if="currentModule !== 'meta-projects'">
        <div class="logo" @click="router.push('/home')" style="cursor: pointer;">
          <img :src="logoImage" alt="TestHub" class="logo-img" />
        </div>
        <el-menu
          :default-active="$route.path"
          router
          background-color="var(--th-sidebar-bg)"
          text-color="var(--th-sidebar-text)"
          active-text-color="var(--th-sidebar-text-active)"
        >
          <!-- AI用例生成模块菜单 -->
          <template v-if="currentModule === 'ai-generation'">
            <el-sub-menu index="requirement">
              <template #title>
                <el-icon><MagicStick /></el-icon>
                <span>{{ $t('menu.intelligentCaseGeneration') }}</span>
              </template>
              <el-menu-item index="/ai-generation/requirement-analysis">{{ $t('menu.aiCaseGeneration') }}</el-menu-item>
              <el-menu-item index="/ai-generation/generated-testcases">{{ $t('menu.aiGeneratedTestcases') }}</el-menu-item>
            </el-sub-menu>
            <el-menu-item index="/ai-generation/knowledge-base">
              <el-icon><FolderOpened /></el-icon>
              <span>{{ $t('menu.knowledgeBase') }}</span>
            </el-menu-item>
            <el-menu-item index="/ai-generation/projects">
              <el-icon><Folder /></el-icon>
              <span>{{ $t('menu.projectManagement') }}</span>
            </el-menu-item>
            <el-menu-item index="/ai-generation/testcases">
              <el-icon><Document /></el-icon>
              <span>{{ $t('menu.testCases') }}</span>
            </el-menu-item>
            <el-menu-item index="/ai-generation/versions">
              <el-icon><Flag /></el-icon>
              <span>{{ $t('menu.versionManagement') }}</span>
            </el-menu-item>
            <el-sub-menu index="reviews">
              <template #title>
                <el-icon><Check /></el-icon>
                <span>{{ $t('menu.reviewManagement') }}</span>
              </template>
              <el-menu-item index="/ai-generation/reviews">{{ $t('menu.reviewList') }}</el-menu-item>
              <el-menu-item index="/ai-generation/review-templates">{{ $t('menu.reviewTemplates') }}</el-menu-item>
            </el-sub-menu>

            <el-menu-item index="/ai-generation/executions">
              <el-icon><VideoPlay /></el-icon>
              <span>{{ $t('menu.testPlan') }}</span>
            </el-menu-item>
            <el-menu-item index="/ai-generation/reports">
              <el-icon><DataAnalysis /></el-icon>
              <span>{{ $t('menu.testReport') }}</span>
            </el-menu-item>
          </template>

          <!-- 接口测试模块菜单 -->
          <template v-else-if="currentModule === 'api-testing'">
            <el-menu-item index="/api-testing/dashboard">
              <el-icon><Odometer /></el-icon>
              <span>{{ $t('menu.dashboard') }}</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/projects">
              <el-icon><Folder /></el-icon>
              <span>{{ $t('menu.projectManagement') }}</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/interfaces">
              <el-icon><Link /></el-icon>
              <span>{{ $t('menu.interfaceManagement') }}</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/automation">
              <el-icon><VideoPlay /></el-icon>
              <span>{{ $t('menu.automationTesting') }}</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/history">
              <el-icon><Timer /></el-icon>
              <span>{{ $t('menu.requestHistory') }}</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/environments">
              <el-icon><Setting /></el-icon>
              <span>{{ $t('menu.environmentManagement') }}</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/reports">
              <el-icon><DataAnalysis /></el-icon>
              <span>{{ $t('menu.testReport') }}</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/scheduled-tasks">
              <el-icon><AlarmClock /></el-icon>
              <span>{{ $t('menu.scheduledTasks') }}</span>
            </el-menu-item>
            <el-menu-item index="/api-testing/notification-logs">
              <el-icon><Bell /></el-icon>
              <span>{{ $t('menu.notificationList') }}</span>
            </el-menu-item>
          </template>

          <!-- UI自动化测试模块菜单 -->
          <template v-else-if="currentModule === 'ui-automation'">
            <el-menu-item index="/ui-automation/dashboard">
              <el-icon><Odometer /></el-icon>
              <span>{{ $t('menu.dashboard') }}</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/projects">
              <el-icon><Folder /></el-icon>
              <span>{{ $t('menu.projectManagement') }}</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/elements-enhanced">
              <el-icon><Aim /></el-icon>
              <span>{{ $t('menu.elementManagement') }}</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/test-cases">
              <el-icon><Document /></el-icon>
              <span>{{ $t('menu.caseManagement') }}</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/scripts-enhanced">
              <el-icon><Edit /></el-icon>
              <span>{{ $t('menu.scriptGeneration') }}</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/scripts">
              <el-icon><DocumentCopy /></el-icon>
              <span>{{ $t('menu.scriptList') }}</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/suites">
              <el-icon><Collection /></el-icon>
              <span>{{ $t('menu.suiteManagement') }}</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/executions">
              <el-icon><VideoPlay /></el-icon>
              <span>{{ $t('menu.executionRecords') }}</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/reports">
              <el-icon><DataAnalysis /></el-icon>
              <span>{{ $t('menu.testReport') }}</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/scheduled-tasks">
              <el-icon><AlarmClock /></el-icon>
              <span>{{ $t('menu.scheduledTasks') }}</span>
            </el-menu-item>
            <el-menu-item index="/ui-automation/notification-logs">
              <el-icon><Bell /></el-icon>
              <span>{{ $t('menu.notificationList') }}</span>
            </el-menu-item>
          </template>

          <!-- APP自动化测试模块菜单 -->
          <template v-else-if="currentModule === 'app-automation'">
            <el-menu-item index="/app-automation/dashboard">
              <el-icon><Odometer /></el-icon>
              <span>{{ $t('menu.appDashboard') }}</span>
            </el-menu-item>
            <el-menu-item index="/app-automation/projects">
              <el-icon><Folder /></el-icon>
              <span>{{ $t('menu.appProjectManagement') }}</span>
            </el-menu-item>
            <el-menu-item index="/app-automation/devices">
              <el-icon><Cellphone /></el-icon>
              <span>{{ $t('menu.appDeviceManagement') }}</span>
            </el-menu-item>
            <el-menu-item index="/app-automation/packages">
              <el-icon><Collection /></el-icon>
              <span>{{ $t('menu.appPackageManagement') }}</span>
            </el-menu-item>
            <el-menu-item index="/app-automation/elements">
              <el-icon><Aim /></el-icon>
              <span>{{ $t('menu.appElementManagement') }}</span>
            </el-menu-item>
            <el-menu-item index="/app-automation/scene-builder">
              <el-icon><Connection /></el-icon>
              <span>{{ $t('menu.appSceneBuilder') }}</span>
            </el-menu-item>
            <el-menu-item index="/app-automation/test-cases">
              <el-icon><Document /></el-icon>
              <span>{{ $t('menu.appTestCases') }}</span>
            </el-menu-item>
            <el-menu-item index="/app-automation/test-suites">
              <el-icon><FolderOpened /></el-icon>
              <span>{{ $t('menu.appTestSuites') }}</span>
            </el-menu-item>
            <el-menu-item index="/app-automation/executions">
              <el-icon><VideoPlay /></el-icon>
              <span>{{ $t('menu.appExecutionRecords') }}</span>
            </el-menu-item>
            <el-menu-item index="/app-automation/reports">
              <el-icon><DataAnalysis /></el-icon>
              <span>{{ $t('menu.appTestReports') }}</span>
            </el-menu-item>
            <el-menu-item index="/app-automation/scheduled-tasks">
              <el-icon><AlarmClock /></el-icon>
              <span>{{ $t('menu.appScheduledTasks') }}</span>
            </el-menu-item>
            <el-menu-item index="/app-automation/notification-logs">
              <el-icon><Bell /></el-icon>
              <span>{{ $t('menu.appNotificationList') }}</span>
            </el-menu-item>
          </template>

          <!-- AI 智能模式模块菜单 -->
          <template v-else-if="currentModule === 'ai-intelligent-mode'">
            <el-menu-item index="/ai-intelligent-mode/projects">
              <el-icon><Folder /></el-icon>
              <span>{{ $t('menu.aiProjectManagement') }}</span>
            </el-menu-item>
            <el-menu-item index="/ai-intelligent-mode/testing">
              <el-icon><VideoPlay /></el-icon>
              <span>{{ $t('menu.aiIntelligentTesting') }}</span>
            </el-menu-item>
            <el-menu-item index="/ai-intelligent-mode/cases">
              <el-icon><Document /></el-icon>
              <span>{{ $t('menu.aiCaseManagement') }}</span>
            </el-menu-item>
            <el-menu-item index="/ai-intelligent-mode/execution-records">
              <el-icon><Timer /></el-icon>
              <span>{{ $t('menu.aiExecutionRecords') }}</span>
            </el-menu-item>
          </template>

          <!-- 项目管理模块 - 不显示侧边菜单 -->


          <!-- 配置中心模块菜单 -->
          <template v-else-if="currentModule === 'configuration'">
            <el-menu-item index="/configuration/project-center">
              <el-icon><Folder /></el-icon>
              <span>{{ $t('menu.projectManagementCenter') }}</span>
            </el-menu-item>
            <el-sub-menu index="ai-case-generation">
              <template #title>
                <el-icon><MagicStick /></el-icon>
                <span>{{ $t('menu.aiCaseGenerationConfig') }}</span>
              </template>
              <el-menu-item index="/configuration/ai-model">
                <el-icon><Cpu /></el-icon>
                <span>{{ $t('menu.aiModelConfig') }}</span>
              </el-menu-item>
              <el-menu-item index="/configuration/prompt-config">
                <el-icon><Edit /></el-icon>
                <span>{{ $t('menu.promptConfigCenter') }}</span>
              </el-menu-item>
              <el-menu-item index="/configuration/generation-config">
                <el-icon><Setting /></el-icon>
                <span>{{ $t('menu.generationConfig') }}</span>
              </el-menu-item>
            </el-sub-menu>
            <el-menu-item index="/configuration/knowledge-base">
              <el-icon><FolderOpened /></el-icon>
              <span>{{ $t('menu.knowledgeBaseConfig') }}</span>
            </el-menu-item>
            <el-menu-item index="/configuration/ui-env">
              <el-icon><Monitor /></el-icon>
              <span>{{ $t('menu.uiEnvConfig') }}</span>
            </el-menu-item>
            <el-menu-item index="/configuration/app-env">
              <el-icon><Cellphone /></el-icon>
              <span>{{ $t('menu.appEnvConfig') }}</span>
            </el-menu-item>
            <el-menu-item index="/configuration/ocr-config">
              <el-icon><Search /></el-icon>
              <span>{{ $t('menu.ocrConfig') }}</span>
            </el-menu-item>
            <el-menu-item index="/configuration/ai-mode">
              <el-icon><MagicStick /></el-icon>
              <span>{{ $t('menu.aiModeConfig') }}</span>
            </el-menu-item>
            <el-menu-item index="/configuration/scheduled-task">
              <el-icon><Timer /></el-icon>
              <span>{{ $t('menu.scheduledTaskConfig') }}</span>
            </el-menu-item>
            <el-menu-item index="/configuration/dify">
              <el-icon><ChatDotRound /></el-icon>
              <span>{{ $t('menu.difyConfig') }}</span>
            </el-menu-item>
            <el-menu-item index="/configuration/theme">
              <el-icon><Brush /></el-icon>
              <span>{{ $t('menu.themeConfig') }}</span>
            </el-menu-item>
          </template>
        </el-menu>
      </el-aside>

      <!-- 主体内容 -->
    <el-container>
      <!-- 顶部导航 -->
      <el-header height="60px" :class="{ 'header-full': currentModule === 'meta-projects' }">
        <div class="header-content">
            <div class="header-left">
              <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ path: '/home' }">{{ $t('nav.home') }}</el-breadcrumb-item>
                <el-breadcrumb-item v-if="moduleName">{{ moduleName }}</el-breadcrumb-item>
                <el-breadcrumb-item v-if="showProjectManagement">{{ $t('menu.projectManagementCenter') }}</el-breadcrumb-item>
                <el-breadcrumb-item>{{ breadcrumbTitle }}</el-breadcrumb-item>
              </el-breadcrumb>
            </div>
            <div class="header-right">
              <!-- 语言切换 -->
              <el-dropdown @command="handleLanguageChange" class="language-dropdown">
                <span class="icon-button icon-button--lang" :title="currentLanguage">
                  <el-icon><Compass /></el-icon>
                  <span class="lang-code">{{ appStore.language === 'zh-cn' ? 'ZH' : 'EN' }}</span>
                  <el-icon class="caret"><ArrowDown /></el-icon>
                </span>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="zh-cn" :disabled="appStore.language === 'zh-cn'">
                      <span class="dropdown-flag">🇨🇳</span> {{ $t('nav.zhCN') }}
                    </el-dropdown-item>
                    <el-dropdown-item command="en" :disabled="appStore.language === 'en'">
                      <span class="dropdown-flag">🇺🇸</span> English
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>

              <!-- 主题切换 -->
              <span class="icon-button" :title="appStore.theme === 'hoppscotch-light' ? $t('nav.themeDark') : $t('nav.themeLight')" @click="toggleTheme">
                <el-icon>
                  <Moon v-if="appStore.theme === 'hoppscotch-light'" />
                  <Sunny v-else />
                </el-icon>
              </span>

              <!-- 用户信息 -->
              <el-dropdown @command="handleCommand" class="user-dropdown">
                <span class="icon-button" :title="userStore.user?.username">
                  <el-avatar :size="20" :src="defaultAvatar" />
                </span>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="profile">{{ $t('nav.profile') }}</el-dropdown-item>
                    <el-dropdown-item divided command="logout">{{ $t('nav.logout') }}</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>
        </el-header>

        <!-- 页面内容 -->
        <el-main>
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useAppStore } from '@/stores/app'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'
import defaultAvatar from '@/assets/images/user-avatar.svg'
import {
  Monitor, Folder, Document, Flag, Check, Collection, VideoPlay,
  DataAnalysis, ChatDotRound, DocumentCopy, Link, MagicStick,
  Odometer, Timer, Setting, AlarmClock, Bell, Aim, Edit, Cpu, ArrowDown, Cellphone, Connection, FolderOpened, Brush, Moon, Sunny, Search
} from '@element-plus/icons-vue'
import logoSvg from '@/assets/images/logo.svg'
import logoHomePng from '@/assets/images/logo_home.png'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const appStore = useAppStore()
const { t } = useI18n()

const logoImage = computed(() => {
		return route.path === '/home' ? logoSvg : logoHomePng
	})
	

// 当前语言显示
const currentLanguage = computed(() => {
  return appStore.language === 'zh-cn' ? t('nav.zhCN') : 'English'
})

const userAvatarUrl = computed(() => {
  const avatar = userStore.user?.avatar
  if (avatar) {
    if (avatar.startsWith('http://') || avatar.startsWith('https://') || avatar.startsWith('/')) {
      return avatar
    }
    return `/media/${avatar}`
  }
  return defaultAvatar
})

// 切换语言（无需刷新页面）
const handleLanguageChange = (lang) => {
  appStore.setLanguage(lang)
  ElMessage.success(t('nav.languageSwitched'))
}

const toggleTheme = () => {
  appStore.setTheme(appStore.theme === 'hoppscotch-light' ? 'hoppscotch-dark' : 'hoppscotch-light')
}

const currentModule = computed(() => {
  if (route.path.startsWith('/ai-generation')) return 'ai-generation'
  if (route.path.startsWith('/api-testing')) return 'api-testing'
  if (route.path.startsWith('/ui-automation')) return 'ui-automation'
  if (route.path.startsWith('/app-automation')) return 'app-automation'
  if (route.path.startsWith('/ai-intelligent-mode')) return 'ai-intelligent-mode'
  if (route.path.startsWith('/configuration')) return 'configuration'
  if (route.path.startsWith('/meta-projects')) return 'meta-projects'
  return ''
})

const moduleName = computed(() => {
  const map = {
    'ai-generation': t('modules.aiGeneration'),
    'api-testing': t('modules.apiTesting'),
    'ui-automation': t('modules.uiAutomation'),
    'app-automation': t('modules.appAutomation'),
    'ai-intelligent-mode': t('modules.aiIntelligentMode'),
    'configuration': t('modules.configuration'),
    'meta-projects': t('modules.unifiedProject')
  }
  return map[currentModule.value] || ''
})

const breadcrumbTitle = computed(() => {
  const routeMap = {
    // AI用例生成
    '/ai-generation/requirement-analysis': t('menu.aiCaseGeneration'),
    '/ai-generation/generated-testcases': t('menu.aiGeneratedTestcases'),
    '/ai-generation/knowledge-base': t('menu.knowledgeBase'),
    '/ai-generation/projects': t('menu.projectManagement'),
    '/ai-generation/testcases': t('menu.testCases'),
    '/ai-generation/versions': t('menu.versionManagement'),
    '/ai-generation/reviews': t('menu.reviewList'),
    '/ai-generation/review-templates': t('menu.reviewTemplates'),
    '/ai-generation/testsuites': t('menu.suiteManagement'),
    '/ai-generation/executions': t('menu.executionRecords'),
    '/ai-generation/reports': t('menu.testReport'),

    // 接口测试
    '/api-testing/dashboard': t('menu.dashboard'),
    '/api-testing/projects': t('menu.projectManagement'),
    '/api-testing/interfaces': t('menu.interfaceManagement'),
    '/api-testing/automation': t('menu.automationTesting'),
    '/api-testing/history': t('menu.requestHistory'),
    '/api-testing/environments': t('menu.environmentManagement'),
    '/api-testing/reports': t('menu.testReport'),
    '/api-testing/scheduled-tasks': t('menu.scheduledTasks'),
    '/api-testing/parameterized-data': t('menu.parameterizedData'),
    '/api-testing/notification-logs': t('menu.notificationList'),

    // UI自动化测试
    '/ui-automation/dashboard': t('menu.dashboard'),
    '/ui-automation/projects': t('menu.projectManagement'),
    '/ui-automation/elements-enhanced': t('menu.elementManagement'),
    '/ui-automation/test-cases': t('menu.caseManagement'),
    '/ui-automation/scripts-enhanced': t('menu.scriptGeneration'),
    '/ui-automation/scripts': t('menu.scriptList'),
    '/ui-automation/suites': t('menu.suiteManagement'),
    '/ui-automation/executions': t('menu.executionRecords'),
    '/ui-automation/reports': t('menu.testReport'),
    '/ui-automation/scheduled-tasks': t('menu.scheduledTasks'),
    '/ui-automation/notification-logs': t('menu.notificationList'),

    // APP自动化测试
    '/app-automation/dashboard': t('menu.appDashboard'),
    '/app-automation/projects': t('menu.appProjectManagement'),
    '/app-automation/devices': t('menu.appDeviceManagement'),
    '/app-automation/packages': t('menu.appPackageManagement'),
    '/app-automation/elements': t('menu.appElementManagement'),
    '/app-automation/scene-builder': t('menu.appSceneBuilder'),
    '/app-automation/test-cases': t('menu.appTestCases'),
    '/app-automation/test-suites': t('menu.appTestSuites'),
    '/app-automation/scheduled-tasks': t('menu.appScheduledTasks'),
    '/app-automation/notification-logs': t('menu.appNotificationList'),
    '/app-automation/executions': t('menu.appExecutionRecords'),
    '/app-automation/reports': t('menu.appTestReports'),

    // AI 智能模式
    '/ai-intelligent-mode/testing': t('menu.aiIntelligentTesting'),
    '/ai-intelligent-mode/projects': t('menu.aiProjectManagement'),
    '/ai-intelligent-mode/cases': t('menu.aiCaseManagement'),
    '/ai-intelligent-mode/execution-records': t('menu.aiExecutionRecords'),


    // 项目管理
    '/configuration/project-center': t('menu.projectManagementCenter'),
    '/configuration/meta-projects': t('menu.projectManagementCenter'),

    // 配置中心
    '/configuration/ai-model': t('menu.aiModelConfig'),
    '/configuration/prompt-config': t('menu.promptConfigCenter'),
    '/configuration/generation-config': t('menu.generationConfig'),
    '/configuration/knowledge-base': t('menu.knowledgeBaseConfig'),
    '/configuration/ui-env': t('menu.uiEnvConfig'),
    '/configuration/ai-mode': t('menu.aiModeConfig'),
    '/configuration/scheduled-task': t('menu.scheduledTaskConfig'),
    '/configuration/dify': t('menu.difyConfig'),
    '/configuration/theme': t('menu.themeConfig'),

    '/profile': t('nav.profile')
  }

  const path = route.path
  if (path.match(/^\/configuration\/meta-projects\/[^/]+$/)) {
    const queryName = route.query.name
    const nameStr = Array.isArray(queryName) ? queryName[0] : queryName
    const projectName = nameStr ? decodeURIComponent(nameStr) : sessionStorage.getItem('metaProjectName')
    return projectName || t('menu.projectManagementCenter')
  }

  return routeMap[path] || route.meta.title || ''
})

const showProjectManagement = computed(() => {
  return route.path.startsWith('/configuration/meta-projects/')
})

const handleCommand = (command) => {
  if (command === 'logout') {
    userStore.logout()
    ElMessage.success(t('nav.logoutSuccess'))
    router.push('/login')
  } else if (command === 'profile') {
    router.push('/ai-generation/profile')
  }
}
</script>

<style lang="scss" scoped>
.layout {
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}

.layout > .el-container {
  height: 100%;
  overflow: hidden;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--th-sidebar-bg);
  color: var(--th-sidebar-text);
  border-bottom: 1px solid var(--th-sidebar-border);
  flex-shrink: 0;

		.logo-img {
			width: 100%;
			height: 100%;
			object-fit: fill;
		}
	}

.el-aside {
  background: var(--th-sidebar-bg);
  border-right: 1px solid var(--th-sidebar-border);
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: width 0.3s ease;
  width: 240px !important;

  .el-menu {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    border-right: none;
    
    &::-webkit-scrollbar {
      width: 0;
    }
  }
}

.el-menu {
  :deep(.el-sub-menu__title),
  :deep(.el-menu-item) {
    font-size: 14px;
  }
}

/* 侧边栏菜单文字溢出截断 */
:deep(.el-menu-item span),
:deep(.el-sub-menu__title span) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.el-menu--collapse {
  width: 64px !important;
  
  :deep(.el-sub-menu__title),
  :deep(.el-menu-item) {
    padding-left: 20px !important;
  }
  
  :deep(.el-sub-menu__title span),
  :deep(.el-menu-item span) {
    display: none;
  }
}

.el-container .el-container {
  height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.el-header {
  background: var(--th-header-bg);
  border-bottom: 1px solid var(--th-header-border);
  box-shadow: var(--th-header-shadow);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  padding: 0;
  flex-shrink: 0;
  height: 60px !important;

  &.header-full {
    .header-content {
      max-width: 100%;
    }
  }

  .header-content {
    height: 100%;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 20px;
    max-width: calc(100% - 240px);
  }

  .header-left {
    flex: 1;
    overflow: hidden;
    
    :deep(.el-breadcrumb) {
      font-size: 14px;
    }
  }

  .user-info {
    display: flex;
    align-items: center;
    cursor: pointer;
    white-space: nowrap;

    .username {
      margin: 0 8px;
      color: var(--th-color-text);
      font-size: 14px;
    }
  }
}

.header-right {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .icon-button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border-radius: 10px;
    color: var(--th-color-text);
    background: transparent;
    cursor: pointer;
    transition: background 0.2s ease, color 0.2s ease;
  }

  .icon-button:hover {
    color: var(--th-color-primary);
    background: transparent;
  }

  .icon-button--lang {
    width: auto;
    padding: 0 10px;
    gap: 6px;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.6px;
  }

  .icon-button--lang .lang-code {
    line-height: 1;
  }

  .icon-button--lang .caret {
    font-size: 12px;
    opacity: 0.7;
  }

  :deep(.icon-only-item) {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 44px;
  }

  :deep(.icon-button .el-avatar) {
    width: 16px;
    height: 16px;
    background: transparent;
  }

  .language-dropdown {
    .language-selector {
      display: flex;
      align-items: center;
      cursor: pointer;
      color: var(--th-color-text);
      font-size: 14px;
      outline: none;

      &:focus {
        outline: none;
      }

      .language-flag {
        font-size: 18px;
        margin-right: 5px;
        line-height: 1;
      }

      span {
        margin: 0 4px;
      }

      &:hover {
        color: var(--th-color-primary);
      }
    }
  }

  .dropdown-flag {
    font-size: 16px;
    margin-right: 5px;
  }

  .user-dropdown {
    .user-info {
      display: flex;
      align-items: center;
      cursor: pointer;
      white-space: nowrap;

      .username {
        margin: 0 8px;
        color: var(--th-color-text);
      }
    }
  }



:deep(.el-menu) {
  background: transparent !important;
  border-right: none;
}

:deep(.el-menu-item),
:deep(.el-sub-menu__title) {
  color: var(--th-sidebar-text) !important;
  border-radius: 10px;
  margin: 4px 10px;
  height: 40px;
  line-height: 40px;
  font-family: var(--th-font-display);
  font-weight: 600;
  letter-spacing: 0.2px;
}

:deep(.el-menu-item:hover),
:deep(.el-sub-menu__title:hover) {
  color: var(--th-sidebar-text-hover) !important;
  background: var(--th-sidebar-item-bg-hover) !important;
}

:deep(.el-menu-item.is-active) {
  color: var(--th-sidebar-text-active) !important;
  background: var(--th-sidebar-item-bg-active) !important;
}

.el-main {
  background-color: var(--th-color-bg);
  padding: 20px;
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}

@media screen and (max-width: 1920px) {
  .el-aside {
  background: var(--th-sidebar-bg);
  border-right: 1px solid var(--th-sidebar-border);
    width: 220px !important;
  }
  
  

:deep(.el-menu) {
  background: transparent !important;
  border-right: none;
}

:deep(.el-menu-item),
:deep(.el-sub-menu__title) {
  color: var(--th-sidebar-text) !important;
  border-radius: 10px;
  margin: 4px 10px;
  height: 40px;
  line-height: 40px;
  font-family: var(--th-font-display);
  font-weight: 600;
  letter-spacing: 0.2px;
}

:deep(.el-menu-item:hover),
:deep(.el-sub-menu__title:hover) {
  color: var(--th-sidebar-text-hover) !important;
  background: var(--th-sidebar-item-bg-hover) !important;
}

:deep(.el-menu-item.is-active) {
  color: var(--th-sidebar-text-active) !important;
  background: var(--th-sidebar-item-bg-active) !important;
}

.el-main {
    padding: 18px;
  }
}

@media screen and (max-width: 1600px) {
  .el-aside {
  background: var(--th-sidebar-bg);
  border-right: 1px solid var(--th-sidebar-border);
    width: 200px !important;
  }
  
  

:deep(.el-menu) {
  background: transparent !important;
  border-right: none;
}

:deep(.el-menu-item),
:deep(.el-sub-menu__title) {
  color: var(--th-sidebar-text) !important;
  border-radius: 10px;
  margin: 4px 10px;
  height: 40px;
  line-height: 40px;
  font-family: var(--th-font-display);
  font-weight: 600;
  letter-spacing: 0.2px;
}

:deep(.el-menu-item:hover),
:deep(.el-sub-menu__title:hover) {
  color: var(--th-sidebar-text-hover) !important;
  background: var(--th-sidebar-item-bg-hover) !important;
}

:deep(.el-menu-item.is-active) {
  color: var(--th-sidebar-text-active) !important;
  background: var(--th-sidebar-item-bg-active) !important;
}

.el-main {
    padding: 16px;
  }

  .el-menu {
    :deep(.el-sub-menu__title),
    :deep(.el-menu-item) {
      font-size: 13px;
    }
  }
}

@media screen and (max-width: 1440px) {
  .el-aside {
  background: var(--th-sidebar-bg);
  border-right: 1px solid var(--th-sidebar-border);
    width: 180px !important;
  }
  
  

:deep(.el-menu) {
  background: transparent !important;
  border-right: none;
}

:deep(.el-menu-item),
:deep(.el-sub-menu__title) {
  color: var(--th-sidebar-text) !important;
  border-radius: 10px;
  margin: 4px 10px;
  height: 40px;
  line-height: 40px;
  font-family: var(--th-font-display);
  font-weight: 600;
  letter-spacing: 0.2px;
}

:deep(.el-menu-item:hover),
:deep(.el-sub-menu__title:hover) {
  color: var(--th-sidebar-text-hover) !important;
  background: var(--th-sidebar-item-bg-hover) !important;
}

:deep(.el-menu-item.is-active) {
  color: var(--th-sidebar-text-active) !important;
  background: var(--th-sidebar-item-bg-active) !important;
}

.el-main {
    padding: 14px;
  }

  .el-menu {
    :deep(.el-sub-menu__title),
    :deep(.el-menu-item) {
      font-size: 13px;
    }
  }
}

@media screen and (max-width: 1366px) {
  .el-aside {
  background: var(--th-sidebar-bg);
  border-right: 1px solid var(--th-sidebar-border);
    width: 180px !important;
  }
  
  

:deep(.el-menu) {
  background: transparent !important;
  border-right: none;
}

:deep(.el-menu-item),
:deep(.el-sub-menu__title) {
  color: var(--th-sidebar-text) !important;
  border-radius: 10px;
  margin: 4px 10px;
  height: 40px;
  line-height: 40px;
  font-family: var(--th-font-display);
  font-weight: 600;
  letter-spacing: 0.2px;
}

:deep(.el-menu-item:hover),
:deep(.el-sub-menu__title:hover) {
  color: var(--th-sidebar-text-hover) !important;
  background: var(--th-sidebar-item-bg-hover) !important;
}

:deep(.el-menu-item.is-active) {
  color: var(--th-sidebar-text-active) !important;
  background: var(--th-sidebar-item-bg-active) !important;
}

.el-main {
    padding: 12px;
  }

  .el-header {
    height: 56px !important;
  }
  
  .el-menu {
    :deep(.el-sub-menu__title),
    :deep(.el-menu-item) {
      font-size: 12px;
    }
  }
}

@media screen and (max-width: 1280px) {
  .el-aside {
  background: var(--th-sidebar-bg);
  border-right: 1px solid var(--th-sidebar-border);
    width: 160px !important;
  }
  
  

:deep(.el-menu) {
  background: transparent !important;
  border-right: none;
}

:deep(.el-menu-item),
:deep(.el-sub-menu__title) {
  color: var(--th-sidebar-text) !important;
  border-radius: 10px;
  margin: 4px 10px;
  height: 40px;
  line-height: 40px;
  font-family: var(--th-font-display);
  font-weight: 600;
  letter-spacing: 0.2px;
}

:deep(.el-menu-item:hover),
:deep(.el-sub-menu__title:hover) {
  color: var(--th-sidebar-text-hover) !important;
  background: var(--th-sidebar-item-bg-hover) !important;
}

:deep(.el-menu-item.is-active) {
  color: var(--th-sidebar-text-active) !important;
  background: var(--th-sidebar-item-bg-active) !important;
}

.el-main {
    padding: 12px;
  }

  .el-header {
    height: 56px !important;
    
    .header-content {
      padding: 0 15px;
    }
  }
  
  .el-menu {
    :deep(.el-sub-menu__title),
    :deep(.el-menu-item) {
      font-size: 12px;
      padding-left: 15px !important;
    }
  }
}

@media screen and (max-width: 1024px) {
  .el-aside {
  background: var(--th-sidebar-bg);
  border-right: 1px solid var(--th-sidebar-border);
    width: 140px !important;
  }
  
  

:deep(.el-menu) {
  background: transparent !important;
  border-right: none;
}

:deep(.el-menu-item),
:deep(.el-sub-menu__title) {
  color: var(--th-sidebar-text) !important;
  border-radius: 10px;
  margin: 4px 10px;
  height: 40px;
  line-height: 40px;
  font-family: var(--th-font-display);
  font-weight: 600;
  letter-spacing: 0.2px;
}

:deep(.el-menu-item:hover),
:deep(.el-sub-menu__title:hover) {
  color: var(--th-sidebar-text-hover) !important;
  background: var(--th-sidebar-item-bg-hover) !important;
}

:deep(.el-menu-item.is-active) {
  color: var(--th-sidebar-text-active) !important;
  background: var(--th-sidebar-item-bg-active) !important;
}

.el-main {
    padding: 10px;
  }

  .el-header {
    height: 52px !important;
    
    .header-content {
      padding: 0 12px;
    }
  }
  
  .el-menu {
    :deep(.el-sub-menu__title),
    :deep(.el-menu-item) {
      font-size: 12px;
      padding-left: 12px !important;
    }
  }
  
  .user-info .username {
    display: none;
  }
}

@media screen and (max-width: 768px) {
  .el-aside {
  background: var(--th-sidebar-bg);
  border-right: 1px solid var(--th-sidebar-border);
    position: fixed;
    left: 0;
    top: 0;
    z-index: 1000;
    width: 240px !important;
    transform: translateX(-100%);
    transition: transform 0.3s ease;
    
    &.mobile-open {
      transform: translateX(0);
    }
  }
  
  

:deep(.el-menu) {
  background: transparent !important;
  border-right: none;
}

:deep(.el-menu-item),
:deep(.el-sub-menu__title) {
  color: var(--th-sidebar-text) !important;
  border-radius: 10px;
  margin: 4px 10px;
  height: 40px;
  line-height: 40px;
  font-family: var(--th-font-display);
  font-weight: 600;
  letter-spacing: 0.2px;
}

:deep(.el-menu-item:hover),
:deep(.el-sub-menu__title:hover) {
  color: var(--th-sidebar-text-hover) !important;
  background: var(--th-sidebar-item-bg-hover) !important;
}

:deep(.el-menu-item.is-active) {
  color: var(--th-sidebar-text-active) !important;
  background: var(--th-sidebar-item-bg-active) !important;
}

.el-main {
    padding: 8px;
  }

  .el-header {
    height: 50px !important;
    
    .header-content {
      padding: 0 10px;
    }
    
    .header-left {
      :deep(.el-breadcrumb__item) {
        &:not(:last-child) {
          display: none;
        }
      }
    }
  }
}

@media screen and (max-width: 480px) {
  .el-aside {
  background: var(--th-sidebar-bg);
  border-right: 1px solid var(--th-sidebar-border);
    width: 220px !important;
  }
  
  

:deep(.el-menu) {
  background: transparent !important;
  border-right: none;
}

:deep(.el-menu-item),
:deep(.el-sub-menu__title) {
  color: var(--th-sidebar-text) !important;
  border-radius: 10px;
  margin: 4px 10px;
  height: 40px;
  line-height: 40px;
  font-family: var(--th-font-display);
  font-weight: 600;
  letter-spacing: 0.2px;
}

:deep(.el-menu-item:hover),
:deep(.el-sub-menu__title:hover) {
  color: var(--th-sidebar-text-hover) !important;
  background: var(--th-sidebar-item-bg-hover) !important;
}

:deep(.el-menu-item.is-active) {
  color: var(--th-sidebar-text-active) !important;
  background: var(--th-sidebar-item-bg-active) !important;
}

.el-main {
    padding: 6px;
  }

  .el-header {
    height: 48px !important;
    
    .header-content {
      padding: 0 8px;
    }
  }
  
  .user-info {
    .el-avatar {
      width: 28px !important;
      height: 28px !important;
    }
  }
}
</style>