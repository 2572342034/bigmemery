<template>
  <div class="auth-page">
    <section class="auth-hero">
      <div>
        <p class="eyebrow">Enterprise AI Workspace</p>
        <h1>BigMemery 智能知识中台</h1>
        <p class="hero-copy">
          面向企业场景的本地大模型工作台，集成会话管理、知识库检索增强、账号体系与流式智能问答。
        </p>
      </div>

      <div class="hero-grid">
        <article>
          <strong>SQLite</strong>
          <span>持久化会话、消息与知识条目元数据。</span>
        </article>
        <article>
          <strong>Chroma + Hybrid RAG</strong>
          <span>向量检索、关键词检索、重排序与引用溯源。</span>
        </article>
        <article>
          <strong>MySQL</strong>
          <span>用户登录、注册与身份鉴权。</span>
        </article>
      </div>
    </section>

    <section class="auth-card">
      <div class="auth-card__head">
        <p class="eyebrow">Access Portal</p>
        <h2>登录你的工作台</h2>
        <span>默认管理员账号已在后端启动时自动初始化。</span>
      </div>

      <el-tabs v-model="activeTab" stretch>
        <el-tab-pane label="登录" name="login">
          <el-form :model="loginForm" label-position="top" @submit.prevent="submitLogin">
            <el-form-item label="用户名">
              <el-input v-model="loginForm.username" placeholder="请输入用户名" />
            </el-form-item>
            <el-form-item label="密码">
              <el-input
                v-model="loginForm.password"
                type="password"
                show-password
                placeholder="请输入密码"
              />
            </el-form-item>
            <el-button type="primary" class="submit-btn" :loading="loading" @click="submitLogin">
              进入工作台
            </el-button>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="注册" name="register">
          <el-form :model="registerForm" label-position="top" @submit.prevent="submitRegister">
            <el-form-item label="用户名">
              <el-input v-model="registerForm.username" placeholder="请输入 3-64 位用户名" />
            </el-form-item>
            <el-form-item label="显示名称">
              <el-input v-model="registerForm.display_name" placeholder="请输入显示名称" />
            </el-form-item>
            <el-form-item label="邮箱">
              <el-input v-model="registerForm.email" placeholder="可选，用于标识用户" />
            </el-form-item>
            <el-form-item label="密码">
              <el-input
                v-model="registerForm.password"
                type="password"
                show-password
                placeholder="至少 6 位密码"
              />
            </el-form-item>
            <el-button type="primary" class="submit-btn" :loading="loading" @click="submitRegister">
              创建账号
            </el-button>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </section>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { login, register } from '../api/auth'

const emit = defineEmits(['authenticated'])

const activeTab = ref('login')
const loading = ref(false)

const loginForm = reactive({
  username: 'admin',
  password: 'Admin@123456',
})

const registerForm = reactive({
  username: '',
  display_name: '',
  email: '',
  password: '',
})

async function submitLogin() {
  loading.value = true
  try {
    const data = await login(loginForm)
    emit('authenticated', data)
    ElMessage.success(`欢迎回来，${data.user.display_name}`)
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || error.message || '登录失败')
  } finally {
    loading.value = false
  }
}

async function submitRegister() {
  loading.value = true
  try {
    const data = await register(registerForm)
    emit('authenticated', data)
    ElMessage.success('账号创建成功，已自动登录')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || error.message || '注册失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
  padding: 28px;
  gap: 28px;
}

.auth-hero,
.auth-card {
  border-radius: 32px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  background: rgba(7, 14, 28, 0.78);
  box-shadow: 0 24px 80px rgba(2, 6, 23, 0.42);
  backdrop-filter: blur(24px);
}

.auth-hero {
  padding: 42px;
  color: #e2e8f0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.eyebrow {
  margin: 0 0 16px;
  color: #38bdf8;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  font-size: 12px;
  font-weight: 700;
}

.auth-hero h1,
.auth-card__head h2 {
  margin: 0;
}

.auth-hero h1 {
  font-size: clamp(40px, 5vw, 68px);
  line-height: 1.04;
}

.hero-copy {
  max-width: 520px;
  margin: 22px 0 0;
  color: #94a3b8;
  font-size: 18px;
  line-height: 1.8;
}

.hero-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.hero-grid article {
  padding: 18px;
  border-radius: 20px;
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.9), rgba(15, 23, 42, 0.64));
  border: 1px solid rgba(56, 189, 248, 0.14);
}

.hero-grid strong {
  display: block;
  margin-bottom: 8px;
  font-size: 18px;
}

.hero-grid span,
.auth-card__head span {
  color: #94a3b8;
  line-height: 1.6;
}

.auth-card {
  padding: 28px;
  color: #e2e8f0;
}

.auth-card__head {
  margin-bottom: 18px;
}

.auth-card__head h2 {
  margin-bottom: 8px;
  font-size: 30px;
}

:deep(.el-tabs__item) {
  color: #94a3b8;
}

:deep(.el-tabs__item.is-active) {
  color: #f8fafc;
}

:deep(.el-form-item__label) {
  color: #cbd5e1;
}

:deep(.el-input__wrapper) {
  background: rgba(15, 23, 42, 0.78);
  box-shadow: 0 0 0 1px rgba(148, 163, 184, 0.14) inset;
}

:deep(.el-input__inner) {
  color: #e2e8f0;
}

.submit-btn {
  width: 100%;
  margin-top: 8px;
}

@media (max-width: 980px) {
  .auth-page {
    grid-template-columns: 1fr;
  }

  .hero-grid {
    grid-template-columns: 1fr;
  }
}
</style>
