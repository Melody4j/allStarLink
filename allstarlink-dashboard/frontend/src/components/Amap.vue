<template>
  <div class="amap-container" ref="mapWrapper">
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

      <el-select v-model="maxMarkersToShow" placeholder="显示数量" size="small" style="margin-left: 10px;" @change="loadLocationsToMap">
        <el-option label="100个节点" :value="100" />
        <el-option label="300个节点" :value="300" />
        <el-option label="500个节点" :value="500" />
        <el-option label="1000个节点" :value="1000" />
        <el-option label="全部节点" :value="99999" />
      </el-select>
    </div>

    <!-- 地图说明 -->
    <div class="map-notice">
      <el-alert
        title="地图调试模式"
        type="warning"
        :closable="false"
        show-icon
      >
        <template #default>
          正在调试AllStarLink节点显示。如果看不到节点，请查看浏览器控制台的调试信息。
        </template>
      </el-alert>
    </div>
    
    <!-- 地图容器 -->
    <div ref="mapContainer" class="map"></div>
    
    <!-- 位置信息弹窗 -->
    <div v-if="selectedLocation" class="node-popup">
      <div class="popup-header">
        <h3>{{ selectedLocation.location }} - 节点统计</h3>
        <button class="popup-close" @click="selectedLocation = null">&times;</button>
      </div>
      <div class="popup-content">
        <p><strong>位置:</strong> {{ selectedLocation.location }}</p>
        <p><strong>经纬度:</strong> 
          <template v-if="selectedLocation.latitude && selectedLocation.longitude">
            {{ selectedLocation.latitude.toFixed(4) }}, {{ selectedLocation.longitude.toFixed(4) }}
          </template>
          <template v-else>
            <span v-if="locationCoordinates.value.has(selectedLocation.location)">
              {{ locationCoordinates.value.get(selectedLocation.location)[1].toFixed(4) }}, {{ locationCoordinates.value.get(selectedLocation.location)[0].toFixed(4) }}
            </span>
            <span v-else>自动生成</span>
          </template>
        </p>
        <p><strong>总节点数:</strong> {{ selectedLocation.totalNodes }}</p>
        <p><strong>活跃节点数:</strong> {{ selectedLocation.activeNodes }}</p>
        <p><strong>非活跃节点数:</strong> {{ selectedLocation.totalNodes - selectedLocation.activeNodes }}</p>
        <p><strong>活跃比例:</strong> {{ ((selectedLocation.activeNodes / selectedLocation.totalNodes) * 100).toFixed(1) }}%</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick, onUnmounted } from 'vue'
import AMapLoader from '@amap/amap-jsapi-loader'

// 组件属性
const props = defineProps({
  locationStats: {
    type: Array,
    default: () => []
  }
})

// 组件状态
const mapContainer = ref(null)
const mapWrapper = ref(null)
const map = ref(null)
const AMapInstance = ref(null) // 存储AMap实例
const mapType = ref('markers')
const activeFilter = ref('all')
const selectedLocation = ref(null)
const markersLayer = ref(null)
const heatmapLayer = ref(null)
const markerClusterer = ref(null) // 节点聚合器
const locationCoordinates = ref(new Map()) // 缓存位置坐标，避免重复请求
const maxMarkersToShow = ref(500) // 最大显示节点数

