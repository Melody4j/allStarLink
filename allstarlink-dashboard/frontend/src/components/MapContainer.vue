<template>
  <div class="map-container tech-map">
    <!-- 科技风背景装饰 -->
    <div class="tech-frame">
      <div class="frame-corner frame-corner-tl"></div>
      <div class="frame-corner frame-corner-tr"></div>
      <div class="frame-corner frame-corner-bl"></div>
      <div class="frame-corner frame-corner-br"></div>
      <div class="frame-edge frame-edge-top"></div>
      <div class="frame-edge frame-edge-right"></div>
      <div class="frame-edge frame-edge-bottom"></div>
      <div class="frame-edge frame-edge-left"></div>
    </div>

    <!-- 地图主体 -->
    <div
      id="amap-container"
      ref="mapContainer"
      class="map-wrapper tech-map-wrapper"
    />

    <!-- 科技风加载遮罩 -->
    <div v-show="mapStore.isMapLoading" class="map-loading tech-loading">
      <div class="loading-content">
        <div class="loading-spinner">
          <div class="spinner-ring"></div>
          <div class="spinner-ring"></div>
          <div class="spinner-ring"></div>
        </div>
        <div class="loading-text">
          <span class="loading-dots">正在加载节点数据</span>
          <div class="loading-progress">
            <div class="progress-bar"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- 科技风控制面板 -->
    <div class="map-controls tech-controls">
      <div class="control-panel">
        <!-- 头部装饰 -->
        <div class="panel-header">
          <div class="header-line"></div>
          <span class="header-text">MAP CONTROL</span>
          <div class="header-indicator">
            <div class="indicator-dot active"></div>
          </div>
        </div>

        <!-- 统计信息 -->
        <div class="stats-section">
          <div class="stat-item">
            <div class="stat-label">
              <span class="stat-icon">◯</span>
              <span class="stat-title">可视区域节点</span>
            </div>
            <div class="stat-value">
              <span class="value-number">{{ mapStore.mapNodes.length }}</span>
              <span class="value-unit">个</span>
            </div>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <div class="stat-label">
              <span class="stat-icon active">●</span>
              <span class="stat-title">在线节点</span>
            </div>
            <div class="stat-value">
              <span class="value-number online">{{ activeNodesCount }}</span>
              <span class="value-unit">个</span>
            </div>
          </div>
        </div>

        <!-- 缩放信息 -->
        <div class="zoom-section">
          <div class="zoom-display">
            <span class="zoom-label">ZOOM LEVEL</span>
            <span class="zoom-value">{{ String(currentZoomLevel).padStart(2, '0') }}</span>
          </div>
          <div class="zoom-meter">
            <div class="meter-track">
              <div class="meter-fill" :style="{ width: `${(currentZoomLevel / 18) * 100}%` }"></div>
            </div>
          </div>
        </div>

        <!-- 控制按钮组 -->
        <div class="controls-section">
          <div class="control-group">
            <button class="tech-button primary" @click="handleForceRefresh">
              <span class="button-icon">⌖</span>
              <span class="button-text">定位标记</span>
            </button>
            <button class="tech-button secondary" @click="handleTestMarkers">
              <span class="button-icon">◢</span>
              <span class="button-text">Label测试</span>
            </button>
          </div>
          <div class="control-group">
            <button class="tech-button success" @click="handleSimpleTest">
              <span class="button-icon">▲</span>
              <span class="button-text">简单测试</span>
            </button>
            <button class="tech-button warning" @click="handleUltraSimpleTest">
              <span class="button-icon">◆</span>
              <span class="button-text">超简测试</span>
            </button>
          </div>
          <div class="control-group">
            <button class="tech-button info full-width" @click="handleCircleNodes">
              <span class="button-icon">◉</span>
              <span class="button-text">定位图标</span>
            </button>
          </div>
        </div>

        <!-- 底部装饰 -->
        <div class="panel-footer">
          <div class="footer-line"></div>
          <div class="footer-indicators">
            <div class="footer-dot"></div>
            <div class="footer-dot"></div>
            <div class="footer-dot"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- 科技风状态指示器 -->
    <div class="map-status">
      <div class="status-indicator">
        <div class="status-dot" :class="{ 'online': !mapStore.isMapLoading }"></div>
        <span class="status-text">{{ mapStore.isMapLoading ? 'LOADING' : 'ONLINE' }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useMapStore } from '@/stores/mapStore'
