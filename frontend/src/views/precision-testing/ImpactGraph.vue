<template>
  <div class="impact-graph">
    <!-- 顶部查询栏 -->
    <div class="graph-toolbar">
      <el-input
        v-model="queryFunc"
        placeholder="输入函数名（如：module.function_name）"
        style="width: 340px"
        clearable
        @keyup.enter="loadGraph"
      >
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-select v-model="queryDepth" style="width: 110px; margin-left: 8px">
        <el-option label="1 层" :value="1" />
        <el-option label="2 层" :value="2" />
        <el-option label="3 层" :value="3" />
      </el-select>
      <el-button type="primary" :loading="graphLoading" style="margin-left: 8px" @click="loadGraph">
        <el-icon><Share /></el-icon> 查询影响
      </el-button>
      <el-button @click="resetGraph"><el-icon><Refresh /></el-icon> 重置</el-button>

      <!-- 图例 -->
      <div class="legend">
        <span v-for="n in nodeTypes" :key="n.type" class="legend-item">
          <i class="legend-dot" :style="{ background: n.color }"></i>{{ n.label }}
        </span>
      </div>
    </div>

    <div class="graph-main">
      <!-- Cytoscape 画布 -->
      <div ref="cyContainer" class="cy-container" v-loading="graphLoading">
        <div v-if="!hasData && !graphLoading" class="cy-empty">
          <el-empty description="输入函数名后点击「查询影响」加载图谱" />
        </div>
      </div>

      <!-- 右侧属性面板 -->
      <div class="props-panel" v-if="selectedNode">
        <div class="props-header">
          <span>节点属性</span>
          <el-icon class="close-btn" @click="selectedNode = null"><Close /></el-icon>
        </div>
        <el-tag :style="{ background: nodeColor(selectedNode.type), color: '#fff', border: 'none' }" size="small">
          {{ selectedNode.type }}
        </el-tag>
        <el-descriptions :column="1" border size="small" style="margin-top: 10px">
          <el-descriptions-item label="ID">{{ selectedNode.id }}</el-descriptions-item>
          <el-descriptions-item label="名称">{{ selectedNode.name }}</el-descriptions-item>
          <el-descriptions-item v-if="selectedNode.module" label="模块">{{ selectedNode.module }}</el-descriptions-item>
          <el-descriptions-item v-if="selectedNode.file_path" label="文件">{{ selectedNode.file_path }}</el-descriptions-item>
          <el-descriptions-item v-if="selectedNode.risk_score != null" label="风险分">
            <el-progress :percentage="Math.round(selectedNode.risk_score * 100)" :color="riskColor(selectedNode.risk_score)" />
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Share, Refresh, Close } from '@element-plus/icons-vue'
import { getGraphData, queryImpact } from '@/api/precision-testing'

const cyContainer = ref(null)
const graphLoading = ref(false)
const hasData = ref(false)
const queryFunc = ref('')
const queryDepth = ref(2)
const selectedNode = ref(null)
let cy = null

const nodeTypes = [
  { type: 'Function', label: '函数', color: '#5470c6' },
  { type: 'TestCase', label: '测试用例', color: '#91cc75' },
  { type: 'APIEndpoint', label: 'API 端点', color: '#fac858' },
  { type: 'Class', label: '类', color: '#ee6666' },
  { type: 'Module', label: '模块', color: '#73c0de' },
]
const nodeColor = (type) => nodeTypes.find(n => n.type === type)?.color || '#aaa'
const riskColor = (score) => score > 0.7 ? '#f56c6c' : score > 0.4 ? '#e6a23c' : '#67c23a'

const buildCyElements = (nodes, edges) => {
  const elements = []
  nodes.forEach(n => {
    // 兼容后端直接返回的 Cytoscape element 格式（含 data 属性）
    if (n.data) {
      elements.push(n)
      return
    }
    // 兼容旧版扁平格式
    elements.push({
      data: {
        id: String(n.id ?? n.neo4j_id),
        label: n.name || n.id,
        type: n.labels?.[0] || n.type || 'Function',
        ...n.properties,
        ...n,
      },
    })
  })
  edges.forEach((e, idx) => {
    if (e.data) {
      elements.push(e)
      return
    }
    elements.push({
      data: {
        id: `e-${e.source}-${e.target}-${e.type}-${idx}`,
        source: String(e.source),
        target: String(e.target),
        label: e.type || e.relationship,
      },
    })
  })
  return elements
}

