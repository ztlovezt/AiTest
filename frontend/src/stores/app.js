import { defineStore } from 'pinia'
import { ref } from 'vue'
import i18n from '@/locales'

// 主题配色方案定义
const COLOR_THEMES = {
  indigo: {
    key: 'indigo',
    light: {
      '--th-color-primary': '#5b5bd6',
      '--th-color-primary-strong': '#4747c2',
      '--th-color-primary-soft': '#eef0ff',
      '--th-sidebar-text-active': '#5b5bd6',
      '--th-sidebar-item-bg-hover': 'rgba(91, 91, 214, 0.08)',
      '--th-sidebar-item-bg-active': 'rgba(91, 91, 214, 0.16)',
    },
    dark: {
      '--th-color-primary': '#7c7ce0',
      '--th-color-primary-strong': '#5b5bd6',
      '--th-color-primary-soft': 'rgba(124, 124, 224, 0.15)',
      '--th-sidebar-text-active': '#9b9be8',
      '--th-sidebar-item-bg-hover': 'rgba(124, 124, 224, 0.12)',
      '--th-sidebar-item-bg-active': 'rgba(124, 124, 224, 0.22)',
    }
  },
  'semi-orange': {
    key: 'semi-orange',
    light: {
      '--th-color-primary': '#F5722B',
      '--th-color-primary-strong': '#D4580D',
      '--th-color-primary-soft': '#FFF3EB',
      '--th-sidebar-text-active': '#F5722B',
      '--th-sidebar-item-bg-hover': 'rgba(245, 114, 43, 0.08)',
      '--th-sidebar-item-bg-active': 'rgba(245, 114, 43, 0.16)',
    },
    dark: {
      '--th-color-primary': '#E8793A',
      '--th-color-primary-strong': '#F5722B',
      '--th-color-primary-soft': 'rgba(232, 121, 58, 0.15)',
      '--th-sidebar-text-active': '#F0A070',
      '--th-sidebar-item-bg-hover': 'rgba(232, 121, 58, 0.12)',
      '--th-sidebar-item-bg-active': 'rgba(232, 121, 58, 0.22)',
    }
  }
}

export const useAppStore = defineStore('app', () => {
  // 状态：当前语言
  const language = ref(localStorage.getItem('app-lang') || 'zh-cn')
  const theme = ref(localStorage.getItem('app-theme') || 'hoppscotch-light')
  const colorTheme = ref(localStorage.getItem('app-color-theme') || 'indigo')

  const applyTheme = (value) => {
    if (typeof document === 'undefined') return
    document.documentElement.setAttribute('data-theme', value)
    // 切换明暗模式后重新应用配色
    applyColorTheme(colorTheme.value)
  }

  const applyColorTheme = (themeKey) => {
    if (typeof document === 'undefined') return
    const themeConfig = COLOR_THEMES[themeKey]
    if (!themeConfig) return
    const isDark = theme.value === 'hoppscotch-dark'
    const colors = isDark ? themeConfig.dark : themeConfig.light
    const root = document.documentElement
    Object.entries(colors).forEach(([prop, value]) => {
      root.style.setProperty(prop, value)
    })
    root.setAttribute('data-color-theme', themeKey)
  }

  // 动作：切换语言
  const setLanguage = (lang) => {
    language.value = lang
    // 1. 修改 i18n 实例语言
    i18n.global.locale.value = lang
    // 2. 持久化
    localStorage.setItem('app-lang', lang)
    // 3. 设置 HTML 标签 lang 属性，利于 SEO 和浏览器识别
    document.querySelector('html')?.setAttribute('lang', lang)
  }

  const setTheme = (value) => {
    theme.value = value
    localStorage.setItem('app-theme', value)
    applyTheme(value)
  }

  const setColorTheme = (themeKey) => {
    colorTheme.value = themeKey
    localStorage.setItem('app-color-theme', themeKey)
    applyColorTheme(themeKey)
  }

  applyTheme(theme.value)

  return { language, theme, colorTheme, setLanguage, setTheme, setColorTheme, COLOR_THEMES }
})
