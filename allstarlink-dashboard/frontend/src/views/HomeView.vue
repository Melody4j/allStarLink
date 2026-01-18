<template>
  <div class="home-container">
    <h1>测试文本：页面应该可以显示这个标题</h1>
    <h2 class="page-title">AllStarLink节点仪表盘</h2>
    
    <!-- 统计卡片 -->
    <div class="stats-cards">
      <stats-card 
        title="总节点数" 
        :count="globalStats.totalNodes" 
        icon="el-icon-data-line"
        color="#409EFF"
      />
      <stats-card 
        title="活跃节点数" 
        :count="globalStats.activeNodes" 
        icon="el-icon-video-camera"
        color="#67C23A"
      />
      <stats-card 
        title="活跃比例" 
        :count="globalStats.activePercentage" 
        icon="el-icon-circle-check"
        color="#E6A23C"
        :is-percentage="true"
      />
      <stats-card 
        title="统计时间范围" 
        :count="timeRange" 
        icon="el-icon-time"
        color="#F56C6C"
        suffix="小时"
      />
    </div>

    <!-- 时间范围选择 -->
    <div class="time-range-selector">
      <el-select
        v-model="timeRange"
        placeholder="选择时间范围"
        size="small"
        @change="handleTimeRangeChange"
      >
        <el-option label="最近1小时" value="1" />
        <el-option label="最近24小时" value="24" />
        <el-option label="最近3天" value="72" />
        <el-option label="最近7天" value="168" />
        <el-option label="自定义..." value="custom" />
      </el-select>
      
      <!-- 自定义时间范围输入 -->
      <div v-if="timeRange === 'custom'" class="custom-time-input">
        <el-input-number
          v-model="customTimeRange"
          :min="1"
          :max="8760"
          size="small"
          placeholder="请输入小时数"
        ></el-input-number>
        <el-button type="primary" size="small" @click="handleCustomTimeApply">
          应用
        </el-button>
      </div>
    </div>

    <!-- 地图区域（使用高德地图） -->
    <div class="map-container">
      <el-card shadow="hover" style="height: 100%; display: flex; flex-direction: column;">
        <template #header>
          <div class="card-header">
            <span>节点分布地图</span>
          </div>
        </template>
        <div style="flex: 1;">
          <amap :location-stats="locationStats" style="width: 100%; height: 100%;" />
        </div>
      </el-card>
    </div>

    <!-- 统计图表 -->
    <div class="charts-container">
      <el-card shadow="hover" class="chart-card">
        <template #header>
          <div class="card-header">
            <span>按国家节点统计</span>
          </div>
        </template>
        <div class="chart-wrapper">
          <v-chart :option="countryChartOption" autoresize />
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import StatsCard from '../components/StatsCard.vue'
import Amap from '../components/Amap.vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, PieChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  GridComponent,
  DatasetComponent,
  TransformComponent,
  LegendComponent
} from 'echarts/components'
import { getGlobalStats, getNodeStatsByCountry, getAllNodes, getNodeStatsByLocation } from '../utils/api'

// 注册 ECharts 组件
use([
  CanvasRenderer,
  BarChart,
  PieChart,
  TitleComponent,
  TooltipComponent,
  GridComponent,
  DatasetComponent,
  TransformComponent,
  LegendComponent
])

// 全局统计数据
const globalStats = reactive({
  totalNodes: 0,
  activeNodes: 0,
  activePercentage: 0
})

// 节点数据
const nodes = ref([])
// 国家统计数据
const countryStats = ref([])
// 位置统计数据，用于地图展示
const locationStats = ref([])
// 时间范围（小时）
const timeRange = ref(1)
// 自定义时间范围（小时）
const customTimeRange = ref(24) // 默认24小时

// 国家图表配置
const countryChartOption = ref({
  title: {
    text: '节点分布（按国家）',
    left: 'center'
  },
  tooltip: {
    trigger: 'item',
    formatter: '{b}: {c} ({d}%)'
  },
  legend: {
    orient: 'vertical',
    left: 'left'
  },
  series: [
    {
      name: '节点数',
      type: 'pie',
      radius: '50%',
      data: [],
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowOffsetX: 0,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        }
      }
    }
  ]
})



