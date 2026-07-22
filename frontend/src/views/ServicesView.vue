<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ChatDotRound, CircleCheck, Connection, Goods, Location, Phone, Refresh, Search, Tools } from '@element-plus/icons-vue'

const router = useRouter()
const query = ref('')
const activeCategory = ref('全部')
const orderNumber = ref('')
const searched = ref(false)

const services = [
  { icon: Tools, title: '智能故障诊断', desc: '按设备与现象逐步排查，必要时带着诊断记录转人工', tag: '设备服务', action: '帮我逐步排查设备故障，请先询问设备型号和具体表现', featured: true },
  { icon: Search, title: '服务进度查询', desc: '查看维修、退换货和寄修服务的当前进度', tag: '售后服务', panel: 'tracking' },
  { icon: Refresh, title: '退换与维修', desc: '判断是否符合政策，并生成申请所需材料清单', tag: '售后服务', action: '我想申请退换货或维修，请帮我判断条件并列出需要准备的材料' },
  { icon: Goods, title: '订单与物流', desc: '查询订单状态、配送节点及签收异常处理方式', tag: '订单服务', action: '我需要查询订单或物流，请告诉我需要提供哪些信息' },
  { icon: Location, title: '附近服务网点', desc: '在地图上查找授权网点，查看地址、电话与导航', tag: '线下服务', route: 'service-centers' },
  { icon: Connection, title: '设备互联助手', desc: '解决米家配网、账号绑定和多设备联动问题', tag: '设备服务', action: '请帮助我解决米家设备配网、绑定或联动问题' },
  { icon: Phone, title: '人工客服', desc: '复杂问题一键转接，并自动整理问题摘要', tag: '人工服务', action: '我的问题需要人工客服，请先帮我整理问题摘要和需要提供的信息' },
  { icon: CircleCheck, title: '保修权益查询', desc: '了解保修范围、期限与意外保障权益', tag: '售后服务', action: '请帮我查询设备保修权益，先询问购买日期、渠道和设备型号' },
]

const categories = ['全部', '售后服务', '设备服务', '订单服务', '线下服务']
const visibleServices = computed(() => services.filter((item) => {
  const matchesCategory = activeCategory.value === '全部' || item.tag === activeCategory.value
  const keyword = query.value.trim().toLowerCase()
  return matchesCategory && (!keyword || `${item.title}${item.desc}${item.tag}`.toLowerCase().includes(keyword))
}))

function openService(item: typeof services[number]): void {
  if (item.panel === 'tracking') {
    document.querySelector('#tracking')?.scrollIntoView({ behavior: 'smooth' })
    return
  }
  if (item.route) {
    void router.push({ name: item.route })
    return
  }
  if (item.action) void router.push({ name: 'chat', query: { prompt: item.action } })
}

function trackOrder(): void {
  searched.value = Boolean(orderNumber.value.trim())
}
</script>

