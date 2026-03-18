<template>
  <div class="user-page">
    <!-- 顶部说明区 -->
    <div class="page-banner">
      <div>
        <div class="page-title">用户管理</div>
        <div class="page-desc">
          统一维护系统用户账号，支持用户查看、新建与删除，便于实现基础权限管理。
        </div>
      </div>

      <div class="page-actions">
        <el-button @click="loadUsers" :loading="loading">刷新数据</el-button>
        <el-button type="primary" @click="openCreateDialog">新建用户</el-button>
      </div>
    </div>

    <!-- 顶部统计 -->
    <el-row :gutter="16" class="section-row">
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card class="stat-card stat-total" shadow="hover">
          <div class="stat-label">用户总数</div>
          <div class="stat-value">{{ stats.total }}</div>
          <div class="stat-sub">系统当前已创建账号数</div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :lg="6">
        <el-card class="stat-card stat-admin" shadow="hover">
          <div class="stat-label">管理员</div>
          <div class="stat-value">{{ stats.admin }}</div>
          <div class="stat-sub">具备系统管理权限</div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :lg="6">
        <el-card class="stat-card stat-operator" shadow="hover">
          <div class="stat-label">审核员</div>
          <div class="stat-value">{{ stats.operator }}</div>
          <div class="stat-sub">主要用于审核任务操作</div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :lg="6">
        <el-card class="stat-card stat-active" shadow="hover">
          <div class="stat-label">启用账号</div>
          <div class="stat-value">{{ stats.active }}</div>
          <div class="stat-sub">当前可正常登录使用</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 用户列表 -->
    <el-card class="table-card" shadow="never">
      <template #header>
        <div class="table-header">
          <div>
            <div class="card-title">用户列表</div>
            <div class="card-subtitle">支持查看账号信息，并对非默认账号执行删除操作</div>
          </div>
          <div class="table-summary">当前显示 {{ users.length }} 个用户</div>
        </div>
      </template>

      <el-table
        :data="users"
        v-loading="loading"
        border
        class="user-table"
        style="width: 100%"
      >
        <el-table-column prop="username" label="用户名" min-width="180">
          <template #default="{ row }">
            <div class="user-cell">
              <el-avatar :size="32" class="user-avatar">
                {{ getInitial(row.username) }}
              </el-avatar>
              <span class="user-name">{{ row.username }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="角色" width="120">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'danger' : 'primary'" effect="light">
              {{ roleText(row.role) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="账号状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" effect="light">
              {{ row.is_active ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="创建时间" min-width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button
              link
              type="danger"
              @click="handleDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty
        v-if="!loading && users.length === 0"
        description="暂无用户数据"
        class="empty-block"
      />
    </el-card>

    <!-- 新建用户弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      title="新建用户"
      width="520px"
      destroy-on-close
    >
      <el-form :model="form" label-width="90px">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </el-form-item>

        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            placeholder="请输入登录密码"
          />
        </el-form-item>

        <el-form-item label="角色">
          <el-select v-model="form.role" placeholder="请选择角色" style="width: 100%">
            <el-option label="管理员" value="admin" />
            <el-option label="审核员" value="operator" />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleCreate">
          创建用户
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchUsers, createUser, deleteUser } from '../api/user'

const loading = ref(false)
const submitLoading = ref(false)

const users = ref([])
const dialogVisible = ref(false)

const form = ref({
  username: '',
  password: '',
  role: 'operator',
})

const stats = computed(() => {
  const list = users.value || []
  return {
    total: list.length,
    admin: list.filter((u) => u.role === 'admin').length,
    operator: list.filter((u) => u.role === 'operator').length,
    active: list.filter((u) => !!u.is_active).length,
  }
})

function unwrap(res) {
  if (!res) return null
  if (res.status && res.data !== undefined) return res.data
  if (res.data && res.data.data !== undefined) return res.data.data
  if (res.data !== undefined) return res.data
  return res
}

function roleText(role) {
  if (role === 'admin') return '管理员'
  if (role === 'operator') return '审核员'
  return role || '未知角色'
}

function formatDateTime(value) {
  if (!value) return '-'
  return String(value).replace('T', ' ').slice(0, 19)
}

function getInitial(username) {
  return String(username || 'U').charAt(0).toUpperCase()
}

function resetForm() {
  form.value = {
    username: '',
    password: '',
    role: 'operator',
  }
}

function openCreateDialog() {
  resetForm()
  dialogVisible.value = true
}

async function loadUsers() {
  loading.value = true
  try {
    const res = await fetchUsers()
    users.value = unwrap(res) || []
  } catch (err) {
    console.error(err)
    ElMessage.error(err?.response?.data?.detail || '获取用户列表失败')
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  if (!String(form.value.username || '').trim()) {
    ElMessage.warning('用户名不能为空')
    return
  }
  if (!String(form.value.password || '').trim()) {
    ElMessage.warning('密码不能为空')
    return
  }

  submitLoading.value = true
  try {
    await createUser({
      username: String(form.value.username || '').trim(),
      password: String(form.value.password || '').trim(),
      role: form.value.role || 'operator',
    })

    ElMessage.success('用户创建成功')
    dialogVisible.value = false
    await loadUsers()
  } catch (err) {
    console.error(err)
    ElMessage.error(err?.response?.data?.detail || '创建用户失败')
  } finally {
    submitLoading.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除用户【${row.username}】吗？`,
      '删除确认',
      {
        type: 'warning',
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
      }
    )
  } catch {
    return
  }

  try {
    await deleteUser(row.id)
    ElMessage.success('删除成功')
    await loadUsers()
  } catch (err) {
    console.error(err)
    ElMessage.error(err?.response?.data?.detail || '删除失败')
  }
}

onMounted(() => {
  loadUsers()
})
</script>

<style scoped>
.user-page {
  padding: 20px;
  background: #f5f7fa;
  min-height: 100%;
  box-sizing: border-box;
}

.page-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
  padding: 22px 24px;
  border-radius: 16px;
  background: #ffffff;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: #303133;
}

.page-desc {
  margin-top: 8px;
  font-size: 14px;
  color: #606266;
}

.page-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.section-row {
  margin-bottom: 16px;
}

.stat-card {
  border: none;
  border-radius: 14px;
}

.stat-card :deep(.el-card__body) {
  padding: 22px 22px 18px;
}

.stat-label {
  font-size: 14px;
  color: #606266;
}

.stat-value {
  margin-top: 12px;
  font-size: 34px;
  font-weight: 700;
  color: #303133;
  line-height: 1;
}

.stat-sub {
  margin-top: 14px;
  font-size: 12px;
  color: #909399;
}

.stat-total {
  border-left: 4px solid #409eff;
}

.stat-admin {
  border-left: 4px solid #f56c6c;
}

.stat-operator {
  border-left: 4px solid #67c23a;
}

.stat-active {
  border-left: 4px solid #9c6bff;
}

.table-card {
  border: none;
  border-radius: 14px;
}

.table-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.card-title {
  font-size: 16px;
  font-weight: 700;
  color: #303133;
}

.card-subtitle {
  margin-top: 4px;
  font-size: 13px;
  color: #909399;
}

.table-summary {
  font-size: 13px;
  color: #909399;
}

.user-table :deep(th.el-table__cell) {
  background: #f8fafc;
  color: #606266;
  font-weight: 600;
}

.user-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-avatar {
  background: #ecf5ff;
  color: #409eff;
  font-weight: 700;
}

.user-name {
  color: #303133;
  font-weight: 500;
}

.empty-block {
  margin-top: 20px;
}

@media (max-width: 992px) {
  .page-banner,
  .table-header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>