// 获取数据
  const fetchData = async () => {
    try {
      console.log('开始获取数据...')
      // 获取全局统计
      console.log('正在获取全局统计...')
      const stats = await getGlobalStats(timeRange.value)
      console.log('获取全局统计成功，数据类型:', typeof stats)
      // 检查数据格式 - 如果是对象，直接使用；如果是包含value字段的对象，使用value
      const actualStats = stats.value ? stats.value : stats
      console.log('实际全局统计数据:', actualStats)
      Object.assign(globalStats, actualStats)

      // 获取国家统计
      console.log('正在获取国家统计...')
      const countryData = await getNodeStatsByCountry(timeRange.value)
      console.log('获取国家统计成功，数据类型:', typeof countryData)
      console.log('国家统计数据结构:', JSON.stringify(Object.keys(countryData)))
      
      // 检查数据格式 - 后端返回的是对象，包含value数组和Count字段
      const actualCountryData = Array.isArray(countryData) ? countryData : countryData.value || []
      console.log('实际国家数据类型:', typeof actualCountryData, '实际数据长度:', actualCountryData.length)
      console.log('国家统计数据示例:', actualCountryData.slice(0, 5))
      
      countryStats.value = actualCountryData
      updateCountryChart()
      console.log('countryStats.value已更新，长度:', countryStats.value.length)

      // 获取位置统计数据，用于地图展示
      console.log('正在获取位置统计数据...')
      try {
        const locationData = await getNodeStatsByLocation(timeRange.value)
        console.log('获取位置统计数据成功，数据类型:', typeof locationData)
        console.log('位置统计数据完整内容:', locationData)
        
        // 检查数据格式
        const actualLocationData = Array.isArray(locationData) ? locationData : locationData.value || []
        console.log('实际位置数据类型:', typeof actualLocationData, '实际数据长度:', actualLocationData.length)
        console.log('位置统计数据示例:', actualLocationData.slice(0, 5))
        
        locationStats.value = actualLocationData
        console.log('locationStats.value已更新，长度:', locationStats.value.length)
      } catch (error) {
        console.error('获取位置统计数据失败:', error)
        console.error('错误详情:', error.response)
      }

      // 获取所有节点数据 - 只获取前100条用于展示，避免数据量太大
      console.log('正在获取所有节点数据...')
      const allNodes = await getAllNodes()
      nodes.value = allNodes.slice(0, 100) // 只获取前100条
      console.log('获取所有节点数据成功，已过滤为前100条用于展示')

      console.log('数据获取完成')
    } catch (error) {
      console.error('获取数据失败:', error)
      console.error('错误详情:', error.response)
    }
  }

// 更新国家图表
const updateCountryChart = () => {
  const pieData = countryStats.value
    .map(item => ({
      name: item.country || '未知',
      value: item.totalNodes
    }))
  
  countryChartOption.value.series[0].data = pieData
}



// 处理时间范围变化
const handleTimeRangeChange = () => {
  // 如果选择的是预设值（不是custom），直接重新获取数据
  if (timeRange.value !== 'custom') {
    fetchData()
  }
}

// 应用自定义时间范围
const handleCustomTimeApply = () => {
  if (customTimeRange.value && customTimeRange.value >= 1 && customTimeRange.value <= 8760) {
    // 将自定义时间范围转换为字符串，确保类型一致
    timeRange.value = customTimeRange.value.toString()
    fetchData()
  } else {
    // 如果输入无效，重置到默认值
    customTimeRange.value = 24
    timeRange.value = 'custom'
  }
}

// 页面加载时获取数据
onMounted(() => {
  console.log('HomeView mounted, fetching data...')
  fetchData()
})
</script>

<style scoped>
.home-container {
  padding: 0 20px;
}

.page-title {
  font-size: 24px;
  margin-bottom: 20px;
  color: #303133;
}

/* 统计卡片 */
.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
}

/* 地图容器 */
.map-container {
  margin-bottom: 20px;
  height: 600px;
}

/* 图表容器 */
.charts-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
  gap: 20px;
}

.chart-card {
  height: 400px;
}

.chart-wrapper {
  height: calc(100% - 44px); /* 减去卡片头部高度 */
}

/* 时间范围选择器 */
.time-range-selector {
  margin: 20px 0;
  padding: 15px;
  background-color: #f5f7fa;
  border-radius: 8px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.custom-time-input {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .stats-cards {
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  }
  
  .charts-container {
    grid-template-columns: 1fr;
  }
  
  .map-container {
    height: 400px;
  }
  
  .time-range-selector {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .custom-time-input {
    width: 100%;
  }
}
</style>