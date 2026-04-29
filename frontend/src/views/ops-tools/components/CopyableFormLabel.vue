<template>
  <span class="copyable-label" @click.stop="handleCopy">
    <span>{{ label }}</span>
    <el-icon><DocumentCopy /></el-icon>
  </span>
</template>

<script setup>
import { DocumentCopy } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";

const props = defineProps({
  label: {
    type: String,
    required: true,
  },
  value: {
    type: [String, Number],
    default: "",
  },
});

async function handleCopy() {
  const text = props.value == null ? "" : String(props.value);
  if (!text) {
    ElMessage.warning(`${props.label} 为空，无法复制`);
    return;
  }
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
  } else {
    const input = document.createElement("textarea");
    input.value = text;
    document.body.appendChild(input);
    input.select();
    document.execCommand("copy");
    document.body.removeChild(input);
  }
  ElMessage.success(`${props.label} 已复制`);
}
</script>

<style scoped>
.copyable-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  color: var(--el-color-primary);
  user-select: none;
}
</style>
