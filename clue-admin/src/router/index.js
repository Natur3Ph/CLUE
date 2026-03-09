import { createRouter, createWebHistory } from 'vue-router'

import Login from '../views/Login.vue'
import Dashboard from '../views/Dashboard.vue'
import TaskList from '../views/TaskList.vue'
import RuleManage from '../views/RuleManage.vue'
import Settings from '../views/Settings.vue'
import UserManage from '../views/UserManage.vue'
import CreateTask from '../views/CreateTask.vue'
import TaskDetail from '../views/TaskDetail.vue'

const routes = [
  {
    path: '/login',
    component: Login,
    meta: { hideLayout: true }
  },
  {
    path: '/',
    component: Dashboard
  },
  {
    path: '/tasks',
    component: TaskList
  },
  {
    path: '/tasks/create',
    component: CreateTask
  },
  {
    path: '/tasks/:id',
    component: TaskDetail
  },
  {
    path: '/rules',
    component: RuleManage
  },
  {
    path: '/settings',
    component: Settings
  },
  {
    path: '/users',
    component: UserManage
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')

  if (to.path !== '/login' && !token) {
    next('/login')
  } else if (to.path === '/login' && token) {
    next('/')
  } else {
    next()
  }
})

export default router