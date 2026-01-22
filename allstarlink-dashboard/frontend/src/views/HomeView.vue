<template>
  <div class="home-container">
    <h1 style="color: green; margin-bottom: 10px;">✓ AllStarLink 节点仪表盘</h1>
    <p><strong>加载状态:</strong> <span :style="{color: loadingStatus.includes('✗') ? 'red' : 'green'}">{{ loadingStatus }}</span></p>
    
    <!-- 时间范围选择 -->
    <div class="time-range-selector">
      <label>时间范围:</label>
      <el-select
        v-model="timeRange"
        placeholder="选择时间范围"
        size="small"
        @change="handleTimeRangeChange"
        style="width: 200px; margin-left: 10px;"
      >
        <el-option label="最近1小时" value="1" />
        <el-option label="最近24小时" value="24" />
        <el-option label="最近3天" value="72" />
        <el-option label="最近7天" value="168" />
      </el-select>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-cards">
      <stats-card 
        title="总节点数" 
        :count="globalStats.totalNodes || 0" 
        icon="el-icon-data-line"
        color="#409EFF"
      />
      <stats-card 
        title="活跃节点数" 
        :count="globalStats.activeNodes || 0" 
        icon="el-icon-video-camera"
        color="#67C23A"
      />
      <stats-card 
        title="活跃比例" 
        :count="globalStats.activePercentage || 0" 
        icon="el-icon-circle-check"
        color="#E6A23C"
        :is-percentage="true"
      />
      <stats-card 
        title="统计时间" 
        :count="parseInt(timeRange) || 1" 
        icon="el-icon-time"
        color="#F56C6C"
        suffix="小时"
      />
    </div>

    <!-- 地图区域 -->
    <div class="map-container" v-if="true">
      <el-card shadow="hover" style="height: 100%; display: flex; flex-direction: column;">
        <template #header>
          <div class="card-header">
            <span>节点分布地图</span>
          </div>
        </template>
        <div style="flex: 1; overflow: hidden;">
          <amap :location-stats="locationStats" style="width: 100%; height: 100%;" />
        </div>
      </el-card>
    </div>

    <!-- 数据预览 -->
    <div style="margin-top: 20px; background: #f5f7fa; padding: 20px; border-radius: 4px;">
      <h3>全局统计数据</h3>
      <pre>{{ JSON.stringify(globalStats, null, 2) }}</pre>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import StatsCard from '../components/StatsCard.vue'
import Amap from '../components/Amap.vue'
import { getGlobalStats, getAllNodes, getActiveNodes, getNodeStatsByLocation, getLimitedActiveNodes } from '../utils/api'

// 全局统计数据
const globalStats = reactive({
  totalNodes: 0,
  activeNodes: 0,
  activePercentage: 0,
  timestamp: ''
})

// 加载状态
const loadingStatus = ref('初始化中...')

// 节点数据
const nodes = ref([])

// 位置统计数据
const locationStats = ref([])

// 时间范围（小时）
const timeRange = ref('1')

// 获取全局统计数据
const fetchGlobalStats = async () => {
  try {
    loadingStatus.value = '正在加载全局统计...'
    console.log('[API] 获取全局统计，timeRange:', parseInt(timeRange.value))
    
    const stats = await getGlobalStats(parseInt(timeRange.value))
    console.log('[API] 全局统计数据:', stats)
    
    if (stats) {
      Object.assign(globalStats, stats)
      console.log('[Data] globalStats已更新:', globalStats)
    }
    
    loadingStatus.value = '✓ 全局统计加载完成'
  } catch (error) {
    console.error('[Error] 获取全局统计失败:', error)
    loadingStatus.value = '✗ 全局统计加载失败: ' + error.message
  }
}

