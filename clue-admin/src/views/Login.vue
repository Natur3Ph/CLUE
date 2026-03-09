<template>
  <div class="login-container">
    <el-card class="login-box">
      <h2 class="title">CLUE 图像安全审核系统</h2>

      <el-form :model="form">
        <el-form-item>
          <el-input v-model="form.username" placeholder="用户名"/>
        </el-form-item>

        <el-form-item>
          <el-input v-model="form.password" type="password" placeholder="密码"/>
        </el-form-item>

        <el-button type="primary" style="width:100%" @click="handleLogin">
          登录
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive } from 'vue'
import { login } from '../api/user'
import { ElMessage } from 'element-plus'
import router from '../router'

const form = reactive({
  username: '',
  password: ''
})

const handleLogin = async () => {
  const res = await login(form)

  localStorage.setItem('token', res.data.token)
  localStorage.setItem('username', res.data.username)
  localStorage.setItem('role', res.data.role)

  ElMessage.success('登录成功')

  router.push('/')
}
</script>

<style scoped>

.login-container{
  height:100vh;
  display:flex;
  justify-content:center;
  align-items:center;
  background:#2c3e50;
}

.login-box{
  width:360px;
}

.title{
  text-align:center;
  margin-bottom:20px;
}

</style>