import { useMap } from '@/composables/useMap'
import { ElCard, ElStatistic, ElText, ElButton, ElLoading } from 'element-plus'

const mapContainer = ref()
const mapStore = useMapStore()
const currentZoomLevel = ref(2)

// 使用地图 Composable
const {
  initializeMap,
  loadNodesInBounds,
  loadNodesSmart,
  createNodeMarkers,
  showNodeInfo,
  panToLocation,
  forceRefreshMarkers,
  createTestMarkers,
  createSimpleTestMarkers,
  createUltraSimpleTest,
  recreateWithCircleMarkers,
  cleanup
} = useMap()

// 计算活跃节点数量
const activeNodesCount = computed(() => {
  return mapStore.mapNodes.filter(node => node.isActive).length
})

// 监听地图缩放变化
const updateZoomLevel = () => {
  if (mapStore.mapInstance) {
    currentZoomLevel.value = mapStore.mapInstance.getZoom()
  }
}

// 滚轮缩放状态标记
let isWheelZooming = false
let wheelZoomTimeout = null

// 强制刷新地图标记
const handleForceRefresh = async () => {
  console.log('用户点击强制刷新标记按钮')
  await forceRefreshMarkers()
}

// 测试标记样式
const handleTestMarkers = async () => {
  console.log('用户点击测试样式按钮')
  await createTestMarkers()
}

// 简单测试标记
const handleSimpleTest = async () => {
  console.log('用户点击简单测试按钮')
  await createSimpleTestMarkers()
}

// 超简单测试标记
const handleUltraSimpleTest = async () => {
  console.log('用户点击超简单测试按钮')
  await createUltraSimpleTest()
}

// 真实节点CircleMarker
const handleCircleNodes = async () => {
  console.log('用户点击真实节点按钮')
  await recreateWithCircleMarkers()
}

onMounted(async () => {
  if (mapContainer.value) {
    await initializeMap(mapContainer.value)

    // 监听缩放变化
    if (mapStore.mapInstance) {
      mapStore.mapInstance.on('zoomchange', updateZoomLevel)
      updateZoomLevel()
    }

    // 防止地图拖拽时页面滚动
    const mapElement = mapContainer.value
    if (mapElement) {
      const preventScroll = (e) => {
        e.preventDefault()
        e.stopPropagation()
        return false
      }

      // 阻止触摸和滚轮事件的默认行为
      mapElement.addEventListener('touchmove', preventScroll, { passive: false })

      // 优化滚轮事件处理，使用状态标记防止页面滚动
      mapElement.addEventListener('wheel', (e) => {
        // 检查鼠标是否在地图容器内
        const rect = mapElement.getBoundingClientRect()
        const isInMap = e.clientX >= rect.left && 
                        e.clientX <= rect.right && 
                        e.clientY >= rect.top && 
                        e.clientY <= rect.bottom

        if (isInMap) {
          // 标记正在缩放
          isWheelZooming = true

          // 清除之前的超时
          if (wheelZoomTimeout) {
            clearTimeout(wheelZoomTimeout)
          }

          // 设置新的超时，在缩放结束后重置状态
          wheelZoomTimeout = setTimeout(() => {
            isWheelZooming = false
          }, 500)

          // 阻止默认行为和事件冒泡
          e.preventDefault()
          e.stopPropagation()
          e.stopImmediatePropagation()
          return false
        }
      }, { passive: false })

      mapElement.addEventListener('scroll', (e) => {
        // 如果正在滚轮缩放，阻止滚动事件
        if (isWheelZooming) {
          e.preventDefault()
          e.stopPropagation()
          return false
        }
      }, { passive: false })
    }
  }
})

onUnmounted(() => {
  cleanup()
})

// 暴露给父组件的方法
defineExpose({
  panToLocation,
  showNodeInfo
})
</script>

<style scoped>
/* === 主地图容器 === */
.map-container {
  position: relative;
  width: 100%;
  height: 600px;
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-lg);
  touch-action: none;
  user-select: none;
  pointer-events: auto;
  background: var(--bg-card);
  border: 1px solid var(--border-primary);
}

.tech-map {
  background: linear-gradient(135deg,
    rgba(45, 52, 54, 0.95) 0%,
    rgba(53, 59, 72, 0.95) 50%,
    rgba(45, 52, 54, 0.95) 100%);
  backdrop-filter: blur(10px);
}

