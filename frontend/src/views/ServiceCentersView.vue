<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef } from 'vue'
import { ArrowLeft, Location, Phone, Position, Search } from '@element-plus/icons-vue'

interface Point { lng: number; lat: number }
interface ServiceCenter { id: string; name: string; address: string; tel: string; distance?: number; district: string; location: Point }
interface PoiRecord {
  id?: string; name?: string; address?: string | string[]; tel?: string | string[]; distance?: number | string; adname?: string
  location?: { lng: number; lat: number; getLng?: () => number; getLat?: () => number }
}
interface SearchResult { poiList?: { pois?: PoiRecord[] } }
interface MapInstance {
  addControl(control: unknown): void; clearMap(): void; destroy(): void
  setFitView(overlays?: unknown[], immediately?: boolean, avoid?: number[]): void
  setZoomAndCenter(zoom: number, center: [number, number]): void
}
interface MarkerInstance { on(event: string, handler: () => void): void; setMap(map: MapInstance | null): void }
interface InfoWindowInstance { open(map: MapInstance, position: [number, number]): void; close(): void }
interface PlaceSearchInstance {
  search(keyword: string, callback: (status: string, result: SearchResult | string) => void): void
  searchNearBy(keyword: string, center: [number, number], radius: number, callback: (status: string, result: SearchResult | string) => void): void
}
interface GeolocationInstance {
  getCurrentPosition(callback: (status: string, result: { position?: Point }) => void): void
}
interface AMapApi {
  Map: new (container: string, options: Record<string, unknown>) => MapInstance
  Marker: new (options: Record<string, unknown>) => MarkerInstance
  InfoWindow: new (options: Record<string, unknown>) => InfoWindowInstance
  PlaceSearch: new (options: Record<string, unknown>) => PlaceSearchInstance
  Geolocation: new (options: Record<string, unknown>) => GeolocationInstance
  ToolBar: new (options?: Record<string, unknown>) => unknown
  Pixel: new (x: number, y: number) => unknown
}

const keyword = ref('小米授权服务中心')
const city = ref('北京')
const loading = ref(true)
const locating = ref(false)
const error = ref('')
const centers = ref<ServiceCenter[]>([])
const selectedId = ref('')
const userPosition = ref<Point>()
const map = shallowRef<MapInstance>()
const infoWindow = shallowRef<InfoWindowInstance>()
let amap: AMapApi | undefined

const apiKey = import.meta.env.VITE_AMAP_KEY?.trim()
const securityCode = import.meta.env.VITE_AMAP_SECURITY_CODE?.trim()
const selectedCenter = computed(() => centers.value.find((item) => item.id === selectedId.value))

function loadAmap(): Promise<AMapApi> {
  const host = window as Window & { AMap?: AMapApi; _AMapSecurityConfig?: { securityJsCode: string } }
  if (host.AMap) return Promise.resolve(host.AMap)
  if (!apiKey || !securityCode) return Promise.reject(new Error('尚未配置高德地图 Key，请在根目录 .env 中填写 VITE_AMAP_KEY 和 VITE_AMAP_SECURITY_CODE'))
  host._AMapSecurityConfig = { securityJsCode: securityCode }
  return new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>('script[data-amap-loader]')
    if (existing) {
      existing.addEventListener('load', () => host.AMap ? resolve(host.AMap) : reject(new Error('地图服务加载失败')))
      existing.addEventListener('error', () => reject(new Error('地图服务加载失败，请检查网络或 Key 配置')))
      return
    }
    const script = document.createElement('script')
    script.dataset.amapLoader = 'true'
    script.src = `https://webapi.amap.com/maps?v=2.0&key=${encodeURIComponent(apiKey)}&plugin=AMap.PlaceSearch,AMap.Geolocation,AMap.ToolBar`
    script.async = true
    script.onload = () => host.AMap ? resolve(host.AMap) : reject(new Error('地图服务初始化失败'))
    script.onerror = () => reject(new Error('地图服务加载失败，请检查网络或 Key 配置'))
    document.head.appendChild(script)
  })
}

function normalizePois(pois: PoiRecord[]): ServiceCenter[] {
  return pois.flatMap((poi, index) => {
    if (!poi.location) return []
    const lng = poi.location.getLng?.() ?? poi.location.lng
    const lat = poi.location.getLat?.() ?? poi.location.lat
    return [{
      id: poi.id || `${lng}-${lat}-${index}`,
      name: poi.name || '小米服务网点',
      address: (Array.isArray(poi.address) ? poi.address.join('') : poi.address) || '地址信息以地图标注为准',
      tel: (Array.isArray(poi.tel) ? poi.tel.join(' / ') : poi.tel) || '暂无公开电话',
      distance: poi.distance === undefined ? undefined : Number(poi.distance),
      district: poi.adname || city.value,
      location: { lng, lat },
    }]
  })
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>'"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[char] || char)
}

