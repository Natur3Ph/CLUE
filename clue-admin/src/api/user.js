import request from './request'

// 登录
export function login(data) {
  return request.post('/api/users/login', data)
}

// 获取用户列表
export function fetchUsers() {
  return request.get('/api/users')
}

// 创建用户
export function createUser(data) {
  return request.post('/api/users', data)
}