<template>
  <div class="stats-container">
    <h2 class="page-title">节点统计分析</h2>

    <!-- 统计选项 -->
    <div class="stats-options">
      <el-select v-model="timeRange" placeholder="选择时间范围" class="time-select">
        <el-option label="1小时" value="1"></el-option>
        <el-option label="6小时" value="6"></el-option>
        <el-option label="12小时" value="12"></el-option>
        <el-option label="24小时" value="24"></el-option>
        <el-option label="7天" value="168"></el-option>
      </el-select>
      <el-button type="primary" @click="fetchData">刷新数据</el-button>
    </div>

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
    </div>

    <!-- 图表区域 -->
    <div class="charts-area">
      <!-- 活跃节点趋势（模拟数据） -->
      <el-card shadow="hover" class="chart-card full-width">
        <template #header>
          <div class="card-header">
            <span>活跃节点趋势</span>
          </div>
        </template>
        <div class="chart-wrapper">
          <v-chart :option="activeTrendChart" autoresize />
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import StatsCard from '../components/StatsCard.vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart, LineChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  GridComponent,
  DatasetComponent,
  TransformComponent,
  LegendComponent
} from 'echarts/components'
import { getGlobalStats } from '../utils/api'

// 注册 ECharts 组件
use([
  CanvasRenderer,
  BarChart,
  PieChart,
  LineChart,
  TitleComponent,
  TooltipComponent,
  GridComponent,
  DatasetComponent,
  TransformComponent,
  LegendComponent
])

// 时间范围
const timeRange = ref(1)

// 全局统计数据
const globalStats = reactive({
  totalNodes: 0,
  activeNodes: 0,
  activePercentage: 0
})

// 活跃节点趋势图配置（模拟数据）
const activeTrendChart = ref({
  title: {
    text: '活跃节点趋势',
    left: 'center'
  },
  tooltip: {
    trigger: 'axis'
  },
  legend: {
    data: ['活跃节点数'],
    bottom: 0
  },
  grid: {
    left: '3%',
    right: '4%',
    bottom: '15%',
    containLabel: true
  },
  xAxis: {
    type: 'category',
    boundaryGap: false,
    data: []
  },
  yAxis: {
    type: 'value'
  },
  series: [
    {
      name: '活跃节点数',
      type: 'line',
      stack: 'Total',
      data: [],
      smooth: true,
      lineStyle: {
        color: '#67C23A'
      },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [{
            offset: 0, color: 'rgba(103, 194, 58, 0.8)'
          }, {
            offset: 1, color: 'rgba(103, 194, 58, 0.1)'
          }]
        }
      }
    }
  ]
})

// 获取数据
    const fetchData = async () => {
      try {
        // 获取全局统计
        const stats = await getGlobalStats(timeRange.value)
        Object.assign(globalStats, stats)

        // 更新趋势图（模拟数据）
        updateActiveTrendChart()

      } catch (error) {
        console.error('获取统计数据失败:', error)
      }
    }

// 更新活跃节点趋势图（模拟数据）
const updateActiveTrendChart = () => {
  // 模拟时间数据
  const hours = Array.from({ length: 24 }, (_, i) => `${i}:00`)
  // 模拟节点数据（基于当前活跃节点数）
  const nodeCounts = hours.map(() => Math.floor(globalStats.activeNodes * (0.8 + Math.random() * 0.4)))
  
  activeTrendChart.value.xAxis.data = hours
  activeTrendChart.value.series[0].data = nodeCounts
}

// 页面加载时获取数据
onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.stats-container {
  padding: 0 20px;
}

.page-title {
  font-size: 24px;
  margin-bottom: 20px;
  color: #303133;
}

/* 统计选项 */
.stats-options {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}

.time-select {
  width: 150px;
  margin-right: 20px;
}

/* 统计卡片 */
.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
}

/* 图表区域 */
.charts-area {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
  gap: 20px;
}

.chart-card {
  height: 400px;
}

.chart-card.full-width {
  grid-column: 1 / -1;
}

.chart-wrapper {
  height: calc(100% - 44px);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .charts-area {
    grid-template-columns: 1fr;
  }
  
  .chart-card {
    height: 300px;
  }
}
</style>