// 地图初始化
const initMap = () => {
  if (!mapContainer.value) {
    console.error('地图容器未找到')
    return
  }
  
  console.log('开始初始化高德地图...')
  console.log('地图容器:', mapContainer.value)
  
  AMapLoader.load({
    key: '2d608fb0a4f54f0bf39462b10bb7dce3', // 用户提供的实际高德地图API密钥
    securityJsCode: 'f53692c16585a101a8434cb7b57eacbe', // 用户提供的安全密钥
    version: '2.0',
    plugins: ['AMap.HeatMap', 'AMap.MarkerClusterer']
  }).then((AMap) => {
    console.log('高德地图加载成功')
    AMapInstance.value = AMap // 保存AMap实例
    
    // 创建地图实例，设置为美国中心（AllStarLink主要区域）
    map.value = new AMap.Map(mapContainer.value, {
      center: [-100, 40], // 美国中心
      zoom: 4, // 适合美国大陆的缩放级别
      viewMode: '2D', // 使用2D视图，提升性能
      mapStyle: 'amap://styles/normal', // 使用默认地图样式，确保地图瓦片正常显示
      showLabel: true, // 开启标签显示，获取更详细的国外地址信息
      features: ['bg', 'road', 'point', 'label'], // 显示所有可用要素，包括标签
      lang: 'en' // 使用英文显示国外地址，获得更准确的国外地名
    })
    
    console.log('地图实例创建成功')
    console.log('地图实例:', map.value)
    
    // 初始化图层 - 不添加额外的TileLayer，使用地图默认图层
    markersLayer.value = []

    // 初始化热力图
    heatmapLayer.value = new AMap.HeatMap(map.value, {
      radius: 30,
      opacity: [0, 0.8]
    })

    // 初始化节点聚合器
    markerClusterer.value = new AMap.MarkerClusterer(map.value, [], {
      gridSize: 60,        // 聚合网格大小
      maxZoom: 15,         // 聚合的最大缩放级别
      averageCenter: true, // 聚合点是否是所有聚合内点的平均中心
      styles: [{
        url: 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="40" height="40"%3E%3Ccircle cx="20" cy="20" r="18" fill="rgba(67,194,58,0.8)" stroke="white" stroke-width="2"/%3E%3Ctext x="20" y="25" font-size="12" text-anchor="middle" fill="white" font-weight="bold"%3E[count]%3C/text%3E%3C/svg%3E',
        size: new AMap.Size(40, 40),
        offset: new AMap.Pixel(-20, -20),
        textColor: '#fff',
        textSize: 12
      }]
    })

    console.log('图层初始化成功（包含聚合器）')
    console.log('初始位置数据:', props.locationStats)

    // 加载位置数据
    loadLocationsToMap()
  }).catch(error => {
    console.error('高德地图加载失败:', error)
    console.error('错误详情:', error.message)
    console.error('错误堆栈:', error.stack)
  })
}