/* === 科技风边框 === */
.tech-frame {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  z-index: 1;
}

.frame-corner {
  position: absolute;
  width: 20px;
  height: 20px;
  border: 2px solid var(--primary-color);
}

.frame-corner-tl {
  top: 0;
  left: 0;
  border-right: none;
  border-bottom: none;
}

.frame-corner-tr {
  top: 0;
  right: 0;
  border-left: none;
  border-bottom: none;
}

.frame-corner-bl {
  bottom: 0;
  left: 0;
  border-right: none;
  border-top: none;
}

.frame-corner-br {
  bottom: 0;
  right: 0;
  border-left: none;
  border-top: none;
}

.frame-edge {
  position: absolute;
  background: var(--primary-gradient);
  opacity: 0.6;
  animation: frame-pulse 3s ease-in-out infinite;
}

.frame-edge-top {
  top: 0;
  left: 20px;
  right: 20px;
  height: 1px;
}

.frame-edge-right {
  top: 20px;
  right: 0;
  bottom: 20px;
  width: 1px;
}

.frame-edge-bottom {
  bottom: 0;
  left: 20px;
  right: 20px;
  height: 1px;
}

.frame-edge-left {
  top: 20px;
  left: 0;
  bottom: 20px;
  width: 1px;
}

@keyframes frame-pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 0.8; }
}

/* === 地图包装器 === */
.tech-map-wrapper {
  width: 100%;
  height: 100%;
  position: relative;
  z-index: 2;
  touch-action: none;
  user-select: none;
  overscroll-behavior: none;
  border-radius: var(--radius-lg);
  overflow: hidden;
}

/* === 科技风加载效果 === */
.tech-loading {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(26, 27, 58, 0.9);
  backdrop-filter: blur(10px);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 50;
}

.loading-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-lg);
}

.loading-spinner {
  position: relative;
  width: 80px;
  height: 80px;
}

.spinner-ring {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  border: 2px solid transparent;
  border-radius: 50%;
  animation: spin 2s linear infinite;
}

.spinner-ring:nth-child(1) {
  border-top-color: var(--primary-color);
  animation-duration: 2s;
}

.spinner-ring:nth-child(2) {
  border-right-color: var(--tech-blue);
  animation-duration: 1.5s;
  animation-direction: reverse;
}

.spinner-ring:nth-child(3) {
  border-bottom-color: var(--tech-cyan);
  animation-duration: 3s;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-text {
  text-align: center;
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 500;
}

.loading-dots::after {
  content: '';
  animation: loading-dots 1.5s infinite;
}

@keyframes loading-dots {
  0%, 20% { content: ''; }
  40% { content: '.'; }
  60% { content: '..'; }
  80%, 100% { content: '...'; }
}

.loading-progress {
  width: 200px;
  height: 2px;
  background: var(--surface-secondary);
  border-radius: var(--radius-full);
  margin-top: var(--spacing-sm);
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: var(--primary-gradient);
  border-radius: var(--radius-full);
  animation: progress-move 2s ease-in-out infinite;
}

@keyframes progress-move {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

/* === 科技风控制面板 === */
.tech-controls {
  position: absolute;
  top: var(--spacing-lg);
  right: var(--spacing-lg);
  z-index: 10;
}

.control-panel {
  background: rgba(58, 43, 82, 0.95);
  backdrop-filter: blur(20px);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl), var(--glow-primary);
  min-width: 280px;
  overflow: hidden;
  transition: all var(--duration-normal);
}

.control-panel:hover {
  border-color: var(--primary-color);
  box-shadow: var(--shadow-xl), var(--glow-secondary);
}

/* === 面板头部 === */
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--surface-primary);
  border-bottom: 1px solid var(--border-primary);
  position: relative;
}

.panel-header::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--primary-gradient);
  opacity: 0.6;
}

.header-line {
  width: 30px;
  height: 2px;
  background: var(--primary-color);
  border-radius: var(--radius-full);
}

.header-text {
  font-size: 12px;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: 2px;
  text-transform: uppercase;
  font-family: var(--font-mono);
  text-shadow: 0 0 8px rgba(255, 255, 255, 0.8), 0 2px 4px rgba(0, 0, 0, 0.8);
}

