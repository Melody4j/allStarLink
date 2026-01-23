<template>
  <div class="map-container">
    <div
      id="amap-container"
      ref="mapContainer"
      class="map-wrapper"
    />

    <!-- 加载遮罩 -->
    <div v-show="mapStore.isMapLoading" class="map-loading">
      <el-loading
        :text="'加载节点数据中...'"
        background="rgba(255, 255, 255, 0.8)"
      />
    </div>

    <!-- 地图控制面板 -->
    <div class="map-controls">
      <el-card shadow="hover" class="control-card">
        <div class="stats-info">
          <el-statistic
            title="可视区域节点"
            :value="mapStore.mapNodes.length"
            suffix="个"
            class="stat-item"
          />
          <el-statistic
            title="在线节点"
            :value="activeNodesCount"
            :value-style="{ color: '#67C23A' }"
            suffix="个"
            class="stat-item"
          />
        </div>
        <div class="zoom-info">
          <el-text size="small" type="info">
            缩放级别: {{ currentZoomLevel }}
          </el-text>
          <div style="margin-top: 8px; display: flex; flex-direction: column; gap: 5px;">
            <el-button
              size="small"
              type="primary"
              @click="handleForceRefresh"
            >
              定位标记
            </el-button>
            <el-button
              size="small"
              type="warning"
              @click="handleTestMarkers"
            >
              Label测试
            </el-button>
            <el-button
              size="small"
              type="success"
              @click="handleSimpleTest"
            >
              简单测试
            </el-button>
            <el-button
              size="small"
              type="danger"
              @click="handleUltraSimpleTest"
            >
              超简测试
            </el-button>
            <el-button
              size="small"
              type="info"
              @click="handleCircleNodes"
            >
              定位图标
            </el-button>
          </div>
        </div>
      </el-card>
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
      mapElement.addEventListener('wheel', preventScroll, { passive: false })
      mapElement.addEventListener('scroll', preventScroll, { passive: false })
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
.map-container {
  position: relative;
  width: 100%;
  height: 600px;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  /* 防止地图拖动时页面滚动 */
  touch-action: none;
  user-select: none;
  pointer-events: auto;
}

.map-wrapper {
  width: 100%;
  height: 100%;
  /* 防止地图拖动时页面滚动 */
  touch-action: none;
  user-select: none;
  -webkit-user-select: none;
  -moz-user-select: none;
  -ms-user-select: none;
  /* 强制阻止页面滚动事件传播 */
  overscroll-behavior: none;
  -webkit-overscroll-behavior: none;
}

.map-loading {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  z-index: 10;
}

.map-controls {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 5;
}

.control-card {
  min-width: 200px;
}

.stats-info {
  display: flex;
  gap: 20px;
  margin-bottom: 10px;
}

.stat-item {
  flex: 1;
}

.zoom-info {
  text-align: center;
}

/* 深度定制 Element Plus 组件 */
:deep(.el-statistic__content) {
  font-size: 16px;
}

:deep(.el-statistic__head) {
  font-size: 12px;
  color: #909399;
}

:deep(.el-card__body) {
  padding: 15px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .map-container {
    height: 400px;
  }

  .map-controls {
    top: 5px;
    right: 5px;
  }

  .stats-info {
    flex-direction: column;
    gap: 10px;
  }

  .control-card {
    min-width: 150px;
  }

  :deep(.el-statistic__content) {
    font-size: 14px;
  }
}

/* 地图信息窗体样式 */
:global(.amap-info-window) {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

:global(.node-info) {
  max-width: 280px;
}

:global(.node-info h4) {
  color: #409EFF;
  margin-bottom: 8px;
  font-size: 16px;
}

:global(.node-info div) {
  margin: 4px 0;
  font-size: 13px;
  line-height: 1.4;
}
</style>