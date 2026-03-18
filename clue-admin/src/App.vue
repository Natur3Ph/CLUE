<template>
  <!-- 登录页：不显示后台布局 -->
  <router-view v-if="hideLayout" />

  <!-- 后台页：显示完整布局 -->
  <el-container v-else class="app-shell">
    <!-- 左侧导航 -->
    <el-aside width="220px" class="aside">
      <div class="logo-wrap">
        <div class="logo-mark">IAS</div>
        <div class="logo-text">
          <div class="logo-title">图像安全审核系统</div>
          <div class="logo-subtitle">Image Safety Audit Platform</div>
        </div>
      </div>

      <el-scrollbar class="aside-scroll">
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

          <el-menu-item index="/benchmark">
            <span>Benchmark测试</span>
          </el-menu-item>

          <el-menu-item index="/settings">
            <span>系统设置</span>
          </el-menu-item>

          <el-menu-item index="/users">
            <span>用户管理</span>
          </el-menu-item>
        </el-menu>
      </el-scrollbar>
    </el-aside>

    <!-- 右侧主区域 -->
    <el-container class="main-shell">
      <el-header class="header">
        <div class="header-left">
          <div class="page-title">图像安全自动化审核系统</div>
          <div class="page-subtitle">Enterprise Image Safety Audit Platform</div>
        </div>

        <div class="header-right">
          <div class="user-box">
            <el-avatar class="user-avatar" :size="34">
              {{ userInitial }}
            </el-avatar>

            <div class="user-meta">
              <div class="user-name">{{ username }}</div>
              <div class="user-role">{{ roleLabel }}</div>
            </div>
          </div>

          <el-button size="small" class="logout-btn" @click="logout">
            退出登录
          </el-button>
        </div>
      </el-header>

      <el-main class="main">
        <div class="content-wrap">
          <router-view />
        </div>
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

const userInitial = computed(() => {
  const name = username.value || 'U'
  return String(name).charAt(0).toUpperCase()
})

const logout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('username')
  localStorage.removeItem('role')
  window.location.href = '/login'
}
</script>

<style scoped>
.app-shell {
  height: 100vh;
  background: #f5f7fa;
}

.aside {
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-right: 1px solid #ebeef5;
  box-shadow: 0 0 20px rgba(0, 0, 0, 0.03);
}

.logo-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 72px;
  padding: 0 18px;
  border-bottom: 1px solid #eef1f6;
  box-sizing: border-box;
}

.logo-mark {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.logo-text {
  min-width: 0;
}

.logo-title {
  font-size: 16px;
  font-weight: 700;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.logo-subtitle {
  margin-top: 2px;
  font-size: 12px;
  color: #909399;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.aside-scroll {
  flex: 1;
}

.menu {
  border-right: none;
  padding: 14px 10px;
}

.menu :deep(.el-menu-item) {
  height: 46px;
  line-height: 46px;
  margin-bottom: 8px;
  border-radius: 10px;
  color: #303133;
  font-size: 15px;
  transition: all 0.2s ease;
}

.menu :deep(.el-menu-item:hover) {
  background: #ecf5ff;
  color: #409eff;
}

.menu :deep(.el-menu-item.is-active) {
  background: linear-gradient(90deg, rgba(64, 158, 255, 0.12), rgba(64, 158, 255, 0.04));
  color: #409eff;
  font-weight: 600;
}

.main-shell {
  min-width: 0;
}

.header {
  height: 72px;
  background: #409eff;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 22px;
  box-sizing: border-box;
  box-shadow: 0 2px 10px rgba(64, 158, 255, 0.16);
}

.header-left {
  min-width: 0;
}

.page-title {
  font-size: 18px;
  font-weight: 700;
  line-height: 1.2;
}

.page-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.88);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-shrink: 0;
}

.user-box {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 10px 6px 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.14);
}

.user-avatar {
  background: #ffffff;
  color: #409eff;
  font-weight: 700;
}

.user-meta {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.user-name {
  font-size: 14px;
  font-weight: 700;
  color: #fff;
}

.user-role {
  margin-top: 3px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.86);
}

.logout-btn {
  border: none;
}

.main {
  background: #f5f7fa;
  padding: 0;
}

.content-wrap {
  height: 100%;
  box-sizing: border-box;
}

/* 移动端兼容 */
@media (max-width: 768px) {
  .logo-subtitle,
  .page-subtitle,
  .user-role {
    display: none;
  }

  .header {
    padding: 0 14px;
  }

  .page-title {
    font-size: 16px;
  }

  .user-box {
    padding-right: 8px;
  }
}
</style>