// 加载位置数据到地图
const loadLocationsToMap = async () => {
  if (!map.value || !AMapInstance.value) {
    console.error('❌ 地图或AMap实例未准备好!')
    console.log('map.value:', map.value)
    console.log('AMapInstance.value:', AMapInstance.value)
    return
  }

  console.log('🗺️ 开始加载位置数据到地图...')
  console.log('📊 原始位置数据数量:', props.locationStats.length)
  console.log('📋 原始位置数据示例:', props.locationStats.slice(0, 2))

  // 清空现有标记
  markersLayer.value.forEach(marker => {
    map.value.remove(marker)
  })
  markersLayer.value = []

  // 清空聚合器
  if (markerClusterer.value) {
    markerClusterer.value.setMarkers([])
  }

  // 清空热力图数据（如果存在）
  if (heatmapLayer.value && typeof heatmapLayer.value.setData === 'function') {
    heatmapLayer.value.setData([])
  }
  
  // 过滤位置数据 - 后端现在返回的是节点列表，不是按位置分组的统计数据
  let filteredNodes = [...props.locationStats]
  
  console.log('所有节点数据数量:', filteredNodes.length)
  
  // 过滤掉没有位置名称或位置名称为空的记录
  filteredNodes = filteredNodes.filter(node => {
    const hasLocation = node.location && node.location.trim() !== ''
    const isActive = node.isActive || false
    console.log('节点筛选:', node.location, '有位置名:', hasLocation, '是否活跃:', isActive, '是否保留:', hasLocation && isActive)
    return hasLocation && isActive
  })
  
  console.log('过滤后节点数据数量:', filteredNodes.length)
  console.log('过滤后节点数据示例:', filteredNodes.slice(0, 3))
  
  // 如果筛选条件是活跃节点，进一步过滤
  if (activeFilter.value === 'active') {
    filteredNodes = filteredNodes.filter(node => node.isActive)
    console.log('活跃节点筛选后数量:', filteredNodes.length)
  } 
  // 非活跃节点筛选（虽然后端已经只返回活跃节点，但保留逻辑）
  else if (activeFilter.value === 'inactive') {
    filteredNodes = filteredNodes.filter(node => !node.isActive)
    console.log('非活跃节点筛选后数量:', filteredNodes.length)
  }
  
  // 性能优化：限制显示的节点数量
  if (filteredNodes.length > maxMarkersToShow.value) {
    // 按节点ID排序，保证一致性（也可以按其他字段如最近在线时间排序）
    filteredNodes.sort((a, b) => b.nodeId - a.nodeId)
    filteredNodes = filteredNodes.slice(0, maxMarkersToShow.value)
    console.log(`性能优化：节点数量过多，只显示前 ${maxMarkersToShow.value} 个节点`)
  }

  console.log('🎯 最终显示的节点数量:', filteredNodes.length)
  console.log('🎯 第一个节点示例:', filteredNodes[0])

  if (mapType.value === 'markers') {
    // 添加节点标记（暂时使用直接模式，不使用聚合）
    console.log('🚀 开始添加节点标记（直接模式）...')
    let addedCount = 0
    for (const node of filteredNodes) {
      await addNodeMarkerDirect(node)
      addedCount++
      if (addedCount <= 3) {
        console.log(`✅ 已处理节点 ${addedCount}/${filteredNodes.length}:`, node.nodeId)
      }
    }
    console.log('✨ 节点标记添加完成！共添加:', markersLayer.value.length, '个标记')
  } else if (mapType.value === 'heatmap') {
    // 创建热力图
    console.log('开始创建热力图...')
    await createHeatmap(filteredNodes)
    console.log('热力图创建完成')
  }
}

// 创建节点标记（用于聚合）
const createNodeMarker = async (node) => {
  if (!node || !node.location || !AMapInstance.value) {
    console.log('跳过无效节点数据:', node)
    return
  }
  
  // 清理位置名称，去除前后空格和特殊字符
  const cleanedLocation = node.location ? node.location.trim() : ''
  if (!cleanedLocation) {
    console.log('跳过空位置名称:', node)
    return
  }
  
  console.log('处理节点:', cleanedLocation, '节点ID:', node.nodeId, '是否活跃:', node.isActive)
  
  try {
    // 获取位置坐标 - 直接使用后端返回的经纬度
    let lngLat = null
    
    // 检查后端是否返回了经纬度
    if (node.latitude && node.longitude) {
      lngLat = [node.longitude, node.latitude] // 注意：高德地图使用 [经度, 纬度] 顺序
      console.log(`使用后端返回的坐标: ${cleanedLocation} - [${lngLat[0]}, ${lngLat[1]}]`)
    } else {
      // 后端没有返回经纬度，使用哈希生成的示例坐标
      lngLat = await generateExampleCoordinates(cleanedLocation)
      console.log(`使用示例坐标: ${cleanedLocation} - [${lngLat[0]}, ${lngLat[1]}]`)
    }
    
    if (!lngLat) {
      console.log('无法获取坐标，跳过节点:', cleanedLocation)
      return // 无法获取经纬度，跳过该节点
    }
    
    // 设置标记颜色
    const markerColor = node.isActive ? 'rgba(103, 194, 58, 0.8)' : 'rgba(245, 108, 108, 0.8)'
    
    // 创建标记
    const marker = new AMapInstance.value.Marker({
      position: lngLat,
      title: `${cleanedLocation} (节点ID: ${node.nodeId})`,
      icon: new AMapInstance.value.Icon({
        size: new AMapInstance.value.Size(25, 25),
        image: `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='25' height='25'%3E%3Ccircle cx='12.5' cy='12.5' r='12' fill='${markerColor}' /%3E%3Ctext x='12.5' y='17' font-size='10' text-anchor='middle' fill='white' font-weight='bold'%3E${node.nodeId}%3C/text%3E%3C/svg%3E`,
        imageSize: new AMapInstance.value.Size(25, 25)
      })
    })
    
    // 绑定点击事件 - 确保事件能被正确触发
    marker.on('click', function(e) {
      console.log('标记被点击:', cleanedLocation, '节点ID:', node.nodeId)
      console.log('点击事件详情:', e)
      // 传递节点数据
      selectedLocation.value = { 
        ...node, 
        location: cleanedLocation,
        totalNodes: 1, // 单个节点
        activeNodes: node.isActive ? 1 : 0
      }
      console.log('selectedLocation更新:', selectedLocation.value)
    })

    // 设置标记的层级（AMap 2.0 API不支持setZIndex，使用默认层级）
    // marker.setZIndex(node.isActive ? 200 : 100) // 活跃节点层级更高

    console.log('标记创建成功:', cleanedLocation, '节点ID:', node.nodeId)
    return marker // 返回标记对象，由聚合器管理

  } catch (error) {
    console.error('创建节点标记失败:', error)
    console.error('节点数据:', node)
    return null
  }
}