.header-indicator {
  display: flex;
  align-items: center;
}

.indicator-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--surface-secondary);
  transition: all var(--duration-normal);
}

.indicator-dot.active {
  background: var(--success);
  box-shadow: 0 0 10px var(--success);
  animation: indicator-blink 2s ease-in-out infinite;
}

@keyframes indicator-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

/* === 统计区域 === */
.stats-section {
  padding: var(--spacing-lg);
  background: var(--bg-card);
}

.stat-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-md) 0;
}

.stat-divider {
  height: 1px;
  background: linear-gradient(90deg,
    transparent 0%,
    var(--border-primary) 20%,
    var(--border-primary) 80%,
    transparent 100%);
  margin: var(--spacing-sm) 0;
}

.stat-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.stat-icon {
  font-size: 16px;
  color: var(--text-secondary);
  transition: color var(--duration-normal);
}

.stat-icon.active {
  color: var(--success);
  text-shadow: 0 0 10px var(--success);
}

.stat-title {
  font-size: 13px;
  color: #ffffff;
  font-weight: 500;
  text-shadow: 0 0 6px rgba(255, 255, 255, 0.7), 0 1px 3px rgba(0, 0, 0, 0.6);
}

.stat-value {
  display: flex;
  align-items: baseline;
  gap: var(--spacing-xs);
}

.value-number {
  font-size: 20px;
  font-weight: 700;
  color: #ffffff;
  font-family: var(--font-mono);
  text-shadow: 0 0 10px rgba(255, 255, 255, 0.8), 0 2px 4px rgba(0, 0, 0, 0.8);
}

.value-number.online {
  color: #00ff9f;
  text-shadow: 0 0 12px rgba(0, 255, 159, 0.8), 0 2px 4px rgba(0, 0, 0, 0.8);
}

.value-unit {
  font-size: 12px;
  color: #e0e0e0;
  text-shadow: 0 0 4px rgba(224, 224, 224, 0.6), 0 1px 2px rgba(0, 0, 0, 0.6);
}

/* === 缩放区域 === */
.zoom-section {
  padding: var(--spacing-lg);
  background: var(--surface-secondary);
  border-top: 1px solid var(--border-primary);
  border-bottom: 1px solid var(--border-primary);
}

.zoom-display {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-md);
}

.zoom-label {
  font-size: 11px;
  color: #ffffff;
  font-weight: 600;
  letter-spacing: 1px;
  font-family: var(--font-mono);
  text-shadow: 0 0 6px rgba(255, 255, 255, 0.7), 0 1px 3px rgba(0, 0, 0, 0.7);
}

.zoom-value {
  font-size: 18px;
  font-weight: 700;
  color: #6c5ce7;
  font-family: var(--font-mono);
  text-shadow: 0 0 12px rgba(108, 92, 231, 0.9), 0 2px 4px rgba(0, 0, 0, 0.8);
}

.zoom-meter {
  width: 100%;
}

.meter-track {
  width: 100%;
  height: 4px;
  background: var(--surface-primary);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.meter-fill {
  height: 100%;
  background: var(--primary-gradient);
  border-radius: var(--radius-full);
  transition: width var(--duration-normal);
  position: relative;
}

.meter-fill::after {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  width: 6px;
  height: 100%;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 0 var(--radius-full) var(--radius-full) 0;
  box-shadow: 0 0 8px rgba(255, 255, 255, 0.6);
}

/* === 控制按钮区域 === */
.controls-section {
  padding: var(--spacing-lg);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.control-group {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-sm);
}

.control-group:last-child {
  grid-template-columns: 1fr;
}

.tech-button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  background: var(--surface-primary);
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--duration-normal);
  position: relative;
  overflow: hidden;
}

.tech-button::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg,
    transparent,
    rgba(255, 255, 255, 0.1),
    transparent);
  transition: left var(--duration-normal);
}

.tech-button:hover::before {
  left: 100%;
}

.tech-button:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md), var(--glow-primary);
}

.tech-button.primary {
  border-color: var(--primary-color);
  background: linear-gradient(135deg, var(--primary-color), var(--primary-dark));
}

.tech-button.secondary {
  border-color: var(--tech-cyan);
  background: linear-gradient(135deg, var(--tech-cyan), var(--tech-teal));
}

.tech-button.success {
  border-color: var(--success);
  background: linear-gradient(135deg, var(--success), var(--tech-teal));
}

