// src/api/settings.js
import request from './request'

// 读取系统设置
export function fetchSettings() {
  return request.get('/api/settings')
}

// 保存系统设置
export function saveSettings(payload) {
  return request.put('/api/settings', payload)
}