// 直接添加节点标记（不使用聚合）
const addNodeMarkerDirect = async (node) => {
  if (!node || !node.location || !AMapInstance.value) {
    console.log('⚠️ 跳过无效节点数据:', node)
    return
  }

  // 清理位置名称，去除前后空格和特殊字符
  const cleanedLocation = node.location ? node.location.trim() : ''
  if (!cleanedLocation) {
    console.log('⚠️ 跳过空位置名称:', node)
    return
  }

  console.log('🔍 处理节点:', cleanedLocation,
    '节点ID:', node.nodeId,
    '是否活跃:', node.isActive,
    '经纬度:', node.latitude + ',' + node.longitude)

  try {
    // 获取位置坐标 - 直接使用后端返回的经纬度
    let lngLat = null

    // 检查后端是否返回了经纬度
    if (node.latitude && node.longitude) {
      lngLat = [node.longitude, node.latitude] // 注意：高德地图使用 [经度, 纬度] 顺序
      console.log(`使用后端返回的坐标: ${cleanedLocation} - [${lngLat[0]}, ${lngLat[1]}]`)
    } else {
      // 后端没有返回经纬度，使用哈希生成的示例坐标
      lngLat = generateExampleCoordinates(cleanedLocation)
      console.log(`使用示例坐标: ${cleanedLocation} - [${lngLat[0]}, ${lngLat[1]}]`)
    }

    if (!lngLat) {
      console.log('无法获取坐标，跳过节点:', cleanedLocation)
      return // 无法获取经纬度，跳过该节点
    }

    // 设置标记颜色
    const markerColor = node.isActive ? 'rgba(103, 194, 58, 0.8)' : 'rgba(245, 108, 108, 0.8)'

    // 创建标记标题
    let markerTitle = `${cleanedLocation}\n节点ID: ${node.nodeId}\n坐标: ${lngLat[1].toFixed(4)}, ${lngLat[0].toFixed(4)}`

    // 创建简单标记（使用默认图标，避免SVG问题）
    const marker = new AMapInstance.value.Marker({
      position: lngLat,
      title: markerTitle,
      // 暂时使用默认标记，不使用自定义图标
    })

    // 绑定点击事件
    marker.on('click', function(e) {
      console.log('标记被点击:', cleanedLocation, '节点ID:', node.nodeId)
      selectedLocation.value = {
        ...node,
        location: cleanedLocation,
        totalNodes: 1,
        activeNodes: node.isActive ? 1 : 0
      }
      console.log('selectedLocation更新:', selectedLocation.value)
    })

    // 设置标记的层级（AMap 2.0 API不支持setZIndex，使用默认层级）
    // marker.setZIndex(node.isActive ? 200 : 100)

    // 直接添加到地图
    map.value.add(marker)
    markersLayer.value.push(marker)
    console.log('✅ 标记成功添加到地图:', cleanedLocation, '节点ID:', node.nodeId,
      '坐标:', lngLat[0].toFixed(3), lngLat[1].toFixed(3))
  } catch (error) {
    console.error('添加节点标记失败:', error)
    console.error('节点数据:', node)
  }
}

