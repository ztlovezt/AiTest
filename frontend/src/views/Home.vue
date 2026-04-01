<template>
  <div class="home-container">
    <div class="content-wrapper">
      <div class="header-actions">
        <el-dropdown @command="handleLanguageChange" class="language-dropdown">
          <span class="icon-button icon-button--lang" :title="$t('home.language.current')">
            <el-icon><Compass /></el-icon>
            <span class="lang-code">{{ currentLanguage === 'zh-cn' ? 'ZH' : 'EN' }}</span>
            <el-icon class="caret"><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="zh-cn" :disabled="currentLanguage === 'zh-cn'">
                <span class="dropdown-flag">🇨🇳</span> {{ $t('home.language.zhCN') }}
              </el-dropdown-item>
              <el-dropdown-item command="en" :disabled="currentLanguage === 'en'">
                <span class="dropdown-flag">🇺🇸</span> {{ $t('home.language.en') }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>

        <span class="icon-button" :title="appStore.theme === 'hoppscotch-light' ? $t('nav.themeDark') : $t('nav.themeLight')" @click="toggleTheme">
          <el-icon>
            <Moon v-if="appStore.theme === 'hoppscotch-light'" />
            <Sunny v-else />
          </el-icon>
        </span>

        <el-dropdown @command="handleCommand">
          <span class="icon-button" :title="userStore.user?.username || $t('home.user')">
            <el-avatar :size="20" :src="defaultAvatar" />
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">{{ $t('home.logout') }}</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
      <h1 class="main-title">{{ $t('home.title') }}</h1>
      <p class="subtitle">{{ $t('home.subtitle') }}</p>

      <div class="cards-container">
        <!-- AI用例生成 -->
        <div class="nav-card" @click="handleNavigate('ai')" role="button" tabindex="0">
          <div class="card-icon ai-icon">
            <el-icon>
              <MagicStick/>
            </el-icon>
          </div>
          <h3>{{ $t('home.aiCaseGeneration') }}</h3>
          <p>{{ $t('home.aiCaseGenerationDesc') }}</p>
        </div>

        <!-- 接口测试 -->
        <div class="nav-card" @click="handleNavigate('api')" role="button" tabindex="0">
          <div class="card-icon api-icon">
            <el-icon>
              <Link/>
            </el-icon>
          </div>
          <h3>{{ $t('home.apiTesting') }}</h3>
          <p>{{ $t('home.apiTestingDesc') }}</p>
        </div>

        <!-- UI自动化测试 -->
        <div class="nav-card" @click="handleNavigate('ui')" role="button" tabindex="0">
          <div class="card-icon ui-icon">
            <el-icon>
              <Monitor/>
            </el-icon>
          </div>
          <h3>{{ $t('home.uiAutomation') }}</h3>
          <p>{{ $t('home.uiAutomationDesc') }}</p>
        </div>

        <!-- APP自动化测试 -->
        <div class="nav-card" @click="handleNavigate('app')" role="button" tabindex="0">
          <div class="card-icon app-icon">
            <el-icon>
              <Cellphone/>
            </el-icon>
          </div>
          <h3>{{ $t('home.appAutomation') }}</h3>
          <p>{{ $t('home.appAutomationDesc') }}</p>
        </div>

        <!-- 数据工厂 -->
        <div class="nav-card" @click="handleNavigate('data')" role="button" tabindex="0">
          <div class="card-icon data-icon">
            <el-icon>
              <DataLine/>
            </el-icon>
          </div>
          <h3>{{ $t('home.dataFactory') }}</h3>
          <p>{{ $t('home.dataFactoryDesc') }}</p>
        </div>

        <!-- AI 智能模式 -->
        <div class="nav-card" @click="handleNavigate('ai-intelligent')" role="button" tabindex="0">
          <div class="card-icon ai-intelligent-icon">
            <el-icon>
              <Cpu/>
            </el-icon>
          </div>
          <h3>{{ $t('home.aiIntelligentMode') }}</h3>
          <p>{{ $t('home.aiIntelligentModeDesc') }}</p>
        </div>

        <!-- AI评测师 -->
        <div class="nav-card" @click="handleNavigate('assistant')" role="button" tabindex="0">
          <div class="card-icon assistant-icon">
            <el-icon>
              <ChatDotRound/>
            </el-icon>
          </div>
          <h3>{{ $t('home.aiEvaluator') }}</h3>
          <p>{{ $t('home.aiEvaluatorDesc') }}</p>
        </div>

        <!-- 配置中心 -->
        <div class="nav-card" @click="handleNavigate('config')" role="button" tabindex="0">
          <div class="card-icon config-icon">
            <el-icon>
              <Setting/>
            </el-icon>
          </div>
          <h3>{{ $t('home.configCenter') }}</h3>
          <p>{{ $t('home.configCenterDesc') }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import {computed} from 'vue'
import {useRouter} from 'vue-router'
import {useI18n} from 'vue-i18n'
import defaultAvatar from '@/assets/images/user-avatar.svg'
import {useUserStore} from '@/stores/user'
import {useAppStore} from '@/stores/app'
import {ElMessage, ElMessageBox} from 'element-plus'
import {
  MagicStick,
  Link,
  Monitor,
  DataLine,
  Cpu,
  Setting,
  ChatDotRound,
  ArrowDown,
  Cellphone,
  Compass,
  Moon,
  Sunny
} from '@element-plus/icons-vue'

const router = useRouter()
const {t} = useI18n()
const userStore = useUserStore()
const appStore = useAppStore()

// 当前语言
const currentLanguage = computed(() => appStore.language)

// 语言切换（无刷新）
const handleLanguageChange = (lang) => {
  appStore.setLanguage(lang)
}

const toggleTheme = () => {
  appStore.setTheme(appStore.theme === 'hoppscotch-light' ? 'hoppscotch-dark' : 'hoppscotch-light')
}

const handleCommand = (command) => {
  if (command === 'logout') {
    handleLogout()
  }
}

const handleLogout = () => {
  ElMessageBox.confirm(t('home.logoutConfirm'), t('common.tips'), {
    confirmButtonText: t('common.confirm'),
    cancelButtonText: t('common.cancel'),
    type: 'warning'
  }).then(() => {
    userStore.logout()
    router.push('/login')
    ElMessage.success(t('home.logoutSuccess'))
  }).catch(() => {
  })
}

const handleNavigate = (type) => {
  const routes = {
    'ai': '/ai-generation/requirement-analysis',
    'api': '/api-testing/dashboard',
    'ui': '/ui-automation/dashboard',
    'app': '/app-automation/dashboard',
    'ai-intelligent': '/ai-intelligent-mode/testing',
    'assistant': '/ai-generation/assistant',
    'config': '/configuration/project-center',
    'data': '/data-factory'
  }

  if (routes[type]) {
    router.push(routes[type])
  }
}
</script>

<style scoped lang="scss">
.home-container {
  min-height: 100vh;
  background: linear-gradient(180deg, var(--th-color-bg) 0%, var(--th-color-surface-muted) 100%);
  background:
    radial-gradient(1200px 600px at 10% -10%, color-mix(in srgb, var(--th-color-primary) 14%, transparent), transparent 60%),
    radial-gradient(900px 500px at 90% 10%, color-mix(in srgb, var(--th-color-info) 14%, transparent), transparent 55%),
    linear-gradient(180deg, var(--th-color-bg) 0%, var(--th-color-surface-muted) 100%);
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 24px;
  position: relative;
  overflow: hidden;
}

.home-container::before {
  content: "";
  position: absolute;
  width: 420px;
  height: 420px;
  border-radius: 50%;
  background: var(--th-color-primary-soft);
  background: color-mix(in srgb, var(--th-color-primary) 8%, transparent);
  top: -180px;
  right: -120px;
  filter: blur(2px);
}

.home-container::after {
  content: "";
  position: absolute;
  width: 360px;
  height: 360px;
  border-radius: 50%;
  background: rgba(34, 197, 94, 0.08);
  bottom: -160px;
  left: -120px;
  filter: blur(2px);
}

.content-wrapper {
  text-align: center;
  max-width: 1200px;
  width: 100%;
  position: relative;
  padding: 72px 0 32px;
  z-index: 1;
}

.header-actions {
  position: absolute;
  top: 0;
  right: 0;
  padding: 8px 12px;
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--th-header-bg);
  border: 1px solid var(--th-header-border);
  border-radius: 999px;
  box-shadow: var(--th-shadow-sm);
  backdrop-filter: blur(8px);

  .language-dropdown {
    .el-dropdown-link {
      display: flex;
      align-items: center;
      cursor: pointer;
      color: var(--th-color-text-muted);
      transition: color 0.2s ease;
      outline: none;

      &:focus-visible {
        outline: 3px solid var(--th-color-primary-soft);
        outline: 3px solid color-mix(in srgb, var(--th-color-primary) 35%, transparent);
        outline-offset: 2px;
        border-radius: 6px;
      }

      .language-icon {
        font-size: 18px;
        margin-right: 5px;
        line-height: 1;
      }

      .language-text {
        margin: 0 5px;
        font-size: 14px;
      }

      &:hover {
        color: var(--th-color-primary);
      }
    }
  }

  .el-dropdown-link {
    display: flex;
    align-items: center;
    cursor: pointer;
    color: var(--th-color-text-muted);
    transition: color 0.2s ease;
    outline: none;

    &:focus-visible {
      outline: 3px solid color-mix(in srgb, var(--th-color-primary) 35%, transparent);
      outline-offset: 2px;
      border-radius: 6px;
    }

    .username {
      margin: 0 8px;
      font-size: 14px;
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

.icon-button .el-avatar {
  width: 16px;
  height: 16px;
  background: transparent;
}

:deep(.icon-only-item) {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
}

.main-title {
  font-size: 3.4rem;
  color: var(--th-color-text);
  margin-bottom: 0.8rem;
  font-weight: 700;
  letter-spacing: 1px;
  font-family: var(--th-font-display);
}

.subtitle {
  font-size: 1.15rem;
  color: var(--th-color-text-muted);
  margin-bottom: 3.2rem;
}

.cards-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 28px;
  padding: 0 8px;
}

.nav-card {
  background: var(--th-color-surface);
  border-radius: var(--th-radius-lg);
  padding: 32px 22px;
  cursor: pointer;
  transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
  box-shadow: var(--th-shadow-sm);
  display: flex;
  flex-direction: column;
  align-items: center;
  border: 1px solid var(--th-color-border);
  animation: fade-up 0.6s ease both;

  &:hover {
    transform: translateY(-6px);
    box-shadow: var(--th-shadow-md);
    border-color: var(--th-color-primary-soft);
    border-color: color-mix(in srgb, var(--th-color-primary) 40%, transparent);
    background: var(--th-color-surface);
  }

  &:focus-visible {
    outline: 3px solid color-mix(in srgb, var(--th-color-primary) 35%, transparent);
    outline-offset: 4px;
  }

  h3 {
    font-size: 1.3rem;
    color: var(--th-color-text);
    margin: 20px 0 10px;
    font-family: var(--th-font-display);
    font-weight: 600;
  }

  p {
    color: var(--th-color-text-muted);
    line-height: 1.6;
    margin: 0;
    font-size: 0.95rem;
  }
}

.card-icon {
  width: 76px;
  height: 76px;
  border-radius: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 36px;
  margin-bottom: 8px;
  transition: transform 0.25s ease;
  background: var(--icon-bg);
  color: var(--icon-color);
  box-shadow: inset 0 0 0 1px rgba(31, 41, 55, 0.06);

  &.ai-icon {
    --icon-bg: var(--th-color-primary-soft);
    --icon-color: var(--th-color-primary-strong);
  }

  &.api-icon {
    --icon-bg: #e0f2fe;
    --icon-color: #2563eb;
  }

  &.ui-icon {
    --icon-bg: #fef3c7;
    --icon-color: #d97706;
  }

  &.data-icon {
    --icon-bg: #dcfce7;
    --icon-color: #16a34a;
  }

  &.app-icon {
    --icon-bg: #fce7f3;
    --icon-color: #db2777;
  }

  &.ai-intelligent-icon {
    --icon-bg: var(--th-color-primary-soft);
    --icon-color: var(--th-color-primary);
  }

  &.config-icon {
    --icon-bg: #ecfdf3;
    --icon-color: #0f766e;
  }

  &.assistant-icon {
    --icon-bg: #fff7ed;
    --icon-color: #ea580c;
  }
}

.nav-card:hover .card-icon {
  transform: translateY(-2px) scale(1.04);
}

.nav-card:nth-child(1) { animation-delay: 0.05s; }
.nav-card:nth-child(2) { animation-delay: 0.1s; }
.nav-card:nth-child(3) { animation-delay: 0.15s; }
.nav-card:nth-child(4) { animation-delay: 0.2s; }
.nav-card:nth-child(5) { animation-delay: 0.25s; }
.nav-card:nth-child(6) { animation-delay: 0.3s; }
.nav-card:nth-child(7) { animation-delay: 0.35s; }
.nav-card:nth-child(8) { animation-delay: 0.4s; }

@keyframes fade-up {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .nav-card {
    animation: none;
    transition: none;
  }

  .nav-card:hover {
    transform: none;
  }

  .nav-card:hover .card-icon {
    transform: none;
  }
}

@media screen and (max-width: 1600px) {
  .main-title {
    font-size: 3rem;
  }

  .subtitle {
    font-size: 1.1rem;
  }

  .cards-container {
    gap: 24px;
  }

  .nav-card {
    padding: 28px 20px;
  }
}

@media screen and (max-width: 1440px) {
  .main-title {
    font-size: 2.7rem;
  }

  .subtitle {
    font-size: 1rem;
  }

  .cards-container {
    gap: 22px;
  }

  .card-icon {
    width: 70px;
    height: 70px;
    font-size: 34px;
  }
}

@media screen and (max-width: 1280px) {
  .main-title {
    font-size: 2.4rem;
  }

  .subtitle {
    font-size: 0.98rem;
  }

  .cards-container {
    gap: 20px;
  }

  .nav-card {
    padding: 24px 18px;

    h3 {
      font-size: 1.2rem;
    }
  }
}

@media screen and (max-width: 1024px) {
  .home-container {
    padding: 18px;
  }

  .content-wrapper {
    padding-top: 64px;
  }

  .main-title {
    font-size: 2.1rem;
  }

  .subtitle {
    font-size: 0.95rem;
    margin-bottom: 2.6rem;
  }

  .cards-container {
    gap: 18px;
  }

  .nav-card {
    padding: 22px 16px;

    p {
      font-size: 0.9rem;
    }
  }

  .card-icon {
    width: 64px;
    height: 64px;
    font-size: 30px;
  }
}

@media screen and (max-width: 768px) {
  .home-container {
    padding: 14px;
  }

  .content-wrapper {
    padding-top: 56px;
  }

  .main-title {
    font-size: 1.8rem;
  }

  .subtitle {
    font-size: 0.88rem;
    margin-bottom: 2rem;
  }

  .cards-container {
    gap: 16px;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  }

  .nav-card {
    padding: 18px 12px;
    border-radius: var(--th-radius-md);

    h3 {
      font-size: 1.05rem;
      margin: 16px 0 6px;
    }

    p {
      font-size: 0.82rem;
    }
  }

  .card-icon {
    width: 56px;
    height: 56px;
    font-size: 26px;
  }

  .header-actions {
    padding: 6px 10px;

    .username {
      display: none;
    }
  }
}

@media screen and (max-width: 480px) {
  .home-container {
    padding: 10px;
  }

  .main-title {
    font-size: 1.5rem;
  }

  .subtitle {
    font-size: 0.8rem;
    margin-bottom: 1.6rem;
  }

  .cards-container {
    gap: 12px;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  }

  .nav-card {
    padding: 14px 10px;

    h3 {
      font-size: 0.95rem;
    }

    p {
      font-size: 0.76rem;
    }
  }

  .card-icon {
    width: 50px;
    height: 50px;
    font-size: 24px;
  }
}


</style>
