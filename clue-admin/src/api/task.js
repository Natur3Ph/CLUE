import request from './request'

// 获取台账任务
export function fetchAuditTasks(limit = 10) {
  return request.get('/api/audit-tasks', { params: { limit } })
}

// 创建单个审核任务
export function createAuditTask(formData) {
  return request.post('/api/moderate', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// 批量创建审核任务
export function createBatchAuditTasks(formData) {
  return request.post('/api/moderate/batch', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 3600000,
  })
}

// 删除审核任务
export function deleteAuditTask(taskId) {
  return request.delete(`/api/audit-tasks/${taskId}`)
}