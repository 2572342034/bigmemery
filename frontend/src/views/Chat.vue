<template>
  <WorkspaceView
    :current-user="currentUser"
    @logout="$emit('logout')"
  />
</template>

<script setup>
import WorkspaceView from './WorkspaceView.vue'

defineProps({
  currentUser: {
    type: Object,
    required: true,
  },
})

defineEmits(['logout'])
</script>
