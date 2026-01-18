<template>
  <div class="node-map-container">
    <!-- 地图控件 -->
    <div class="map-controls">
      <el-radio-group v-model="mapType" size="small">
        <el-radio-button label="markers">节点标记</el-radio-button>
        <el-radio-button label="heatmap">热力图</el-radio-button>
      </el-radio-group>
      
      <el-select v-model="activeFilter" placeholder="筛选状态" size="small" style="margin-left: 10px;">
        <el-option label="全部节点" value="all" />
        <el-option label="活跃节点" value="active" />
        <el-option label="非活跃节点" value="inactive" />
      </el-select>
    </div>
    
    <!-- 地图容器 -->
    <div ref="mapContainer" class="map"></div>
    
    <!-- 节点信息弹窗 -->
    <div v-if="selectedNode" class="node-popup">
      <div class="popup-header">
        <h3>节点信息</h3>
        <button class="popup-close" @click="selectedNode = null">&times;</button>
      </div>
      <div class="popup-content">
        <p><strong>节点ID:</strong> {{ selectedNode.nodeId }}</p>
        <p><strong>呼号:</strong> {{ selectedNode.callsign }}</p>
        <p><strong>所有者:</strong> {{ selectedNode.owner }}</p>
        <p><strong>位置:</strong> {{ selectedNode.location }}</p>
        <p><strong>频率:</strong> {{ selectedNode.frequency }}</p>
        <p><strong>亚音频:</strong> {{ selectedNode.tone }}</p>
        <p><strong>站点:</strong> {{ selectedNode.site }}</p>
        <p><strong>所属组织:</strong> {{ selectedNode.affiliation }}</p>
        <p><strong>最后在线:</strong> {{ formatDateTime(selectedNode.lastSeen) }}</p>
        <p><strong>状态:</strong> <span :class="selectedNode.isActive ? 'status-active' : 'status-inactive'">
          {{ selectedNode.isActive ? '活跃' : '非活跃' }}</span></p>
        <p><strong>功能:</strong> {{ selectedNode.features || '无' }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { geocodeLocation } from '../utils/api'

// 组件属性
const props = defineProps({
  nodes: {
    type: Array,
    default: () => []
  },
  stats: {
    type: Array,
    default: () => []
  }
})

// 组件状态
const mapContainer = ref(null)
const map = ref(null)
const mapType = ref('markers')
const activeFilter = ref('all')
const selectedNode = ref(null)
const markersLayer = ref(null)
const heatmapLayer = ref(null)

// 地图初始化
const initMap = () => {
  if (!mapContainer.value) return
  
  // 创建地图实例
  map.value = L.map(mapContainer.value, {
    center: [40.0, -95.0], // 默认美国中心
    zoom: 4,
    layers: [
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      })
    ]
  })
  
  // 初始化图层
  markersLayer.value = L.layerGroup().addTo(map.value)
  heatmapLayer.value = L.layerGroup()
  
  // 加载节点数据
  loadNodesToMap()
}

// 加载节点到地图
const loadNodesToMap = async () => {
  if (!map.value) return
  
  // 清空现有标记
  markersLayer.value.clearLayers()
  heatmapLayer.value.clearLayers()
  
  // 过滤节点
  let filteredNodes = [...props.nodes]
  
  // 只保留经纬度不为 null 的节点（在线节点）
  filteredNodes = filteredNodes.filter(node => node.latitude !== null && node.longitude !== null)
  
  if (activeFilter.value === 'active') {
    filteredNodes = filteredNodes.filter(node => node.isActive)
  } else if (activeFilter.value === 'inactive') {
    filteredNodes = filteredNodes.filter(node => !node.isActive)
  }
  
  if (mapType.value === 'markers') {
    // 添加节点标记
    for (const node of filteredNodes) {
      await addNodeMarker(node)
    }
  } else if (mapType.value === 'heatmap') {
    // 创建热力图
    createHeatmap(filteredNodes)
  }
}

// 添加节点标记
const addNodeMarker = async (node) => {
  if (!node || !node.location) return
  
  try {
    // 如果节点有经纬度，直接使用
    let latLng
    if (node.latitude && node.longitude) {
      latLng = [node.latitude, node.longitude]
    } else {
      // 否则尝试地理编码
      const result = await geocodeLocation(node.location)
      if (result.data && result.data.length > 0) {
        latLng = [parseFloat(result.data[0].lat), parseFloat(result.data[0].lon)]
      } else {
        return // 无法获取经纬度
      }
    }
    
    // 创建标记
    const marker = L.marker(latLng, {
      icon: getNodeIcon(node.isActive),
      title: `节点 ${node.nodeId} (${node.callsign})`
    })
    
    // 绑定点击事件
    marker.on('click', () => {
      selectedNode.value = node
    })
    
    // 添加到图层
    marker.addTo(markersLayer.value)
  } catch (error) {
    console.error(`无法为节点 ${node.nodeId} 添加标记:`, error)
  }
}