// 根据位置名称生成示例坐标（当后端没有提供经纬度时使用）
const generateExampleCoordinates = (locationName) => {
  // 清理位置名称，去除前后空格
  const cleanedLocation = locationName.trim()
  
  // 如果位置名称为空，直接返回null
  if (!cleanedLocation) {
    return null
  }
  
  // 检查缓存
  if (locationCoordinates.value.has(cleanedLocation)) {
    return locationCoordinates.value.get(cleanedLocation)
  }
  
  // 根据位置名称生成不同的坐标，使标记分散显示
  const hash = cleanedLocation.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)
  const lng = -120 + (hash % 40) // 生成 -120 到 -80 之间的经度
  const lat = 25 + (hash % 30) // 生成 25 到 55 之间的纬度
  const exampleLngLat = [lng, lat]
  
  // 缓存坐标结果
  locationCoordinates.value.set(cleanedLocation, exampleLngLat)
  return exampleLngLat
}

// 创建热力图
const createHeatmap = async (nodes) => {
  if (!map.value || !AMapInstance.value) return
  
  const heatPoints = []
  
  for (const node of nodes) {
    if (!node || !node.location) continue
    
    // 获取位置坐标
    let lngLat = null
    
    // 检查后端是否返回了经纬度
    if (node.latitude && node.longitude) {
      lngLat = [node.longitude, node.latitude] // 注意：高德地图使用 [经度, 纬度] 顺序
    } else {
      // 后端没有返回经纬度，使用哈希生成的示例坐标
      lngLat = await generateExampleCoordinates(node.location)
    }
    
    if (lngLat) {
      // 根据节点活跃状态设置热力图强度
      const intensity = node.isActive ? 10 : 1
      heatPoints.push({
        lng: lngLat[0],
        lat: lngLat[1],
        count: intensity
      })
    }
  }
  
  // 确保热力图实例存在
  if (!heatmapLayer.value) {
    heatmapLayer.value = new AMapInstance.value.HeatMap(map.value, {
      radius: 30,
      opacity: [0, 0.8]
    })
  }
  
  // 设置热力图数据
  if (typeof heatmapLayer.value.setData === 'function') {
    heatmapLayer.value.setData(heatPoints)
  }
}

// 监听地图类型变化
watch(mapType, () => {
  loadLocationsToMap()
})

// 监听筛选条件变化
watch(activeFilter, () => {
  loadLocationsToMap()
})

// 监听位置统计数据变化
watch(() => props.locationStats, () => {
  loadLocationsToMap()
}, { deep: true })

// 组件挂载后初始化地图
onMounted(() => {
  nextTick(() => {
    initMap()
  })
})

// 组件卸载时清理资源
onUnmounted(() => {
  if (markerClusterer.value) {
    markerClusterer.value.setMarkers([])
  }
  if (map.value) {
    map.value.destroy()
  }
})
</script>

<style scoped>
.amap-container {
  position: relative;
  width: 100%;
  height: 100%;
  display: block;
  min-height: 500px;
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
  z-index: 10;
}

.map-notice {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 1000;
  max-width: 350px;
}

.map {
  width: 100%;
  height: 500px;
  position: relative;
  background-color: #f0f0f0;
  border: 1px solid #ddd;
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
</style>