.tech-button.warning {
  border-color: var(--warning);
  background: linear-gradient(135deg, var(--warning), var(--error));
}

.tech-button.info {
  border-color: var(--info);
  background: linear-gradient(135deg, var(--info), var(--tech-blue));
}

.tech-button.full-width {
  grid-column: 1 / -1;
}

.button-icon {
  font-size: 14px;
  color: #ffffff;
  text-shadow: 0 0 4px rgba(255, 255, 255, 0.6), 0 1px 2px rgba(0, 0, 0, 0.7);
}

.button-text {
  font-size: 12px;
  color: #ffffff;
  white-space: nowrap;
  text-shadow: 0 0 4px rgba(255, 255, 255, 0.6), 0 1px 2px rgba(0, 0, 0, 0.7);
}

/* === 面板底部 === */
.panel-footer {
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--surface-primary);
  border-top: 1px solid var(--border-primary);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.footer-line {
  width: 60px;
  height: 1px;
  background: var(--primary-color);
  opacity: 0.6;
}

.footer-indicators {
  display: flex;
  gap: var(--spacing-xs);
}

.footer-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--text-disabled);
  animation: footer-pulse 2s ease-in-out infinite;
}

.footer-dot:nth-child(2) {
  animation-delay: 0.5s;
}

.footer-dot:nth-child(3) {
  animation-delay: 1s;
}

@keyframes footer-pulse {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 1; background: var(--primary-color); }
}

/* === 状态指示器 === */
.map-status {
  position: absolute;
  bottom: var(--spacing-lg);
  left: var(--spacing-lg);
  z-index: 10;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  background: rgba(58, 43, 82, 0.9);
  backdrop-filter: blur(10px);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--error);
  transition: all var(--duration-normal);
}

.status-dot.online {
  background: var(--success);
  box-shadow: 0 0 10px var(--success);
}

.status-text {
  font-size: 10px;
  font-weight: 600;
  color: #ffffff;
  letter-spacing: 1px;
  font-family: var(--font-mono);
  text-shadow: 0 0 6px rgba(255, 255, 255, 0.7), 0 1px 3px rgba(0, 0, 0, 0.7);
}

/* === 响应式设计 === */
@media (max-width: 768px) {
  .map-container {
    height: 400px;
  }

  .tech-controls {
    top: var(--spacing-sm);
    right: var(--spacing-sm);
  }

  .control-panel {
    min-width: 240px;
  }

  .control-group {
    grid-template-columns: 1fr;
  }

  .tech-button .button-text {
    font-size: 10px;
  }

  .map-status {
    bottom: var(--spacing-sm);
    left: var(--spacing-sm);
  }
}

@media (max-width: 480px) {
  .tech-controls {
    position: relative;
    top: 0;
    right: 0;
    margin: var(--spacing-sm) 0;
  }

  .control-panel {
    min-width: auto;
    width: 100%;
  }

  .map-status {
    position: relative;
    bottom: auto;
    left: auto;
    justify-content: center;
    margin: var(--spacing-sm) 0;
  }
}

/* === 全局地图样式 === */
:global(.amap-info-window) {
  background: var(--bg-card) !important;
  border: 1px solid var(--border-primary) !important;
  border-radius: var(--radius-md) !important;
  box-shadow: var(--shadow-xl) !important;
  backdrop-filter: blur(10px) !important;
}

:global(.node-info) {
  max-width: 300px;
  color: var(--text-primary) !important;
}

:global(.node-info h4) {
  color: var(--primary-color) !important;
  margin-bottom: var(--spacing-sm) !important;
  font-size: 16px !important;
  text-shadow: 0 0 8px rgba(108, 92, 231, 0.5) !important;
}

:global(.node-info div) {
  margin: var(--spacing-xs) 0 !important;
  font-size: 13px !important;
  line-height: 1.4 !important;
  color: var(--text-secondary) !important;
}

:global(.amap-info-close) {
  background: var(--error) !important;
  color: var(--text-primary) !important;
  border-radius: 50% !important;
  width: 20px !important;
  height: 20px !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  font-size: 12px !important;
  transition: all var(--duration-normal) !important;
}

:global(.amap-info-close:hover) {
  background: var(--primary-color) !important;
  box-shadow: var(--glow-primary) !important;
}
</style>