<template>
  <!-- 登录页：不显示后台布局 -->
  <router-view v-if="hideLayout" />

  <!-- 后台页：显示完整布局 -->
  <el-container v-else style="height: 100vh;">
    <el-aside width="220px" class="aside">
      <div class="logo">CLUE 图像安全审核系统</div>

      <el-menu
        router
        :default-active="$route.path"
        class="menu"
      >
        <el-menu-item index="/">
          <span>仪表盘</span>
        </el-menu-item>

        <el-menu-item index="/tasks">
          <span>审核任务</span>
        </el-menu-item>

        <el-menu-item index="/rules">
          <span>规则管理</span>
        </el-menu-item>

        <el-menu-item index="/settings">
          <span>系统设置</span>
        </el-menu-item>

        <el-menu-item index="/users">
          <span>用户管理</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-left">
          <span class="sys-title">CLUE 图像安全自动化审核系统</span>
        </div>

        <div class="header-right">
          <el-tag type="info" style="margin-right: 10px;">
            {{ roleLabel }}
          </el-tag>
          <span style="margin-right: 12px;">{{ username }}</span>
          <el-button size="small" @click="logout">退出登录</el-button>
        </div>
      </el-header>

      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const hideLayout = computed(() => route.meta?.hideLayout === true)

const username = computed(() => localStorage.getItem('username') || '未登录用户')

const roleLabel = computed(() => {
  const role = localStorage.getItem('role')
  if (role === 'admin') return '管理员'
  if (role === 'operator') return '审核员'
  return '未知角色'
})

const logout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('username')
  localStorage.removeItem('role')
  window.location.href = '/login'
}
</script>

<style scoped>
.aside {
  background: #ffffff;
  border-right: 1px solid #ebeef5;
}

.logo {
  height: 64px;
  line-height: 64px;
  text-align: center;
  font-weight: 700;
  color: #2c3e50;
  border-bottom: 1px solid #ebeef5;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  padding: 0 12px;
}

.menu {
  border-right: none;
}

.header {
  background: #409eff;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sys-title {
  font-size: 20px;
  font-weight: 700;
}

.header-right {
  display: flex;
  align-items: center;
}

.main {
  background: #f5f7fa;
}
</style>