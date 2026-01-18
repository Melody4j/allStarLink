import axios from 'axios'

// 创建axios实例
const apiClient = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 响应拦截器
apiClient.interceptors.response.use(
  response => response.data,
  error => {
    console.error('API请求错误:', error)
    return Promise.reject(error)
  }
)

// API接口定义

// 获取全局统计信息
export const getGlobalStats = (timeThresholdHours = 1) => {
  return apiClient.get(`/stats/global?timeThresholdHours=${timeThresholdHours}`)
}

// 获取按国家分组的节点统计
export const getNodeStatsByCountry = (timeThresholdHours = 1) => {
  return apiClient.get(`/stats/country?timeThresholdHours=${timeThresholdHours}`)
}

// 获取按位置分组的节点统计
export const getNodeStatsByLocation = (timeThresholdHours = 1) => {
  return apiClient.get(`/stats/location?timeThresholdHours=${timeThresholdHours}`)
}

// 获取所有节点
export const getAllNodes = () => {
  return apiClient.get('/nodes')
}

// 分页获取节点
export const getNodesByPage = (pageNum = 1, pageSize = 20) => {
  return apiClient.get(`/nodes/page?pageNum=${pageNum}&pageSize=${pageSize}`)
}

// 获取所有活跃节点
export const getActiveNodes = () => {
  return apiClient.get('/nodes/active')
}

// 根据节点ID获取节点
export const getNodeById = (nodeId) => {
  return apiClient.get(`/nodes/${nodeId}`)
}

// 根据位置查询节点
export const searchNodesByLocation = (location) => {
  return apiClient.get(`/nodes/search?location=${encodeURIComponent(location)}`)
}

// 根据地理范围查询节点
export const getNodesByGeoBounds = (minLat, maxLat, minLon, maxLon) => {
  return apiClient.get(`/nodes/geo?minLat=${minLat}&maxLat=${maxLat}&minLon=${minLon}&maxLon=${maxLon}`)
}

// 地理编码服务（将位置文本转换为经纬度）
export const geocodeLocation = (location) => {
  // 使用OpenStreetMap Nominatim API进行地理编码
  const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(location)}&format=json&limit=1`
  return axios.get(url, { timeout: 10000 })
}
