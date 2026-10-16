<template>
  <div v-if="initializing" class="boot-screen">
    <div class="boot-card">
      <p>BigMemery AI Workspace</p>
      <span>Loading enterprise console...</span>
    </div>
  </div>

  <AuthView
    v-else-if="!currentUser"
    @authenticated="handleAuthenticated"
  />

  <KnowledgeBaseView
    v-else-if="currentPage === 'knowledge'"
    :current-user="currentUser"
    @back-chat="currentPage = 'chat'"
    @logout="handleLogout"
  />

  <WorkspaceView
    v-else
    :current-user="currentUser"
    @open-knowledge="currentPage = 'knowledge'"
    @logout="handleLogout"
  />
</template>

<script setup>
import { onMounted, ref } from 'vue'
import AuthView from './views/AuthView.vue'
import KnowledgeBaseView from './views/KnowledgeBaseView.vue'
import WorkspaceView from './views/WorkspaceView.vue'
import { getCurrentUser } from './api/auth'
import { clearSession, getAccessToken, getStoredUser, setAccessToken, setStoredUser } from './api/http'

const initializing = ref(true)
const currentUser = ref(getStoredUser())
const currentPage = ref('chat')

function handleAuthenticated(payload) {
  setAccessToken(payload.access_token)
  setStoredUser(payload.user)
  currentUser.value = payload.user
  currentPage.value = 'chat'
}

function handleLogout() {
  clearSession()
  currentUser.value = null
  currentPage.value = 'chat'
}

onMounted(async () => {
  if (!getAccessToken()) {
    initializing.value = false
    return
  }

  try {
    currentUser.value = await getCurrentUser()
    setStoredUser(currentUser.value)
  } catch (error) {
    clearSession()
    currentUser.value = null
  } finally {
    initializing.value = false
  }
})
</script>

<style scoped>
.boot-screen {
  min-height: 100vh;
  display: grid;
  place-items: center;
}

.boot-card {
  padding: 28px 32px;
  border-radius: 24px;
  background: rgba(11, 18, 32, 0.88);
  border: 1px solid rgba(148, 163, 184, 0.16);
  color: #e2e8f0;
  box-shadow: 0 24px 64px rgba(15, 23, 42, 0.4);
}

.boot-card p {
  margin: 0 0 8px;
  font-size: 18px;
  font-weight: 600;
}

.boot-card span {
  color: #94a3b8;
}
</style>
