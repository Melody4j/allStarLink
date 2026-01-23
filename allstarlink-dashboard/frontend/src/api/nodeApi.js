import axios from 'axios'

// 创建axios实例
const apiClient = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 响应拦截器
apiClient.interceptors.response.use(
  response => {
    // 如果后端返回统一格式 { code, message, data }，则提取data
    if (response.data && typeof response.data === 'object' && 'code' in response.data) {
      if (response.data.code === 200) {
        return response.data.data
      } else {
        return Promise.reject(new Error(response.data.message || '请求失败'))
      }
    }
    // 兼容原来的直接返回数据格式
    return response.data
  },
  error => {
    console.error('API请求错误:', error)
    return Promise.reject(error)
  }
)

/**
 * 节点API类
 */
class NodeApi {
  /**
   * 获取地图边界内的节点数据
   * @param {Object} params - 查询参数
   * @param {number} params.minLng - 最小经度
   * @param {number} params.maxLng - 最大经度
   * @param {number} params.minLat - 最小纬度
   * @param {number} params.maxLat - 最大纬度
   * @param {number} params.zoomLevel - 缩放级别
   * @returns {Promise<Array>} 地图节点列表
   */
  async getMapNodesByBounds(params) {
    const response = await apiClient.get('/api/nodes/map/bounds', { params })
    return response
  }

  /**
   * 统计边界内节点数量
   * @param {Object} params - 查询参数
   * @returns {Promise<number>} 节点总数
   */
  async countNodesByBounds(params) {
    const response = await apiClient.get('/api/nodes/map/bounds/count', { params })
    return response
  }

  /**
   * 分页查询节点列表
   * @param {Object} params - 分页查询参数
   * @returns {Promise<Object>} 分页结果
   */
  async getNodeListByPage(params) {
    const response = await apiClient.get('/api/nodes/list', { params })
    return response
  }

  /**
   * 根据节点ID获取详情
   * @param {number} nodeId - 节点ID
   * @returns {Promise<Object>} 节点详情
   */
  async getNodeById(nodeId) {
    const response = await apiClient.get(`/api/nodes/${nodeId}`)
    return response
  }

  /**
   * 获取分布统计数据
   * @param {string} dimension - 统计维度：'continent' 或 'country'
   * @returns {Promise<Array>} 分布统计列表
   */
  async getDistribution(dimension) {
    const response = await apiClient.get('/api/stats/distribution', {
      params: { dimension }
    })
    return response
  }

  /**
   * 获取大洲分布统计
   * @returns {Promise<Array>} 大洲分布统计列表
   */
  async getDistributionByContinent() {
    const response = await apiClient.get('/api/stats/distribution/continent')
    return response
  }

  /**
   * 获取国家分布统计
   * @returns {Promise<Array>} 国家分布统计列表
   */
  async getDistributionByCountry() {
    const response = await apiClient.get('/api/stats/distribution/country')
    return response
  }

  /**
   * 获取全球统计概览
   * @returns {Promise<Object>} 全球统计信息
   */
  async getStatsOverview() {
    const response = await apiClient.get('/api/stats/overview')
    return response
  }

  /**
   * 获取全球节点统计
   * @returns {Promise<Object>} 全球统计信息
   */
  async getGlobalStats() {
    const response = await apiClient.get('/api/stats/global')
    return response
  }

  /**
   * 服务健康检查
   * @returns {Promise<string>} 健康状态信息
   */
  async healthCheck() {
    const response = await apiClient.get('/api/nodes/health')
    return response
  }
}

// 创建实例并导出
export const nodeApi = new NodeApi()

// 为了向后兼容，也导出单独的函数
export const getMapNodesByBounds = (params) => nodeApi.getMapNodesByBounds(params)
export const countNodesByBounds = (params) => nodeApi.countNodesByBounds(params)
export const getNodeListByPage = (params) => nodeApi.getNodeListByPage(params)
export const getNodeById = (nodeId) => nodeApi.getNodeById(nodeId)
export const getDistribution = (dimension) => nodeApi.getDistribution(dimension)
export const getDistributionByContinent = () => nodeApi.getDistributionByContinent()
export const getDistributionByCountry = () => nodeApi.getDistributionByCountry()
export const getStatsOverview = () => nodeApi.getStatsOverview()
export const getGlobalStats = () => nodeApi.getGlobalStats()
export const healthCheck = () => nodeApi.healthCheck()

// 兼容性：保留原有的API函数名
export const getAllNodes = () => nodeApi.getNodeListByPage({ current: 1, size: 10000 })
export const getActiveNodes = () => nodeApi.getMapNodesByBounds({
  minLng: -180, maxLng: 180, minLat: -90, maxLat: 90, zoomLevel: 2
})
export const getLimitedActiveNodes = (limit = 500) => nodeApi.getMapNodesByBounds({
  minLng: -180, maxLng: 180, minLat: -90, maxLat: 90, zoomLevel: 2
})
export const getNodeStatsByLocation = () => nodeApi.getDistributionByCountry()