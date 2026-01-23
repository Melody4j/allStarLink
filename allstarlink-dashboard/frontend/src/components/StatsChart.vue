<template>
  <div class="stats-chart-container">
    <el-card shadow="hover">
      <template #header>
        <div class="chart-header">
          <h3>全球节点分布统计</h3>
          <el-radio-group
            v-model="currentDimension"
            size="small"
            @change="handleDimensionChange"
          >
            <el-radio-button label="continent">按大洲</el-radio-button>
            <el-radio-button label="country">按国家</el-radio-button>
          </el-radio-group>
        </div>
      </template>

      <div
        ref="chartContainer"
        class="chart-wrapper"
        v-loading="isLoading"
        element-loading-text="加载统计数据中..."
        element-loading-background="rgba(255, 255, 255, 0.8)"
      />

      <!-- 统计信息 -->
      <div class="chart-summary">
        <el-row :gutter="16">
          <el-col :span="6">
            <el-statistic
              title="总节点数"
              :value="globalStats.totalNodes || 0"
              suffix="个"
            />
          </el-col>
          <el-col :span="6">
            <el-statistic
              title="在线节点"
              :value="globalStats.activeNodes || 0"
              :value-style="{ color: '#67C23A' }"
              suffix="个"
            />
          </el-col>
          <el-col :span="6">
            <el-statistic
              title="全球活跃率"
              :value="globalStats.globalActiveRate || 0"
              :precision="2"
              :value-style="{ color: '#409EFF' }"
              suffix="%"
            />
          </el-col>
          <el-col :span="6">
            <el-statistic
              :title="currentDimension === 'continent' ? '覆盖大洲' : '覆盖国家'"
              :value="currentDimension === 'continent' ?
                (globalStats.activeContinents || 0) :
                (globalStats.activeCountries || 0)"
              :value-style="{ color: '#E6A23C' }"
              suffix="个"
            />
          </el-col>
        </el-row>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useMapStore } from '@/stores/mapStore'
import { useStats } from '@/composables/useStats'
import {
  ElCard,
  ElRadioGroup,
  ElRadioButton,
  ElRow,
  ElCol,
  ElStatistic
} from 'element-plus'

// Props & Emits
const props = defineProps({
  onRegionClick: {
    type: Function,
    default: null
  }
})

const emit = defineEmits(['regionClick'])

const chartContainer = ref()
const mapStore = useMapStore()

const {
  initializeChart,
  updateChartData,
  resizeChart,
  destroyChart,
  isLoading,
  currentDimension,
  globalStats
} = useStats()

// 处理维度切换
const handleDimensionChange = async (dimension) => {
  mapStore.switchStatsDimension(dimension)
  await updateChartData(dimension)
}

// 监听图表点击事件
const handleChartClick = (regionName) => {
  if (props.onRegionClick) {
    props.onRegionClick(regionName, currentDimension.value)
  }
  emit('regionClick', regionName, currentDimension.value)
}

onMounted(async () => {
  if (chartContainer.value) {
    await initializeChart(chartContainer.value, handleChartClick)

    // 监听窗口大小变化
    window.addEventListener('resize', resizeChart)
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeChart)
  destroyChart()
})

// 注释掉可能导致循环调用的watch监听器
// 图表数据更新已通过 updateChartData 方法直接处理
// watch(
//   () => mapStore.distributionStats,
//   (newStats) => {
//     updateChartData(currentDimension.value)
//   },
//   { deep: true }
// )
</script>

<style scoped>
.stats-chart-container {
  width: 100%;
  margin-bottom: 20px;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.chart-header h3 {
  margin: 0;
  color: #303133;
  font-size: 18px;
}

.chart-wrapper {
  width: 100%;
  height: 400px;
  min-height: 300px;
}

.chart-summary {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #EBEEF5;
}

/* 深度定制 Element Plus 组件样式 */
:deep(.el-statistic__head) {
  font-size: 14px;
  color: #909399;
  margin-bottom: 5px;
}

:deep(.el-statistic__content) {
  font-size: 18px;
  font-weight: bold;
}

:deep(.el-card__header) {
  padding: 18px 20px;
  border-bottom: 1px solid #EBEEF5;
}

:deep(.el-card__body) {
  padding: 20px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .chart-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .chart-header h3 {
    font-size: 16px;
  }

  .chart-wrapper {
    height: 300px;
  }

  .chart-summary :deep(.el-col) {
    margin-bottom: 15px;
  }

  :deep(.el-statistic__content) {
    font-size: 16px;
  }

  :deep(.el-radio-group) {
    flex-wrap: wrap;
  }
}

@media (max-width: 480px) {
  .chart-summary :deep(.el-row) {
    display: flex;
    flex-direction: column;
  }

  .chart-summary :deep(.el-col) {
    width: 100% !important;
    text-align: center;
    margin-bottom: 10px;
  }
}

/* 加载状态样式 */
.chart-wrapper[v-loading] {
  position: relative;
}
</style>