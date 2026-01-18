import { defineStore } from 'pinia'

// 定义全局状态管理
const useAppStore = defineStore('app', {
  state: () => ({
    // 时间范围（小时）
    timeRange: 1,
    // 全局统计数据
    globalStats: {
      totalNodes: 0,
      activeNodes: 0,
      activePercentage: 0
    },
    // 节点数据
    nodes: [],
    // 国家统计数据
    countryStats: [],
    // 位置统计数据
    locationStats: []
  }),

  getters: {
    // 时间范围标签
    timeRangeLabel: (state) => {
      const hours = state.timeRange
      if (hours === 1) return '最近1小时'
      if (hours === 24) return '最近24小时'
      if (hours === 72) return '最近3天'
      if (hours === 168) return '最近7天'
      return `最近${hours}小时`
    }
  },

  actions: {
    // 更新时间范围
    updateTimeRange(hours) {
      this.timeRange = hours
    },

    // 更新全局统计数据
    updateGlobalStats(stats) {
      this.globalStats = stats
    },

    // 更新节点数据
    updateNodes(nodes) {
      this.nodes = nodes
    },

    // 更新国家统计数据
    updateCountryStats(stats) {
      this.countryStats = stats
    },

    // 更新位置统计数据
    updateLocationStats(stats) {
      this.locationStats = stats
    }
  }
})

export default useAppStore