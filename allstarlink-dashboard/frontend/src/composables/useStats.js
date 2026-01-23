import { ref, computed } from 'vue'
import * as echarts from 'echarts'
import { useMapStore } from '@/stores/mapStore'
import { nodeApi } from '@/api/nodeApi'
import { ElMessage } from 'element-plus'

/**
 * 统计图表功能 Composable
 */
export function useStats() {
  const mapStore = useMapStore()

  let chartInstance = null
  const isLoading = ref(false)

  // 当前统计维度
  const currentDimension = ref('continent')

  // 全球统计数据
  const globalStats = computed(() => mapStore.globalStats)

  /**
   * 初始化 ECharts 图表
   */
  const initializeChart = async (container, onRegionClick) => {
    try {
      // 创建图表实例
      chartInstance = echarts.init(container)

      // 绑定点击事件
      if (onRegionClick) {
        chartInstance.on('click', (params) => {
          if (params.name) {
            onRegionClick(params.name)
          }
        })
      }

      // 加载初始数据
      await loadStatsData('continent')
      await loadGlobalStats()

      console.log('📊 ECharts 统计图表初始化完成')
    } catch (error) {
      console.error('图表初始化失败:', error)
      ElMessage.error('统计图表加载失败')
    }
  }

  /**
   * 加载统计数据
   */
  const loadStatsData = async (dimension) => {
    try {
      isLoading.value = true

      const stats = await nodeApi.getDistribution(dimension)
      mapStore.updateDistributionStats(Array.isArray(stats) ? stats : [])

      currentDimension.value = dimension
      renderChart(Array.isArray(stats) ? stats : [])
    } catch (error) {
      console.error('加载统计数据失败:', error)
      ElMessage.error('统计数据加载失败')
      // 设置空数据以避免图表崩溃
      mapStore.updateDistributionStats([])
      renderChart([])
    } finally {
      isLoading.value = false
    }
  }

  /**
   * 加载全球统计概览
   */
  const loadGlobalStats = async () => {
    try {
      const stats = await nodeApi.getStatsOverview()
      if (stats) {
        mapStore.updateGlobalStats(stats)
      }
    } catch (error) {
      console.error('加载全球统计失败:', error)
    }
  }

  /**
   * 渲染图表
   */
  const renderChart = (stats) => {
    if (!chartInstance) return

    const option = {
      title: {
        text: currentDimension.value === 'continent' ? '按大洲分布' : '按国家分布',
        left: 'center',
        top: 20,
        textStyle: {
          fontSize: 16,
          color: '#303133'
        }
      },

      tooltip: {
        trigger: 'item',
        formatter: (params) => {
          const data = params.data
          return `
            <div>
              <strong>${data.name}</strong><br/>
              总节点: ${data.totalCount || 0}<br/>
              活跃节点: ${data.activeCount || 0}<br/>
              活跃率: ${data.activeRate || 0}%<br/>
              占比: ${data.percentage || 0}%
            </div>
          `
        }
      },

      legend: {
        orient: 'vertical',
        left: 'left',
        top: 'middle',
        icon: 'circle',
        itemWidth: 10,
        itemHeight: 10,
        textStyle: {
          fontSize: 12
        }
      },

      series: [
        {
          name: '节点分布',
          type: 'pie',
          radius: ['40%', '70%'],
          center: ['60%', '50%'],
          avoidLabelOverlap: true,
          itemStyle: {
            borderRadius: 8,
            borderColor: '#fff',
            borderWidth: 2
          },
          label: {
            show: true,
            position: 'outside',
            formatter: '{b}\n{c} 个\n({d}%)',
            fontSize: 10
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 14,
              fontWeight: 'bold'
            },
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.5)'
            }
          },
          data: stats.map((item, index) => ({
            name: item.dimensionName || '未知',
            value: item.totalCount || 0,
            totalCount: item.totalCount || 0,
            activeCount: item.activeCount || 0,
            activeRate: item.activeRate || 0,
            percentage: item.percentage || 0,
            itemStyle: {
              color: getRegionColor(index)
            }
          }))
        }
      ]
    }

    chartInstance.setOption(option, true)
  }

  /**
   * 获取区域颜色
   */
  const getRegionColor = (index) => {
    const colors = [
      '#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de',
      '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc', '#5fb3d4',
      '#b6a2de', '#2fc25b', '#ffdb5c', '#ff9f7f', '#fb7293'
    ]
    return colors[index % colors.length]
  }

  /**
   * 更新图表数据
   */
  const updateChartData = async (dimension) => {
    await loadStatsData(dimension)
  }

  /**
   * 调整图表大小
   */
  const resizeChart = () => {
    if (chartInstance) {
      chartInstance.resize()
    }
  }

  /**
   * 销毁图表
   */
  const destroyChart = () => {
    if (chartInstance) {
      chartInstance.dispose()
      chartInstance = null
    }
  }

  return {
    initializeChart,
    updateChartData,
    resizeChart,
    destroyChart,
    isLoading,
    currentDimension,
    globalStats
  }
}