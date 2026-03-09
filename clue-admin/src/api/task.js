// src/api/task.js
import request from './request'

// 获取台账任务
export function fetchAuditTasks(limit = 10) {
  return request.get('/api/audit-tasks', { params: { limit } })
}

// 创建审核任务（上传图片 + rules）
export function createAuditTask(formData) {
  return request.post('/api/moderate', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// 获取单个任务详情（如果你后端做了 /api/audit-tasks/{task_id} 再补）
// export function fetchAuditTaskDetail(taskId) {
//   return request.get(`/api/audit-tasks/${taskId}`)
// }