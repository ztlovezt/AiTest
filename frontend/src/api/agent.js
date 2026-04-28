import api from '@/utils/api'

export const agentApi = {
  getStatus() {
    return api.get('/agent/status/')
  },
  listSessions() {
    return api.get('/agent/sessions/')
  },
  getMessages(sessionPk) {
    return api.get(`/agent/sessions/${sessionPk}/messages/`)
  },
  deleteSession(sessionPk) {
    return api.delete(`/agent/sessions/${sessionPk}/`)
  },
  sendMessage(payload) {
    return api.post('/agent/chat/send_message/', payload, { timeout: 65000 })
  },
  syncBuiltinDocs() {
    return api.post('/agent/chat/sync_builtin_docs/')
  },
    listConfigs() {
        return api.get('/agent/configs/')
    },
    createConfig(payload) {
        return api.post('/agent/configs/', payload)
    },
    updateConfig(id, payload) {
        return api.patch(`/agent/configs/${id}/`, payload)
    },
    deleteConfig(id) {
        return api.delete(`/agent/configs/${id}/`)
    },
    testConfigConnection(id) {
        return api.post(`/agent/configs/${id}/test_connection/`, {}, {timeout: 90000})
    },
    testConfigConnectionPreview(payload) {
        return api.post('/agent/configs/test_connection/', payload, {timeout: 90000})
    },
}
