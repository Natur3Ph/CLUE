<template>
  <el-container style="height:100vh">
    <el-aside width="200px">
      <el-menu router>
        <el-menu-item index="/dashboard">仪表盘</el-menu-item>
        <el-menu-item index="/tasks">审核任务</el-menu-item>
        <el-menu-item index="/rules">规则管理</el-menu-item>
        <el-menu-item index="/settings">系统设置</el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header style="background:#409EFF;color:white;">
        CLUE 图像安全审核系统
      </el-header>

      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>