const initCy = async (elements) => {
  if (!cyContainer.value) return
  // 动态加载 cytoscape（避免 SSR 问题）
  const cytoscape = (await import('cytoscape')).default

  if (cy) { cy.destroy(); cy = null }

  cy = cytoscape({
    container: cyContainer.value,
    elements,
    style: [
      {
        selector: 'node',
        style: {
          label: 'data(label)',
          'font-size': '11px',
          'text-valign': 'bottom',
          'text-halign': 'center',
          'background-color': (ele) => nodeColor(ele.data('node_type') || ele.data('type')),
          width: 36,
          height: 36,
          color: '#333',
          'text-max-width': '100px',
          'text-wrap': 'ellipsis',
        },
      },
      {
        selector: 'edge',
        style: {
          label: 'data(label)',
          'font-size': '10px',
          'line-color': '#ccc',
          'target-arrow-color': '#ccc',
          'target-arrow-shape': 'triangle',
          'curve-style': 'bezier',
          width: 1.5,
          color: '#888',
        },
      },
      {
        selector: 'node[is_changed]',
        style: {
          'border-width': 3,
          'border-color': '#f56c6c',
          'background-color': '#ee6666',
        },
      },
      {
        selector: 'node:selected',
        style: {
          'border-width': 3,
          'border-color': '#409eff',
        },
      },
    ],
    layout: { name: 'cose', animate: true, randomize: false, nodeRepulsion: 8000, idealEdgeLength: 80 },
  })

  cy.on('tap', 'node', (evt) => {
    const data = evt.target.data()
    selectedNode.value = {
      id: data.node_id || data.id,
      name: data.name || data.label,
      type: data.node_type || data.type || 'Function',
      module: data.module,
      file_path: data.file_path,
      risk_score: data.risk_score,
    }
  })
  cy.on('tap', (evt) => {
    if (evt.target === cy) selectedNode.value = null
  })
}

const loadGraph = async () => {
  if (!queryFunc.value.trim()) {
    // 无查询条件时加载全量图谱
    graphLoading.value = true
    try {
      const res = await getGraphData()
      const { nodes, edges } = res.data
      if (!nodes?.length) { ElMessage.info('图谱暂无数据'); return }
      hasData.value = true
      await nextTick()
      await initCy(buildCyElements(nodes, edges))
    } catch {
      ElMessage.error('加载图谱失败')
    } finally {
      graphLoading.value = false
    }
    return
  }

  graphLoading.value = true
  try {
    const res = await queryImpact({ changed_functions: [queryFunc.value.trim()], depth: queryDepth.value })
    const { nodes, edges } = res.data
    if (!nodes?.length) { ElMessage.warning('未找到影响节点'); return }
    hasData.value = true
    await nextTick()
    await initCy(buildCyElements(nodes, edges))
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '查询失败')
  } finally {
    graphLoading.value = false
  }
}

const resetGraph = () => {
  queryFunc.value = ''
  queryDepth.value = 2
  selectedNode.value = null
  hasData.value = false
  if (cy) { cy.destroy(); cy = null }
}

onMounted(() => {
  // 初始加载全量图谱（小规模）
  loadGraph()
})
onBeforeUnmount(() => { if (cy) cy.destroy() })
</script>

<style scoped>
.impact-graph { display: flex; flex-direction: column; height: calc(100vh - 120px); padding: 16px; box-sizing: border-box; }
.graph-toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
  padding: 12px 16px;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
}
.legend { display: flex; gap: 12px; margin-left: auto; flex-wrap: wrap; }
.legend-item { display: flex; align-items: center; gap: 4px; font-size: 12px; color: var(--el-text-color-secondary); }
.legend-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; }

.graph-main { flex: 1; display: flex; gap: 12px; min-height: 0; }
.cy-container {
  flex: 1;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  background: var(--el-bg-color);
  position: relative;
  min-height: 400px;
}
.cy-empty { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; }

.props-panel {
  width: 260px;
  flex-shrink: 0;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  background: var(--el-bg-color);
  padding: 14px;
  overflow-y: auto;
}
.props-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 10px;
  color: var(--el-text-color-primary);
}
.close-btn { cursor: pointer; color: var(--el-text-color-secondary); }
.close-btn:hover { color: var(--el-color-primary); }
</style>
