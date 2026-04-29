import re

file_path = '/Users/chenjigang/Desktop/testhub_platform/frontend/src/views/configuration/KnowledgeBaseConfig.vue'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace HTML template for Vision
vision_template_start = content.find('<!-- Vision 模型配置 -->')
vision_template_end = content.find('<div class="form-actions">')

if vision_template_start != -1 and vision_template_end != -1:
    new_template = """<!-- Tika Server 配置 -->
          <div class="section-title">
            <el-icon><Document /></el-icon>
            {{ $t('configuration.knowledgeBase.tikaTitle', '文档解析服务 (Tika Server)') }}
          </div>
          <el-alert
            :title="$t('configuration.knowledgeBase.tikaHint', '用于解析 PDF、Word 等文档内容，提取纯文本供向量化使用。')"
            type="info"
            :closable="false"
            show-icon
            style="margin-bottom: 20px;"
          />
          <el-form-item :label="$t('configuration.knowledgeBase.tikaServerUrl', 'Tika 服务地址')" prop="tika_server_url">
            <el-input v-model="form.tika_server_url" placeholder="如: http://localhost:9987" clearable>
              <template #prepend><el-icon><Link /></el-icon></template>
            </el-input>
          </el-form-item>

          """
    content = content[:vision_template_start] + new_template + content[vision_template_end:]

# Replace state descriptions
desc_start = content.find('<el-descriptions-item label="Vision API Key">')
desc_end = content.find('</el-descriptions-item>', desc_start) + len('</el-descriptions-item>')

if desc_start != -1:
    new_desc = """<el-descriptions-item label="Tika Server URL">{{ currentConfig.tika_server_url || '未配置' }}</el-descriptions-item>"""
    content = content[:desc_start] + new_desc + content[desc_end:]

# Replace form state
content = content.replace("vision_api_key: '',\n  vision_base_url: '',\n  vision_model: 'glm-4v-flash',\n  vision_provider: 'zhipu'", "tika_server_url: 'http://localhost:9987'")
content = content.replace("vision_api_key: response.data.vision_api_key_masked ? '****' : '',\n        vision_base_url: response.data.vision_base_url || '',\n        vision_model: response.data.vision_model || 'glm-4v-flash',\n        vision_provider: response.data.vision_provider || 'zhipu'", "tika_server_url: response.data.tika_server_url || 'http://localhost:9987'")

# Remove computed properties for vision
content = re.sub(r'const visionBaseUrlPlaceholder = computed\(\(\) => \{.*?\n\}\)\n', '', content, flags=re.DOTALL)
content = re.sub(r'const visionModelPlaceholder = computed\(\(\) => \{.*?\n\}\)\n', '', content, flags=re.DOTALL)
content = re.sub(r'const handleProviderChange = \(provider\) => \{.*?\n\}\n', '', content, flags=re.DOTALL)

# Modify saveConfig
content = content.replace("if (payload.vision_api_key === '****') delete payload.vision_api_key", "")

# Update icons import
content = content.replace("Picture", "Document")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Vue template updated.")