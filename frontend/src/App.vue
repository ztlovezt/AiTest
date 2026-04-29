<template>
  <el-config-provider :locale="elementLocale">
    <div id="app">
      <router-view />
      <GlobalAgentFloating v-if="showFloatingAgent" />
    </div>
  </el-config-provider>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElConfigProvider } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { useAppStore } from '@/stores/app'
import GlobalAgentFloating from '@/components/agent/GlobalAgentFloating.vue'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import en from 'element-plus/es/locale/lang/en'

const userStore = useUserStore()
const appStore = useAppStore()
const route = useRoute()

// 根据 Element Plus 需要的 locale 配置
const elementLocale = computed(() => {
  return appStore.language === 'zh-cn' ? zhCn : en
})

const showFloatingAgent = computed(() => {
  if (!userStore.isAuthenticated) return false
  if (route.path === '/login' || route.path === '/register' || route.path === '/agent') return false
  return true
})

onMounted(() => {
  userStore.initAuth()
})
</script>

<style>
#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 
    'Hiragino Sans GB', 'Microsoft YaHei', 'Helvetica Neue', Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  height: 100vh;
  width: 100vw;
}
</style>
