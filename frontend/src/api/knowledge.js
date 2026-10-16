import { http } from './http'

export async function listKnowledge() {
  const { data } = await http.get('/knowledge')
  return data
}

export async function getKnowledge(documentId) {
  const { data } = await http.get(`/knowledge/${documentId}`)
  return data
}

export async function createKnowledge(payload) {
  const { data } = await http.post('/knowledge', payload)
  return data
}

export async function uploadKnowledgeFile({ file, source, title, onUploadProgress }) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('source', source || 'upload')
  if (title) {
    formData.append('title', title)
  }

  const { data } = await http.post('/knowledge/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    timeout: 120000,
    onUploadProgress,
  })
  return data
}

export async function downloadKnowledgeFile(documentId) {
  const response = await http.get(`/knowledge/${documentId}/download`, {
    responseType: 'blob',
  })
  return response.data
}

export async function deleteKnowledge(documentId) {
  const { data } = await http.delete(`/knowledge/${documentId}`)
  return data
}
