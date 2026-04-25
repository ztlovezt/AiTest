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
}
