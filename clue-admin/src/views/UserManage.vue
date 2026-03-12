<template>
  <div style="padding: 16px;">
    <el-card shadow="hover">
      <template #header>
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span style="font-weight:700;">用户管理</span>
          <div>
            <el-button @click="load" :loading="loading">刷新</el-button>
            <el-button type="primary" @click="openCreate">新增用户</el-button>
          </div>
        </div>
      </template>

      <el-table :data="users" v-loading="loading" style="width:100%;" border stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="用户名" min-width="160" />
        <el-table-column prop="role" label="角色" width="120">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'danger' : 'success'">
              {{ row.role === 'admin' ? '管理员' : '审核员' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="is_active" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="created_at" label="创建时间" min-width="200" />

        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button
              type="danger"
              size="small"
              @click.stop="handleDelete(row)"
              :disabled="row.username === 'admin'"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty
        v-if="!loading && users.length === 0"
        description="暂无用户数据"
        style="margin-top:20px;"
      />
    </el-card>

    <el-dialog v-model="dialogVisible" title="新增用户" width="520px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </el-form-item>

        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            show-password
          />
        </el-form-item>

        <el-form-item label="角色">
          <el-select v-model="form.role" style="width:100%">
            <el-option label="管理员" value="admin" />
            <el-option label="审核员" value="operator" />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreate" :loading="saving">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchUsers, createUser, deleteUser } from '../api/user'

const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const users = ref([])

const form = reactive({
  username: '',
  password: '',
  role: 'operator'
})

async function load() {
  loading.value = true
  try {
    const res = await fetchUsers()
    users.value = res?.data || []
  } catch (e) {
    console.error(e)
    ElMessage.error(e?.response?.data?.detail || e?.message || '获取用户列表失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  form.username = ''
  form.password = ''
  form.role = 'operator'
  dialogVisible.value = true
}

async function handleCreate() {
  if (!form.username.trim()) {
    ElMessage.warning('用户名不能为空')
    return
  }
  if (!form.password.trim()) {
    ElMessage.warning('密码不能为空')
    return
  }

  saving.value = true
  try {
    await createUser({
      username: form.username.trim(),
      password: form.password,
      role: form.role
    })
    ElMessage.success('创建成功')
    dialogVisible.value = false
    await load()
  } catch (e) {
    console.error(e)
    ElMessage.error(e?.response?.data?.detail || e?.message || '创建失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除用户【${row.username}】吗？删除后不可恢复。`,
      '删除确认',
      {
        type: 'warning',
        confirmButtonText: '确定删除',
        cancelButtonText: '取消'
      }
    )
  } catch {
    return
  }

  try {
    await deleteUser(row.id)
    ElMessage.success('删除成功')
    await load()
  } catch (e) {
    console.error(e)
    ElMessage.error(e?.response?.data?.detail || e?.message || '删除失败')
  }
}

onMounted(() => {
  load()
})
</script>