// 获取节点图标
const getNodeIcon = (isActive) => {
  const color = isActive ? 'green' : 'red'
  const iconSize = [20, 20]
  const iconAnchor = [10, 10]
  
  return L.divIcon({
    className: `node-marker ${isActive ? 'active' : 'inactive'}`,
    html: `<div style="width: ${iconSize[0]}px; height: ${iconSize[1]}px; background-color: ${color}; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 5px rgba(0,0,0,0.5);"></div>`,
    iconSize: iconSize,
    iconAnchor: iconAnchor
  })
}

// 创建热力图
const createHeatmap = (nodes) => {
  // 由于Leaflet默认不支持热力图，这里使用简化的方式
  // 实际项目中可以使用Leaflet.heat插件
  const heatPoints = []
  
  for (const node of nodes) {
    if (node.latitude && node.longitude) {
      heatPoints.push([node.latitude, node.longitude, node.isActive ? 1 : 0.3])
    } else if (node.location) {
      // 可以在这里添加地理编码逻辑
      // 为了简化，这里省略
    }
  }
  
  // 简化的热力图实现：使用圆形标记的密度表示热度
  heatPoints.forEach((point, index) => {
    const [lat, lng, intensity] = point
    const radius = 5 * intensity
    
    L.circle([lat, lng], {
      radius: radius * 1000, // 米
      fillColor: '#ff0000',
      fillOpacity: 0.2,
      stroke: false
    }).addTo(heatmapLayer.value)
  })
  
  // 切换到热力图层
  map.value.removeLayer(markersLayer.value)
  map.value.addLayer(heatmapLayer.value)
}

// 格式化日期时间
const formatDateTime = (dateTime) => {
  if (!dateTime) return '未知'
  
  const date = new Date(dateTime)
  return date.toLocaleString('zh-CN')
}

// 监听地图类型变化
watch(mapType, () => {
  if (!map.value) return
  
  if (mapType.value === 'markers') {
    map.value.removeLayer(heatmapLayer.value)
    map.value.addLayer(markersLayer.value)
  } else if (mapType.value === 'heatmap') {
    map.value.removeLayer(markersLayer.value)
    createHeatmap(props.nodes)
    map.value.addLayer(heatmapLayer.value)
  }
})

// 监听筛选条件变化
watch(activeFilter, () => {
  loadNodesToMap()
})

// 监听节点数据变化
watch(() => props.nodes, () => {
  loadNodesToMap()
}, { deep: true })

// 组件挂载后初始化地图
onMounted(() => {
  nextTick(() => {
    initMap()
  })
})

// 窗口大小变化时调整地图
window.addEventListener('resize', () => {
  if (map.value) {
    map.value.invalidateSize()
  }
})
</script>

<style scoped>
.node-map-container {
  position: relative;
  width: 100%;
  height: 100%;
}

.map-controls {
  position: absolute;
  top: 10px;
  left: 10px;
  z-index: 1000;
  background-color: rgba(255, 255, 255, 0.9);
  padding: 8px 12px;
  border-radius: 4px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
}

.map {
  width: 100%;
  height: 100%;
}

.node-popup {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 300px;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 1000;
  overflow: hidden;
}

.popup-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background-color: #409EFF;
  color: white;
}

.popup-header h3 {
  margin: 0;
  font-size: 16px;
}

.popup-close {
  background: none;
  border: none;
  color: white;
  font-size: 20px;
  cursor: pointer;
  padding: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.popup-content {
  padding: 16px;
}

.popup-content p {
  margin: 8px 0;
  font-size: 14px;
}

.status-active {
  color: #67C23A;
  font-weight: bold;
}

.status-inactive {
  color: #F56C6C;
  font-weight: bold;
}

/* Leaflet 样式修复 */
:deep(.leaflet-popup-content-wrapper) {
  border-radius: 4px;
}

:deep(.leaflet-popup-tip) {
  background-color: white;
}

.node-marker {
  transition: transform 0.2s ease;
}

.node-marker:hover {
  transform: scale(1.2);
}
</style>