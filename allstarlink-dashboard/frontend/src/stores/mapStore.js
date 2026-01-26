import { defineStore } from 'pinia'
import { ref, shallowRef } from 'vue'

export const useMapStore = defineStore('map', () => {
  // ======================= 地图相关状态 =======================

  /**
   * 地图实例 (shallowRef 避免深度响应式追踪)
   */
  const mapInstance = shallowRef(null)

  /**
   * 标注图层实例
   */
  const labelsLayer = shallowRef(null)

  /**
   * 信息窗体实例 (单例复用)
   */
  const infoWindow = shallowRef(null)

  /**
   * 当前地图节点数据
   */
  const mapNodes = shallowRef([])

  /**
   * 全量节点索引（用于低缩放级别的抽稀）
   */
  const fullNodeIndex = shallowRef([])

  /**
   * 全量地图节点（用于前端地图展示，包含所有经纬度不为0的节点）
   */
  const fullMapNodes = shallowRef([])

  /**
   * 分级缓存（用于中等缩放级别）
   */
  const levelCache = shallowRef({})

  /**
   * 当前选中的节点
   */
  const selectedNode = ref(null)

  /**
   * 地图加载状态
   */
  const isMapLoading = ref(false)

  /**
   * 当前可视区域边界
   */
  const currentBounds = ref({
    minLng: 0,
    maxLng: 0,
    minLat: 0,
    maxLat: 0,
    zoomLevel: 2
  })

  // ======================= 统计数据相关状态 =======================

  /**
   * 分布统计数据
   */
  const distributionStats = ref([])

  /**
   * 当前统计维度
   */
  const statsDimension = ref('continent')

  /**
   * 全球统计概览
   */
  const globalStats = ref({
    totalNodes: 0,
    activeNodes: 0,
    globalActiveRate: 0,
    activeContinents: 0,
    activeCountries: 0,
    totalContinents: 0,
    totalCountries: 0
  })

  // ======================= Actions =======================

  /**
   * 设置地图实例
   */
  const setMapInstance = (map) => {
    mapInstance.value = map
  }

  /**
   * 设置标注图层
   */
  const setLabelsLayer = (layer) => {
    labelsLayer.value = layer
  }

  /**
   * 设置信息窗体
   */
  const setInfoWindow = (window) => {
    infoWindow.value = window
  }

  /**
   * 更新地图节点数据
   */
  const updateMapNodes = (nodes) => {
    mapNodes.value = nodes
  }

  /**
   * 设置选中节点
   */
  const setSelectedNode = (node) => {
    selectedNode.value = node
  }

  /**
   * 更新当前边界
   */
  const updateCurrentBounds = (bounds) => {
    currentBounds.value = bounds
  }

  /**
   * 更新分布统计数据
   */
  const updateDistributionStats = (stats) => {
    distributionStats.value = stats
  }

  /**
   * 切换统计维度
   */
  const switchStatsDimension = (dimension) => {
    statsDimension.value = dimension
  }

  /**
   * 更新全球统计
   */
  const updateGlobalStats = (stats) => {
    globalStats.value = stats
  }

  return {
    // State
    mapInstance,
    labelsLayer,
    infoWindow,
    mapNodes,
    selectedNode,
    isMapLoading,
    currentBounds,
    distributionStats,
    statsDimension,
    globalStats,
    fullNodeIndex,
    fullMapNodes,
    levelCache,

    // Actions
    setMapInstance,
    setLabelsLayer,
    setInfoWindow,
    updateMapNodes,
    setSelectedNode,
    updateCurrentBounds,
    updateDistributionStats,
    switchStatsDimension,
    updateGlobalStats
  }
})