<template>
  <section class="services-page">
    <header class="hero">
      <div class="hero__copy"><span>MI SMART SERVICE</span><h1>服务，不止回答问题</h1><p>从发现问题到解决问题，把查询、诊断、申请和人工协助放在一个地方。</p></div>
      <div class="search-box"><el-icon><Search /></el-icon><input v-model="query" aria-label="搜索服务" placeholder="搜索维修、物流、配网…" /><kbd>⌘ K</kbd></div>
    </header>

    <div class="service-overview">
      <div><i class="online" /><span><b>7 × 24</b><small>AI 在线服务</small></span></div>
      <div><b>3 min</b><small>预计自助解决</small></div>
      <div><b>全链路</b><small>服务记录可追踪</small></div>
    </div>

    <nav class="filters" aria-label="服务分类"><button v-for="category in categories" :key="category" :class="{ active: activeCategory === category }" @click="activeCategory = category">{{ category }}</button></nav>

    <div class="services-grid">
      <button v-for="item in visibleServices" :key="item.title" class="service-card" :class="{ featured: item.featured }" type="button" @click="openService(item)">
        <span class="service-card__icon"><el-icon><component :is="item.icon" /></el-icon></span>
        <span class="service-card__body"><small>{{ item.tag }}</small><b>{{ item.title }}</b><p>{{ item.desc }}</p></span>
        <span class="arrow">↗</span>
      </button>
      <p v-if="!visibleServices.length" class="empty">没有找到相关服务，换个关键词试试。</p>
    </div>

    <section id="tracking" class="tracking-card">
      <div><small>SERVICE TRACKING</small><h2>一次查询，掌握服务进度</h2><p>支持维修单、退换货单、寄修单。演示环境将展示示例节点，不会提交真实订单信息。</p></div>
      <form @submit.prevent="trackOrder"><label for="order-number">服务单号 / 手机号后四位</label><div><input id="order-number" v-model="orderNumber" placeholder="例如：MI20260722001" /><button type="submit">查询进度</button></div></form>
      <div v-if="searched" class="timeline">
        <div class="done"><i /><span><b>申请已受理</b><small>今天 09:42</small></span></div>
        <div class="current"><i /><span><b>设备检测中</b><small>预计今天 18:00 前完成</small></span></div>
        <div><i /><span><b>维修 / 处理</b><small>等待检测结果</small></span></div>
        <div><i /><span><b>寄回或完成</b><small>待更新</small></span></div>
      </div>
    </section>

    <aside class="human-strip"><span class="avatar"><el-icon><ChatDotRound /></el-icon></span><div><b>问题比较复杂？</b><p>AI 会先整理设备、现象和已尝试步骤，再无缝转给人工客服。</p></div><button @click="router.push({ name: 'chat', query: { prompt: '请帮我整理当前问题并转接人工客服' } })">联系人工</button></aside>
  </section>
</template>

