<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import AppShell from '@/components/AppShell.vue'

const route = useRoute()
const isLogin = computed(() => route.name === 'login')
</script>

<template>
  <RouterView v-if="isLogin" v-slot="{ Component }">
    <transition name="fade-transform" mode="out-in">
      <component :is="Component" />
    </transition>
  </RouterView>
  <AppShell v-else>
    <RouterView v-slot="{ Component }">
      <transition name="fade-transform" mode="out-in">
        <component :is="Component" />
      </transition>
    </RouterView>
  </AppShell>
</template>

