<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ products: readonly string[]; intents: Readonly<Record<string, number>> }>()
const intentLabels: Record<string,string> = { knowledge_query:'产品知识',product_comparison:'产品对比',purchase_advice:'选购建议',troubleshooting:'故障诊断',order_query:'订单查询',human_transfer:'人工服务',general_chat:'日常交流' }
const planets = computed(() => [
  ...props.products.slice(0, 5).map((label,index) => ({ label, weight: 5-index, kind:'product' })),
  ...Object.entries(props.intents).sort((a,b)=>b[1]-a[1]).slice(0,4).map(([key,count])=>({ label:intentLabels[key] ?? key, weight:Math.min(5,count), kind:'intent' })),
])
</script>

<template>
  <section class="galaxy-card"><header><div><span>INTEREST CONSTELLATION</span><h2>兴趣星系</h2></div><p>随真实咨询动态生长</p></header><div v-if="planets.length" class="galaxy" aria-label="咨询兴趣星系"><span v-for="(planet,index) in planets" :key="`${planet.kind}-${planet.label}`" class="planet" :class="`planet--${planet.kind}`" :style="{ '--size': `${42 + planet.weight * 8}px`, '--delay': `${index * -.8}s`, '--x': `${12 + (index * 29) % 72}%`, '--y': `${14 + (index * 37) % 68}%` }">{{ planet.label }}</span><i class="orbit orbit--a"/><i class="orbit orbit--b"/></div><div v-else class="galaxy-empty"><b>你的星系还在等待第一束光</b><p>咨询一个具体产品后，这里会形成真实偏好。</p></div></section>
</template>

<style scoped>
.galaxy-card{background:linear-gradient(155deg,#faf8ff,#f2edff);border:1px solid #e2daf3;border-radius:24px;min-height:355px;overflow:hidden;padding:22px;position:relative}.galaxy-card header{align-items:flex-end;display:flex;justify-content:space-between}.galaxy-card header span{color:#7556dc;font-family:var(--font-mono);font-size:9px;letter-spacing:.16em}.galaxy-card h2{font-size:23px;margin:5px 0}.galaxy-card header p{color:#968ba5;font-size:11px}.galaxy{height:260px;position:relative}.planet{align-items:center;animation:planet-float 5s ease-in-out infinite;animation-delay:var(--delay);background:linear-gradient(135deg,#6d50dc,#c95cce);border:1px solid #ffffff8c;border-radius:50%;box-shadow:0 12px 27px rgba(112,73,203,.22);color:white;display:flex;font-size:10px;height:var(--size);justify-content:center;left:var(--x);max-width:105px;padding:7px;position:absolute;text-align:center;top:var(--y);transform:translate(-50%,-50%);width:var(--size);z-index:2}.planet--intent{background:linear-gradient(135deg,#ff6900,#ff9c55);box-shadow:0 12px 27px rgba(255,105,0,.2)}.orbit{border:1px solid #9e84e82b;border-radius:50%;inset:14% 15%;position:absolute;transform:rotate(-12deg)}.orbit--b{inset:28% 4%;transform:rotate(23deg)}.galaxy-empty{display:grid;height:250px;place-content:center;text-align:center}.galaxy-empty b{color:#514263}.galaxy-empty p{color:#978da3;font-size:12px}@keyframes planet-float{50%{transform:translate(-50%,calc(-50% - 9px)) scale(1.04)}}@media(prefers-reduced-motion:reduce){.planet{animation:none}}
</style>