<style scoped>
.services-page{margin:0 auto;max-width:1160px}.hero{align-items:end;display:flex;gap:36px;justify-content:space-between;margin:4px 0 22px}.hero__copy{max-width:650px}.hero__copy>span,.tracking-card>div>small{color:var(--mi-orange);font-family:var(--font-mono);font-size:10px;font-weight:800;letter-spacing:.17em}.hero h1{font-size:clamp(36px,5vw,58px);letter-spacing:-.055em;line-height:1;margin:10px 0 12px}.hero p{color:var(--ink-muted);line-height:1.7;margin:0}.search-box{align-items:center;background:#fff;border:1px solid var(--line);border-radius:15px;box-shadow:var(--shadow-sm);display:flex;gap:10px;min-width:340px;padding:5px 7px 5px 14px}.search-box .el-icon{color:var(--ink-muted)}.search-box input{background:none;border:0;flex:1;min-width:0;outline:0;padding:10px 0}.search-box kbd{background:var(--surface-soft);border:1px solid var(--line);border-radius:7px;color:#96918b;font-size:10px;padding:5px 7px}.service-overview{background:#1d1c1a;border-radius:18px;color:#fff;display:grid;grid-template-columns:1.2fr 1fr 1fr;margin-bottom:25px;padding:17px 22px}.service-overview>div{align-items:center;border-right:1px solid #393733;display:flex;gap:10px;padding:2px 24px}.service-overview>div:first-child{padding-left:0}.service-overview>div:last-child{border:0}.service-overview b,.service-overview small{display:block}.service-overview b{font-size:16px}.service-overview small{color:#aaa59e;font-size:10px;margin-top:2px}.online{background:#41c784;border:4px solid #284c3b;border-radius:50%;height:14px;width:14px}.filters{display:flex;gap:8px;margin-bottom:14px;overflow:auto}.filters button{background:transparent;border:1px solid var(--line);border-radius:999px;color:var(--ink-muted);cursor:pointer;padding:8px 14px;white-space:nowrap}.filters button.active{background:var(--ink);border-color:var(--ink);color:#fff}.services-grid{display:grid;gap:12px;grid-template-columns:repeat(4,1fr)}.service-card{align-items:flex-start;background:#fff;border:1px solid var(--line);border-radius:18px;color:var(--ink);cursor:pointer;display:flex;min-height:190px;padding:20px;position:relative;text-align:left;transition:.2s}.service-card:hover{border-color:#ffbd8e;box-shadow:0 15px 34px rgba(60,50,40,.08);transform:translateY(-3px)}.service-card.featured{background:linear-gradient(145deg,#ff7718,#f25800);border-color:transparent;color:#fff}.service-card__icon{background:#fff2e8;border-radius:12px;color:var(--mi-orange);display:grid;font-size:23px;height:42px;place-items:center;min-width:42px}.featured .service-card__icon{background:rgba(255,255,255,.18);color:#fff}.service-card__body{align-self:flex-end;margin-left:-42px;padding-top:55px}.service-card__body small,.service-card__body b{display:block}.service-card__body small{color:var(--mi-orange);font-size:9px;font-weight:800;letter-spacing:.1em;margin-bottom:6px}.featured .service-card__body small{color:#ffe3d0}.service-card__body b{font-size:17px}.service-card p{color:var(--ink-muted);font-size:12px;line-height:1.6;margin:7px 0 0}.featured p{color:#fff1e8}.arrow{font-size:16px;margin-left:auto}.empty{color:var(--ink-muted);grid-column:1/-1;padding:40px;text-align:center}.tracking-card{align-items:start;background:#fff;border:1px solid var(--line);border-radius:22px;display:grid;gap:28px;grid-template-columns:1.1fr 1fr;margin-top:30px;padding:28px}.tracking-card h2{font-size:28px;letter-spacing:-.035em;margin:8px 0}.tracking-card p{color:var(--ink-muted);font-size:12px;line-height:1.7;margin:0}.tracking-card form label{display:block;font-size:11px;font-weight:700;margin-bottom:8px}.tracking-card form>div{display:flex}.tracking-card input{border:1px solid var(--line);border-radius:10px 0 0 10px;min-width:0;padding:11px 12px;width:100%}.tracking-card form button,.human-strip>button{background:var(--mi-orange);border:0;color:#fff;cursor:pointer;font-weight:700;padding:0 18px}.tracking-card form button{border-radius:0 10px 10px 0;white-space:nowrap}.timeline{display:grid;grid-column:1/-1;grid-template-columns:repeat(4,1fr);padding-top:3px}.timeline>div{border-top:2px solid var(--line);padding:17px 10px 0 0;position:relative}.timeline i{background:#d7d3ce;border:4px solid #fff;border-radius:50%;height:13px;left:0;position:absolute;top:-7px;width:13px}.timeline .done,.timeline .current{border-color:var(--mi-orange)}.timeline .done i,.timeline .current i{background:var(--mi-orange)}.timeline b,.timeline small{display:block}.timeline b{font-size:12px}.timeline small{color:var(--ink-muted);font-size:10px;margin-top:5px}.human-strip{align-items:center;background:#fff3e9;border:1px solid #ffddc4;border-radius:18px;display:flex;gap:14px;margin-top:16px;padding:16px 18px}.avatar{background:var(--mi-orange);border-radius:12px;color:#fff;display:grid;font-size:20px;height:42px;place-items:center;width:42px}.human-strip div{flex:1}.human-strip b{font-size:13px}.human-strip p{color:var(--ink-muted);font-size:11px;margin:4px 0 0}.human-strip>button{border-radius:10px;padding:10px 16px}@media(max-width:950px){.services-grid{grid-template-columns:repeat(2,1fr)}.hero{align-items:stretch;flex-direction:column}.search-box{min-width:0}.tracking-card{grid-template-columns:1fr}}@media(max-width:600px){.services-grid{grid-template-columns:1fr}.service-card{min-height:160px}.service-overview{grid-template-columns:1fr}.service-overview>div{border-bottom:1px solid #393733;border-right:0;padding:10px 0}.timeline{gap:0;grid-template-columns:1fr}.timeline>div{border-left:2px solid var(--line);border-top:0;padding:0 0 22px 22px}.timeline .done,.timeline .current{border-left-color:var(--mi-orange)}.timeline i{left:-7px;top:0}.human-strip{align-items:flex-start;flex-wrap:wrap}.human-strip>button{margin-left:56px}.hero h1{font-size:40px}}
</style>
