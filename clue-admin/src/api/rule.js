// src/api/rule.js
import request from './request'

// all=true 返回全部规则；all=false 仅启用
export function fetchRules(all = true) {
  return request.get('/api/rules', { params: { all } })
}

export function createRule(payload) {
  return request.post('/api/rules', payload)
}

// ✅ 更新规则：你现在后端如果是 PUT，就用 PUT
// 如果你后端实际是 PATCH，把 request.put 改成 request.patch
export function updateRule(id, payload) {
  return request.put(`/api/rules/${id}`, payload)
}

export function deleteRule(id) {
  return request.delete(`/api/rules/${id}`)
}

// ✅ 新增：一键客观化 / 生成预条件链
export function objectifyRule(id) {
  return request.post(`/api/rules/${id}/objectify`)
}