function drawMarkers(): void {
  if (!amap || !map.value) return
  map.value.clearMap()
  const overlays: MarkerInstance[] = []
  centers.value.forEach((center, index) => {
    const marker = new amap!.Marker({
      position: [center.location.lng, center.location.lat], title: center.name,
      content: `<button class="amap-mi-marker" aria-label="${escapeHtml(center.name)}"><span>${index + 1}</span></button>`, offset: new amap!.Pixel(-17, -38),
    })
    marker.on('click', () => selectCenter(center))
    marker.setMap(map.value!)
    overlays.push(marker)
  })
  if (overlays.length) map.value.setFitView(overlays, false, [70, 70, 70, 410])
}

function selectCenter(center: ServiceCenter): void {
  if (!amap || !map.value) return
  selectedId.value = center.id
  const distance = center.distance ? ` · 距你 ${formatDistance(center.distance)}` : ''
  infoWindow.value?.close()
  infoWindow.value = new amap.InfoWindow({
    anchor: 'bottom-center', offset: new amap.Pixel(0, -42),
    content: `<div class="amap-info-card"><b>${escapeHtml(center.name)}</b><p>${escapeHtml(center.address)}</p><small>${escapeHtml(center.tel)}${escapeHtml(distance)}</small></div>`,
  })
  infoWindow.value.open(map.value, [center.location.lng, center.location.lat])
  map.value.setZoomAndCenter(15, [center.location.lng, center.location.lat])
  nextTick(() => document.querySelector(`[data-center-id="${CSS.escape(center.id)}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }))
}

function runSearch(): void {
  if (!amap || !map.value) return
  loading.value = true; error.value = ''; selectedId.value = ''
  const search = new amap.PlaceSearch({ city: city.value.trim() || '全国', citylimit: Boolean(city.value.trim()), pageSize: 20, extensions: 'all' })
  const callback = (status: string, result: SearchResult | string) => {
    loading.value = false
    if (status !== 'complete' || typeof result === 'string') {
      centers.value = []; error.value = '没有找到相关网点，请更换城市或搜索关键词'; drawMarkers(); return
    }
    centers.value = normalizePois(result.poiList?.pois ?? []).sort((a, b) => (a.distance ?? Number.MAX_SAFE_INTEGER) - (b.distance ?? Number.MAX_SAFE_INTEGER))
    if (!centers.value.length) error.value = '没有找到相关网点，请更换城市或搜索关键词'
    drawMarkers()
  }
  const text = keyword.value.trim() || '小米授权服务中心'
  if (userPosition.value) search.searchNearBy(text, [userPosition.value.lng, userPosition.value.lat], 50000, callback)
  else search.search(text, callback)
}

function locateMe(): void {
  if (!amap || !map.value) return
  locating.value = true; error.value = ''
  const geolocation = new amap.Geolocation({ enableHighAccuracy: true, timeout: 10000, zoomToAccuracy: true, position: 'RB' })
  map.value.addControl(geolocation)
  geolocation.getCurrentPosition((status, result) => {
    locating.value = false
    if (status !== 'complete' || !result.position) { error.value = '暂时无法获取位置，请允许浏览器定位权限，或手动输入城市搜索'; return }
    userPosition.value = result.position; city.value = ''; runSearch()
  })
}

function formatDistance(distance?: number): string {
  if (distance === undefined || Number.isNaN(distance)) return '距离未知'
  return distance < 1000 ? `${Math.round(distance)} m` : `${(distance / 1000).toFixed(1)} km`
}

function navigateTo(center: ServiceCenter): void {
  const destination = `${center.location.lng},${center.location.lat},${center.name}`
  window.open(`https://uri.amap.com/navigation?to=${encodeURIComponent(destination)}&mode=car&policy=1&src=xiaomi-ai-service&coordinate=gaode&callnative=1`, '_blank', 'noopener,noreferrer')
}

onMounted(async () => {
  try {
    amap = await loadAmap()
    map.value = new amap.Map('service-center-map', { zoom: 11, center: [116.397428, 39.90923], viewMode: '2D', resizeEnable: true })
    map.value.addControl(new amap.ToolBar({ position: 'RT' }))
    runSearch()
  } catch (reason) { loading.value = false; error.value = reason instanceof Error ? reason.message : '地图初始化失败' }
})
onBeforeUnmount(() => { infoWindow.value?.close(); map.value?.destroy() })
</script>

<template>
  <section class="centers-page">
    <header class="page-heading">
      <RouterLink to="/services"><el-icon><ArrowLeft /></el-icon> 返回服务中心</RouterLink>
      <div><span>OFFLINE SERVICE</span><h1>附近服务网点</h1><p>查找小米授权服务网点，查看详细地址、联系方式和导航路线。</p></div>
    </header>
    <form class="search-panel" @submit.prevent="runSearch">
      <label><span>城市</span><input v-model="city" placeholder="例如：北京" /></label>
      <label class="keyword"><span>网点关键词</span><input v-model="keyword" placeholder="小米授权服务中心" /></label>
      <button class="search-button" type="submit"><el-icon><Search /></el-icon>搜索网点</button>
      <button class="locate-button" type="button" :disabled="locating" @click="locateMe"><el-icon><Location /></el-icon>{{ locating ? '定位中…' : '定位附近' }}</button>
    </form>
    <el-alert v-if="error" :title="error" :type="apiKey ? 'warning' : 'error'" show-icon :closable="false" />
    <div class="map-layout">
      <aside class="center-list" aria-label="服务网点列表">
        <div class="list-heading"><div><b>{{ loading ? '正在查找…' : `找到 ${centers.length} 个网点` }}</b><small>{{ userPosition ? '已按距离由近到远排序' : `当前城市：${city || '定位附近'}` }}</small></div><span><i /> 官方地图数据</span></div>
        <div v-if="loading" class="skeleton-list"><i v-for="item in 4" :key="item" /></div>
        <button v-for="(center, index) in centers" :key="center.id" :data-center-id="center.id" class="center-item" :class="{ active: selectedId === center.id }" type="button" @click="selectCenter(center)">
          <span class="number">{{ index + 1 }}</span><span class="center-copy"><b>{{ center.name }}</b><small>{{ center.district }} · {{ formatDistance(center.distance) }}</small><p>{{ center.address }}</p><span class="contact"><em><el-icon><Phone /></el-icon>{{ center.tel }}</em><em class="nav" @click.stop="navigateTo(center)"><el-icon><Position /></el-icon>导航</em></span></span>
        </button>
        <div v-if="!loading && !centers.length" class="empty-state"><el-icon><Location /></el-icon><b>没有找到网点</b><p>尝试更换城市或搜索“小米之家”。</p></div>
      </aside>
      <div class="map-wrap"><div id="service-center-map" /><div v-if="!apiKey" class="map-placeholder"><el-icon><Location /></el-icon><b>地图等待配置</b><p>填写高德 Key 后将自动显示真实地图与网点。</p></div></div>
    </div>
    <aside v-if="selectedCenter" class="mobile-detail"><div><b>{{ selectedCenter.name }}</b><p>{{ selectedCenter.address }}</p></div><button @click="navigateTo(selectedCenter)"><el-icon><Position /></el-icon>去这里</button></aside>
    <p class="map-note">网点信息来自高德地图公开 POI，营业状态和可维修品类可能变化，前往前建议电话确认。</p>
  </section>
</template>

<style scoped>
.centers-page{margin:0 auto;max-width:1220px}.page-heading{align-items:flex-end;display:flex;justify-content:space-between;margin-bottom:22px}.page-heading>a{align-items:center;color:var(--ink-muted);display:flex;font-size:12px;gap:5px;text-decoration:none}.page-heading>a:hover{color:var(--mi-orange)}.page-heading>div{text-align:right}.page-heading span{color:var(--mi-orange);font-family:var(--font-mono);font-size:10px;font-weight:800;letter-spacing:.16em}.page-heading h1{font-size:42px;letter-spacing:-.05em;line-height:1;margin:8px 0}.page-heading p{color:var(--ink-muted);font-size:13px;margin:0}.search-panel{align-items:end;background:#fff;border:1px solid var(--line);border-radius:17px;display:grid;gap:10px;grid-template-columns:180px 1fr auto auto;margin-bottom:14px;padding:13px}.search-panel label span{color:var(--ink-muted);display:block;font-size:10px;font-weight:700;margin:0 0 6px 3px}.search-panel input{border:1px solid var(--line);border-radius:10px;outline:0;padding:10px 11px;width:100%}.search-panel input:focus{border-color:var(--mi-orange);box-shadow:0 0 0 3px rgba(255,105,0,.09)}.search-panel button{align-items:center;border-radius:10px;cursor:pointer;display:flex;font-size:12px;font-weight:700;gap:6px;height:39px;padding:0 15px}.search-button{background:var(--mi-orange);border:1px solid var(--mi-orange);color:#fff}.locate-button{background:#fff;border:1px solid var(--line);color:var(--ink)}.locate-button:disabled{cursor:wait;opacity:.6}.map-layout{background:#fff;border:1px solid var(--line);border-radius:20px;display:grid;grid-template-columns:390px 1fr;height:min(680px,calc(100vh - 260px));margin-top:14px;min-height:520px;overflow:hidden}.center-list{border-right:1px solid var(--line);overflow:auto}.list-heading{align-items:center;background:rgba(255,255,255,.95);border-bottom:1px solid var(--line);display:flex;justify-content:space-between;padding:15px 17px;position:sticky;top:0;z-index:2}.list-heading b,.list-heading small{display:block}.list-heading b{font-size:13px}.list-heading small{color:var(--ink-muted);font-size:9px;margin-top:4px}.list-heading>span{align-items:center;background:#edf7f1;border-radius:99px;color:#28734f;display:flex;font-size:9px;gap:5px;padding:5px 7px}.list-heading i{background:#31a86f;border-radius:50%;height:5px;width:5px}.center-item{background:#fff;border:0;border-bottom:1px solid var(--line);cursor:pointer;display:flex;gap:11px;padding:17px;text-align:left;width:100%}.center-item:hover,.center-item.active{background:#fff7f0}.center-item.active{box-shadow:inset 3px 0 var(--mi-orange)}.number{background:#fff0e5;border:1px solid #ffd7bb;border-radius:9px;color:var(--mi-orange);display:grid;font-size:11px;font-weight:800;height:29px;min-width:29px;place-items:center}.center-copy{min-width:0;width:100%}.center-copy>b{display:block;font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.center-copy>small{color:var(--mi-orange);display:block;font-size:9px;margin-top:5px}.center-copy>p{color:var(--ink-muted);font-size:11px;line-height:1.55;margin:7px 0 10px}.contact{align-items:center;display:flex!important;justify-content:space-between}.contact em{align-items:center;color:var(--ink-muted);display:flex;font-size:9px;font-style:normal;gap:4px}.contact .nav{color:var(--mi-orange);font-weight:700}.map-wrap{min-width:0;position:relative}#service-center-map{height:100%;width:100%}.map-placeholder{align-items:center;background:radial-gradient(circle at center,#fff8f2,#f3f0eb);display:flex;flex-direction:column;inset:0;justify-content:center;position:absolute;text-align:center}.map-placeholder .el-icon{color:var(--mi-orange);font-size:36px}.map-placeholder b{font-size:17px;margin-top:12px}.map-placeholder p{color:var(--ink-muted);font-size:11px}.empty-state{align-items:center;color:var(--ink-muted);display:flex;flex-direction:column;padding:70px 20px;text-align:center}.empty-state .el-icon{color:#c9c4bd;font-size:35px}.empty-state b{color:var(--ink);margin-top:12px}.empty-state p{font-size:11px}.skeleton-list{display:grid;gap:1px}.skeleton-list i{animation:pulse 1.2s infinite alternate;background:linear-gradient(90deg,#f5f3f0,#ebe8e3,#f5f3f0);height:112px}.mobile-detail{display:none}.map-note{color:#a09b95;font-size:10px;margin:10px;text-align:right}:global(.amap-mi-marker){background:var(--mi-orange);border:3px solid #fff;border-radius:50% 50% 50% 7px;box-shadow:0 4px 12px rgba(80,40,10,.28);color:#fff;cursor:pointer;height:34px;transform:rotate(-45deg);width:34px}:global(.amap-mi-marker span){display:block;font-size:11px;font-weight:800;transform:rotate(45deg)}:global(.amap-info-card){font-family:var(--font-body);padding:3px 2px;width:230px}:global(.amap-info-card b){font-size:13px}:global(.amap-info-card p){color:#6e6963;font-size:11px;line-height:1.5;margin:6px 0}:global(.amap-info-card small){color:#ff6900;font-size:9px}@keyframes pulse{to{opacity:.55}}@media(max-width:850px){.page-heading{align-items:flex-start;flex-direction:column;gap:18px}.page-heading>div{text-align:left}.search-panel{grid-template-columns:1fr 1fr}.keyword{grid-column:2}.search-panel button{justify-content:center}.map-layout{display:flex;flex-direction:column;height:auto;min-height:0}.map-wrap{height:390px;order:1}.center-list{border:0;max-height:430px;order:2}.mobile-detail{align-items:center;background:#fff;border:1px solid var(--line);border-radius:15px;bottom:82px;box-shadow:var(--shadow-lg);display:flex;gap:12px;justify-content:space-between;left:24px;padding:12px 14px;position:fixed;right:24px;z-index:50}.mobile-detail div{min-width:0}.mobile-detail b,.mobile-detail p{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.mobile-detail b{font-size:12px}.mobile-detail p{color:var(--ink-muted);font-size:9px;margin:4px 0 0}.mobile-detail button{align-items:center;background:var(--mi-orange);border:0;border-radius:9px;color:#fff;display:flex;gap:4px;padding:9px;white-space:nowrap}}@media(max-width:560px){.page-heading h1{font-size:34px}.search-panel{grid-template-columns:1fr 1fr}.search-panel label{grid-column:1/-1}.map-wrap{height:330px}}
</style>