// 获取位置统计数据（恢复真实API，处理海外坐标）
const fetchLocationStats = async () => {
  try {
    loadingStatus.value = '正在加载位置数据...'
    console.log('[API] 获取活跃节点用于地图显示')

    // 使用真实的活跃节点API
    const data = await getActiveNodes()
    console.log('[API] 活跃节点数据长度:', data?.length)

    if (data) {
      // 不限制节点数量，让地图组件根据用户选择决定显示多少
      let limitedData = Array.isArray(data) ? data : []

      // 过滤和处理节点数据
      console.log('[DEBUG] 原始数据前3个节点:', limitedData.slice(0, 3))

      limitedData = limitedData.filter(node => {
        const hasCoords = node.latitude && node.longitude &&
               node.latitude !== null && node.longitude !== null
        const hasLocation = node.location && node.location.trim() !== ''

        console.log(`[FILTER] 节点 ${node.nodeId}: 有坐标=${hasCoords}, 有位置=${hasLocation}`,
          {lat: node.latitude, lng: node.longitude, location: node.location})

        return hasCoords && hasLocation
      })

      console.log('[DEBUG] 过滤后节点数量:', limitedData.length)

      // 暂时不做坐标映射，直接显示原始坐标
      limitedData = limitedData.map(node => {
        console.log(`[COORD] 节点 ${node.nodeId} 坐标: ${node.latitude}, ${node.longitude}`)
        return {
          ...node,
          originalLatitude: node.latitude,
          originalLongitude: node.longitude
        }
      })

      locationStats.value = limitedData
      console.log('[Data] 处理后的节点数量:', locationStats.value.length)
      console.log('[Data] 示例节点:', limitedData[0])
    }

    loadingStatus.value = '✓ 位置数据加载完成'
  } catch (error) {
    console.error('[Error] 获取位置数据失败:', error)
    loadingStatus.value = '✗ 位置数据加载失败: ' + error.message

    // 如果API失败，回退到测试数据
    console.log('[FALLBACK] 使用备用测试数据')
    locationStats.value = [
      {
        nodeId: 12345,
        location: "北京市 (测试)",
        latitude: 39.9042,
        longitude: 116.4074,
        isActive: true,
        callsign: "TEST1",
        owner: "Test User 1"
      }
    ]
  }
}

// 获取所有节点
const fetchAllNodes = async () => {
  try {
    loadingStatus.value = '正在加载节点列表...'
    console.log('[API] 获取所有节点')
    
    const data = await getAllNodes()
    console.log('[API] 节点列表数据长度:', data?.length)
    
    if (data) {
      nodes.value = Array.isArray(data) ? data : []
      console.log('[Data] nodes已更新，长度:', nodes.value.length)
    }
    
    loadingStatus.value = '✓ 所有数据加载完成'
  } catch (error) {
    console.error('[Error] 获取节点列表失败:', error)
    loadingStatus.value = '✗ 数据加载完成（部分数据失败）'
  }
}

// 获取所有数据
const fetchData = async () => {
  try {
    console.log('[Load] 开始加载所有数据，timeRange:', timeRange.value)
    
    // 并行获取数据
    await Promise.all([
      fetchGlobalStats(),
      fetchLocationStats(),
      fetchAllNodes()
    ])
    
    console.log('[Load] 所有数据加载完成')
    loadingStatus.value = '✓ 加载完成'
  } catch (error) {
    console.error('[Error] 数据加载出错:', error)
    loadingStatus.value = '✗ 数据加载失败'
  }
}

// 处理时间范围变化
const handleTimeRangeChange = () => {
  console.log('[Event] 时间范围变化:', timeRange.value)
  fetchData()
}

// 页面加载时获取数据
onMounted(() => {
  console.log('[Mount] HomeView已挂载，开始获取初始数据')
  fetchData()
})
</script>

<style scoped>
.home-container {
  padding: 20px;
}

.page-title {
  font-size: 24px;
  margin-bottom: 20px;
  color: #303133;
}

/* 时间范围选择器 */
.time-range-selector {
  margin: 20px 0;
  padding: 15px;
  background-color: #f5f7fa;
  border-radius: 8px;
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}

/* 统计卡片容器 */
.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

/* 地图容器 */
.map-container {
  margin-bottom: 20px;
  height: 600px;
}

/* 卡片样式 */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

h1 {
  margin-bottom: 10px;
  margin-top: 0;
  font-size: 28px;
}

h3 {
  margin-top: 0;
  color: #303133;
}

pre {
  background-color: #f5f5f5;
  padding: 15px;
  border-radius: 4px;
  overflow-x: auto;
  max-height: 300px;
  font-size: 12px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .stats-cards {
    grid-template-columns: 1fr;
  }
  
  .map-container {
    height: 400px;
  }
  
  .time-range-selector {
    flex-direction: column;
    align-items: flex-start;
  }
  
  h1 {
    font-size: 20px;
  }
}
</style>