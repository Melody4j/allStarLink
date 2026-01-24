import { nextTick } from 'vue'
import { useMapStore } from '@/stores/mapStore'
import { nodeApi } from '@/api/nodeApi'
import { debounce } from 'lodash-es'
import { ElMessage } from 'element-plus'

/**
 * 地图功能 Composable
 */
export function useMap() {
  const mapStore = useMapStore()

  /**
   * 初始化高德地图
   */
  const initializeMap = async (container) => {
    try {
      // 动态加载高德地图 API
      const AMapLoader = (await import('@amap/amap-jsapi-loader')).default

      const AMap = await AMapLoader.load({
        key: '2d608fb0a4f54f0bf39462b10bb7dce3', // 从后端代码中获取的key
        version: '2.0',
        plugins: ['AMap.Scale', 'AMap.ToolBar', 'AMap.MouseTool']
      })

      // 创建地图实例
      const map = new AMap.Map(container, {
        zoom: 2,
        center: [116.397428, 39.90923],
        mapStyle: 'amap://styles/normal',
        viewMode: '3D',
        showLabel: true,
        features: ['bg', 'road', 'building', 'point']
      })

      // 创建标注图层 (Canvas 模式)
      const labelsLayer = new AMap.LabelsLayer({
        zIndex: 1000,
        collision: false, // 暂时关闭避让，确保所有节点都显示
        allowCollision: true
      })

      // 创建信息窗体 (单例复用)
      const infoWindow = new AMap.InfoWindow({
        anchor: 'bottom-center',
        offset: [0, -20],
        autoMove: true,
        closeWhenClickMap: true
      })

      // 添加图层到地图
      map.add(labelsLayer)

      // 保存到 Store
      mapStore.setMapInstance(map)
      mapStore.setLabelsLayer(labelsLayer)
      mapStore.setInfoWindow(infoWindow)

      // 绑定地图事件
      bindMapEvents(map)

      // 初始加载数据
      await loadInitialNodes(map)

      console.log('🗺️ 高德地图初始化完成 - 使用样式:', map.getMapStyle())
    } catch (error) {
      console.error('地图初始化失败:', error)
      ElMessage.error('地图加载失败，请刷新页面重试')
    }
  }

  /**
   * 绑定地图事件
   */
  const bindMapEvents = (map) => {
    // 防抖加载函数
    const debouncedLoad = debounce(async () => {
      await loadNodesInBounds(map)
    }, 300)

    // 监听地图移动结束事件
    map.on('moveend', debouncedLoad)

    // 监听地图缩放结束事件
    map.on('zoomend', debouncedLoad)

    // 监听地图完成事件
    map.on('complete', debouncedLoad)
  }

  /**
   * 加载初始节点数据
   */
  const loadInitialNodes = async (map) => {
    const bounds = map.getBounds()
    if (bounds) {
      const sw = bounds.getSouthWest()
      const ne = bounds.getNorthEast()

      const boundsQuery = {
        minLng: Math.max(-180, Math.min(180, sw.lng)),
        maxLng: Math.max(-180, Math.min(180, ne.lng)),
        minLat: Math.max(-90, Math.min(90, sw.lat)),
        maxLat: Math.max(-90, Math.min(90, ne.lat)),
        zoomLevel: Math.round(Math.max(1, Math.min(18, map.getZoom())))
      }

      await loadNodesData(boundsQuery)
    }
  }

  /**
   * 根据当前地图边界加载节点
   */
  const loadNodesInBounds = async (map) => {
    let bounds
    try {
      bounds = map.getBounds()
    } catch (error) {
      console.warn('获取地图边界失败:', error)
      return
    }
    if (!bounds) return

    const sw = bounds.getSouthWest()
    const ne = bounds.getNorthEast()
    const zoom = map.getZoom()

    const boundsQuery = {
      minLng: Math.max(-180, Math.min(180, sw.lng)),
      maxLng: Math.max(-180, Math.min(180, ne.lng)),
      minLat: Math.max(-90, Math.min(90, sw.lat)),
      maxLat: Math.max(-90, Math.min(90, ne.lat)),
      zoomLevel: Math.round(Math.max(1, Math.min(18, zoom)))
    }

    // 更新当前边界到 Store
    mapStore.updateCurrentBounds(boundsQuery)

    await loadNodesData(boundsQuery)
  }

  /**
   * 请求节点数据并渲染
   */
  const loadNodesData = async (query) => {
    try {
      mapStore.isMapLoading = true

      const nodes = await nodeApi.getMapNodesByBounds(query)

      // 更新 Store 中的节点数据
      mapStore.updateMapNodes(Array.isArray(nodes) ? nodes : [])

      // 重新渲染标记
      await createNodeMarkers(Array.isArray(nodes) ? nodes : [])

      console.log(`🎯 加载了 ${nodes?.length || 0} 个节点 (缩放级别: ${query.zoomLevel})`)
    } catch (error) {
      console.error('加载节点数据失败:', error)
      ElMessage.error('节点数据加载失败')
    } finally {
      mapStore.isMapLoading = false
    }
  }

  /**
   * 创建节点标记 (使用定位图标)
   */
  const createNodeMarkers = async (nodes) => {
    const { mapInstance, labelsLayer } = mapStore
    if (!labelsLayer || !mapInstance) return

    // 清理旧的直接标记
    if (mapStore.directMarkers) {
      mapStore.directMarkers.forEach(marker => {
        mapInstance.remove(marker)
      })
      mapStore.directMarkers = []
    }

    // 清除LabelMarker层
    labelsLayer.clear()

    // 强制刷新图层渲染
    await new Promise(resolve => setTimeout(resolve, 50))

    if (!Array.isArray(nodes) || nodes.length === 0) {
      return
    }

    console.log(`🎨 开始创建 ${nodes.length} 个节点标记，使用新样式`)

    // 批量创建标记
    const markers = [] // LabelMarker数组（文本）
    const directMarkers = [] // 直接Marker数组（图标）

    nodes.forEach(node => {
      if (!node.longitude || !node.latitude) return

      // 根据节点状态选择颜色
      const color = getNodeColor(node)
      const size = getNodeSize(node)
      const strokeColor = getStrokeColor(node)

      // 创建定位图标样式的SVG
      const createLocationIcon = (fillColor, strokeColor, size) => {
        const svgSize = size * 2.5
        const shadowId = `shadow-${node.nodeId}-${Math.random().toString(36).substr(2, 9)}`
        return `
          <svg width="${svgSize}" height="${svgSize}" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <filter id="${shadowId}" x="-20%" y="-20%" width="140%" height="140%">
                <feDropShadow dx="1" dy="2" stdDeviation="2" flood-opacity="0.3"/>
              </filter>
            </defs>
            <!-- 定位图标主体 -->
            <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z"
                  fill="${fillColor}"
                  stroke="${strokeColor}"
                  stroke-width="2"
                  filter="url(#${shadowId})"/>
            <!-- 内部圆点 -->
            <circle cx="12" cy="9" r="2.5" fill="${strokeColor}" opacity="0.8"/>
          </svg>
        `.trim()
      }

      const svgIcon = createLocationIcon(color, strokeColor, size)

      // 使用Marker代替LabelMarker来支持自定义SVG图标
      const marker = new AMap.Marker({
        position: [node.longitude, node.latitude],
        content: `<div style="transform: translate(-50%, -100%); cursor: pointer;">${svgIcon}</div>`,
        zIndex: getNodeZIndex(node),
        anchor: 'bottom-center'
      })

      // 创建LabelMarker用于显示文本（如果需要的话）
      const textMarker = new AMap.LabelMarker({
        position: [node.longitude, node.latitude],
        zIndex: getNodeZIndex(node) - 1,
        // 添加唯一ID
        id: `text-${node.nodeId}-${Date.now()}-${Math.random()}`,
        icon: {
          type: 'circle',
          size: 1, // 极小的透明图标
          fillColor: 'transparent',
          fillOpacity: 0,
          strokeColor: 'transparent',
          strokeWidth: 0,
          anchor: 'center'
        },
        text: {
          content: node.callsign || node.nodeId?.toString() || '',
          direction: 'bottom',
          offset: [0, 15],
          style: {
            fontSize: 11,
            fontWeight: 'bold',
            fillColor: '#2c3e50',
            strokeColor: '#ffffff',
            strokeWidth: 3,
            fontFamily: 'Arial, sans-serif',
            textShadow: '1px 1px 2px rgba(0,0,0,0.3)'
          }
        }
      })

      // 绑定主图标的点击事件
      marker.on('click', () => {
        showNodeInfo(node, [node.longitude, node.latitude])
        mapStore.setSelectedNode(node)
      })

      // 绑定文本标记的点击事件
      textMarker.on('click', () => {
        showNodeInfo(node, [node.longitude, node.latitude])
        mapStore.setSelectedNode(node)
      })

      // 添加到地图（直接添加，不通过LabelLayer）
      mapInstance.add(marker)

      // 分别收集不同类型的标记
      directMarkers.push(marker) // 收集图标标记
      markers.push(textMarker) // 收集文本标记
    })

    // 批量添加到图层
    labelsLayer.add(markers)

    await nextTick()

    // 保存直接添加到地图的标记引用（用于下次清理）
    mapStore.directMarkers = directMarkers

    console.log(`📍 已创建 ${directMarkers.length} 个定位图标 + ${markers.length} 个文本标记`)
  }

  /**
   * 获取节点颜色
   */
  const getNodeColor = (node) => {
    if (!node.isActive) return '#BDC3C7' // 浅灰色-离线

    switch (node.nodeRank) {
      case 'Core': return '#FF6B35' // 鲜橙色-核心
      case 'Active': return '#00D084' // 鲜绿色-活跃
      case 'Transient': return '#3B82F6' // 鲜蓝色-临时
      default: return '#BDC3C7'
    }
  }

  /**
   * 获取节点大小
   */
  const getNodeSize = (node) => {
    if (!node.isActive) return 8

    switch (node.nodeRank) {
      case 'Core': return 14
      case 'Active': return 12
      case 'Transient': return 10
      default: return 8
    }
  }

  /**
   * 获取节点描边颜色
   */
  const getStrokeColor = (node) => {
    if (!node.isActive) return '#7F8C8D' // 深灰色描边-离线

    switch (node.nodeRank) {
      case 'Core': return '#E74C3C' // 红色描边-核心
      case 'Active': return '#27AE60' // 深绿色描边-活跃
      case 'Transient': return '#2980B9' // 深蓝色描边-临时
      default: return '#7F8C8D'
    }
  }

  /**
   * 获取节点层级
   */
  const getNodeZIndex = (node) => {
    if (!node.isActive) return 1

    switch (node.nodeRank) {
      case 'Core': return 100
      case 'Active': return 50
      case 'Transient': return 10
      default: return 1
    }
  }

  /**
   * 显示节点信息窗体
   */
  const showNodeInfo = (node, position) => {
    const { infoWindow } = mapStore
    if (!infoWindow) return

    const content = `
      <div class="node-info" style="padding: 10px; font-family: Arial, sans-serif;">
        <h4 style="margin: 0 0 10px 0; color: #333;">${node.callsign || node.nodeId}</h4>
        <div style="margin: 5px 0;">
          <span style="font-weight: bold;">状态:</span>
          <span style="color: ${node.isActive ? '#67C23A' : '#909399'};">
            ${node.isActive ? '在线' : '离线'}
          </span>
        </div>
        <div style="margin: 5px 0;">
          <span style="font-weight: bold;">等级:</span>
          <span>${node.nodeRank || '未知'}</span>
        </div>
        <div style="margin: 5px 0;">
          <span style="font-weight: bold;">类型:</span>
          <span>${node.affiliationType || '未知'}</span>
        </div>
        <div style="margin: 5px 0;">
          <span style="font-weight: bold;">位置:</span>
          <span>${node.country || '未知'}</span>
        </div>
        <div style="margin: 5px 0;">
          <span style="font-weight: bold;">坐标:</span>
          <span>${node.latitude?.toFixed(4) || 0}, ${node.longitude?.toFixed(4) || 0}</span>
        </div>
      </div>
    `

    infoWindow.setContent(content)
    infoWindow.open(mapStore.mapInstance, position)
  }

  /**
   * 平移到指定位置
   */
  const panToLocation = (longitude, latitude, zoom = 10) => {
    const { mapInstance } = mapStore
    if (!mapInstance) return

    mapInstance.setZoomAndCenter(zoom, [longitude, latitude])
  }

  /**
   * 创建测试标记 - 用于验证样式
   */
  const createTestMarkers = async () => {
    const { mapInstance, labelsLayer } = mapStore
    if (!labelsLayer || !mapInstance) return

    console.log('🧪 创建测试标记...')

    // 清除现有标记
    labelsLayer.clear()

    // 创建不同类型的测试节点 - 分散坐标避免重叠
    const testNodes = [
      { nodeId: 'TEST1', callsign: 'TEST-CORE', longitude: 116.0, latitude: 40.0, nodeRank: 'Core', isActive: true },
      { nodeId: 'TEST2', callsign: 'TEST-ACTIVE', longitude: 117.0, latitude: 40.0, nodeRank: 'Active', isActive: true },
      { nodeId: 'TEST3', callsign: 'TEST-TEMP', longitude: 116.0, latitude: 39.0, nodeRank: 'Transient', isActive: true },
      { nodeId: 'TEST4', callsign: 'TEST-OFF', longitude: 117.0, latitude: 39.0, nodeRank: 'Active', isActive: false }
    ]

    const markers = []

    testNodes.forEach(node => {
      const color = getNodeColor(node)
      const size = getNodeSize(node) + 5 // 稍大一些便于观察
      const strokeColor = getStrokeColor(node)

      console.log(`测试节点 ${node.callsign}: 颜色=${color}, 描边=${strokeColor}, 大小=${size}, 等级=${node.nodeRank}, 状态=${node.isActive}`)

      const marker = new AMap.LabelMarker({
        position: [node.longitude, node.latitude],
        zIndex: 9999, // 确保在最顶层
        id: `test-${node.nodeId}-${Date.now()}`,
        icon: {
          type: 'circle',
          size: size,
          fillColor: color,
          fillOpacity: 0.95,
          strokeColor: strokeColor,
          strokeWidth: 3,
          anchor: 'center'
        },
        text: {
          content: node.callsign,
          direction: 'bottom',
          offset: [0, 20],
          style: {
            fontSize: 12,
            fontWeight: 'bold',
            fillColor: '#000000',
            strokeColor: '#ffffff',
            strokeWidth: 2
          }
        }
      })

      markers.push(marker)
    })

    labelsLayer.add(markers)

    // 立即移动地图视野以查看测试节点
    mapInstance.setFitView(markers)

    console.log(`🧪 已创建 ${markers.length} 个测试标记，坐标分散显示`)
  }

  /**
   * 创建简单Marker测试 - 使用传统Marker而不是LabelMarker
   */
  const createSimpleTestMarkers = async () => {
    const { mapInstance } = mapStore
    if (!mapInstance) return

    console.log('🟡 创建简单Marker测试...')

    // 清除现有的LabelMarker层
    const { labelsLayer } = mapStore
    if (labelsLayer) {
      try {
        labelsLayer.clear()
      } catch (error) {
        console.warn('清除LabelMarker层时出错:', error)
      }
    }

    // 创建简单的测试标记
    const testMarkers = []

    const testNodes = [
      { callsign: 'CORE', longitude: 115.5, latitude: 40.5, nodeRank: 'Core', isActive: true },
      { callsign: 'ACTIVE', longitude: 117.5, latitude: 40.5, nodeRank: 'Active', isActive: true },
      { callsign: 'TEMP', longitude: 115.5, latitude: 38.5, nodeRank: 'Transient', isActive: true },
      { callsign: 'OFF', longitude: 117.5, latitude: 38.5, nodeRank: 'Active', isActive: false }
    ]

    testNodes.forEach(node => {
      const color = getNodeColor(node)
      const strokeColor = getStrokeColor(node)
      const size = getNodeSize(node) + 8

      console.log(`简单标记 ${node.callsign}: 颜色=${color}, 描边=${strokeColor}, 大小=${size}`)

      // 使用传统的CircleMarker
      const marker = new AMap.CircleMarker({
        center: [node.longitude, node.latitude],
        radius: size,
        fillColor: color,
        fillOpacity: 0.9,
        strokeColor: strokeColor,
        strokeWeight: 3,
        zIndex: 9999
      })

      // 添加到地图
      mapInstance.add(marker)
      testMarkers.push(marker)
    })

    // 直接设置地图中心和缩放级别
    if (testMarkers.length > 0) {
      // 设置到测试区域的中心
      mapInstance.setZoomAndCenter(6, [116.5, 39.5])
    }

    console.log(`🟡 已创建 ${testMarkers.length} 个简单标记`)

    // 保存引用以便后续清理
    mapStore.testMarkers = testMarkers
  }

  /**
   * 创建超简单测试 - 直接在当前视图中心创建标记
   */
  const createUltraSimpleTest = async () => {
    const { mapInstance } = mapStore
    if (!mapInstance) return

    console.log('⭐ 创建超简单测试标记...')

    // 清理旧的测试标记
    if (mapStore.testMarkers) {
      mapStore.testMarkers.forEach(marker => {
        mapInstance.remove(marker)
      })
    }

    // 获取当前地图中心
    const center = mapInstance.getCenter()
    const centerLng = center.lng
    const centerLat = center.lat

    const testMarkers = []
    const colors = ['#FF6B35', '#00D084', '#3B82F6', '#BDC3C7'] // 我们的新颜色
    const offsets = [[0, 0.5], [0.5, 0], [0, -0.5], [-0.5, 0]] // 相对偏移

    for (let i = 0; i < 4; i++) {
      const [offsetLng, offsetLat] = offsets[i]

      console.log(`超简单标记 ${i+1}: 颜色=${colors[i]}, 位置=[${centerLng + offsetLng}, ${centerLat + offsetLat}]`)

      const marker = new AMap.CircleMarker({
        center: [centerLng + offsetLng, centerLat + offsetLat],
        radius: 20 + i * 5, // 不同大小
        fillColor: colors[i],
        fillOpacity: 0.8,
        strokeColor: '#FFFFFF',
        strokeWeight: 3,
        zIndex: 9999
      })

      mapInstance.add(marker)
      testMarkers.push(marker)
    }

    // 保存引用
    mapStore.testMarkers = testMarkers

    console.log(`⭐ 已在当前视图中心创建 ${testMarkers.length} 个超简单标记`)
  }

  /**
   * 使用定位图标重新创建所有真实节点
   */
  const recreateWithCircleMarkers = async () => {
    const { mapInstance } = mapStore
    if (!mapInstance || !mapStore.mapNodes || mapStore.mapNodes.length === 0) return

    console.log('📍 使用定位图标重新创建真实节点...')

    // 清理旧的测试标记
    if (mapStore.testMarkers) {
      mapStore.testMarkers.forEach(marker => {
        mapInstance.remove(marker)
      })
      mapStore.testMarkers = []
    }

    // 清理LabelMarker层
    const { labelsLayer } = mapStore
    if (labelsLayer) {
      labelsLayer.clear()
    }

    // 创建定位图标数组
    const circleMarkers = []

    // 分析数据结构和多样性
    const allNodes = mapStore.mapNodes
    console.log(`🔍 分析 ${allNodes.length} 个节点的数据多样性:`)

    // 统计不同类型
    const rankStats = {}
    const activeStats = { active: 0, inactive: 0 }
    const typeStats = {}

    allNodes.forEach(node => {
      // 统计nodeRank
      rankStats[node.nodeRank] = (rankStats[node.nodeRank] || 0) + 1

      // 统计isActive
      if (node.isActive) activeStats.active++
      else activeStats.inactive++

      // 统计affiliationType
      typeStats[node.affiliationType] = (typeStats[node.affiliationType] || 0) + 1
    })

    console.log('节点等级分布:', rankStats)
    console.log('活跃状态分布:', activeStats)
    console.log('组织类型分布:', typeStats)

    // 创建多样化演示：人工修改一些节点的属性来展示不同颜色
    const demonstrationNodes = allNodes.slice(0, 50).map((node, index) => {
      const demoNode = { ...node }

      // 每4个节点创建不同类型的演示
      const typeIndex = index % 4
      switch (typeIndex) {
        case 0: // 保持原样 (Active + true)
          break
        case 1: // 改为Core
          demoNode.nodeRank = 'Core'
          demoNode.isActive = true
          break
        case 2: // 改为Transient
          demoNode.nodeRank = 'Transient'
          demoNode.isActive = true
          break
        case 3: // 改为离线
          demoNode.isActive = false
          break
      }

      return demoNode
    })

    console.log('🎨 创建多样化演示：每4个节点循环显示不同颜色')

    demonstrationNodes.forEach(node => { // 使用演示数据
      if (!node.longitude || !node.latitude) return

      const color = getNodeColor(node)
      const strokeColor = getStrokeColor(node)
      const size = getNodeSize(node)

      // 创建定位图标样式的SVG
      const createLocationIcon = (fillColor, strokeColor, size) => {
        const svgSize = size * 2.5
        return `
          <svg width="${svgSize}" height="${svgSize}" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <filter id="shadow${Math.random()}" x="-20%" y="-20%" width="140%" height="140%">
                <feDropShadow dx="1" dy="2" stdDeviation="2" flood-opacity="0.3"/>
              </filter>
            </defs>
            <!-- 定位图标主体 -->
            <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z"
                  fill="${fillColor}"
                  stroke="${strokeColor}"
                  stroke-width="2"
                  filter="url(#shadow${Math.random()})"/>
            <!-- 内部圆点 -->
            <circle cx="12" cy="9" r="2.5" fill="${strokeColor}" opacity="0.8"/>
          </svg>
        `.trim()
      }

      const svgIcon = createLocationIcon(color, strokeColor, size)

      const marker = new AMap.Marker({
        position: [node.longitude, node.latitude],
        content: `<div style="transform: translate(-50%, -100%)">${svgIcon}</div>`,
        zIndex: getNodeZIndex(node),
        anchor: 'bottom-center'
      })

      // 添加点击事件
      marker.on('click', () => {
        showNodeInfo(node, [node.longitude, node.latitude])
        mapStore.setSelectedNode(node)
      })

      mapInstance.add(marker)
      circleMarkers.push(marker)
    })

    // 保存引用
    mapStore.circleMarkers = circleMarkers

    console.log(`📍 已用定位图标创建 ${circleMarkers.length} 个真实节点，使用新颜色系统`)
  }

  /**
   * 强制刷新地图标记（定位图标样式）
   */
  const forceRefreshMarkers = async () => {
    console.log('🔄 强制刷新定位图标标记...')
    const { mapInstance } = mapStore
    if (!mapInstance || !mapStore.mapNodes || mapStore.mapNodes.length === 0) return

    // 完全重新创建图层
    await recreateLabelsLayer(mapInstance)

    // 重新创建定位图标标记
    await createNodeMarkers(mapStore.mapNodes)
    console.log('✅ 定位图标标记已强制刷新')
  }

  /**
   * 重新创建标注图层
   */
  const recreateLabelsLayer = async (map) => {
    const { labelsLayer: oldLayer } = mapStore

    // 移除旧图层
    if (oldLayer) {
      oldLayer.clear()
      map.remove(oldLayer)
      // 等待图层完全移除
      await new Promise(resolve => setTimeout(resolve, 100))
    }

    // 创建新图层 - 完全不同的配置确保重新渲染
    const newLabelsLayer = new AMap.LabelsLayer({
      zIndex: 1001 + Math.floor(Math.random() * 100), // 随机z-index
      collision: false, // 暂时关闭避让，确保所有节点都显示
      allowCollision: true,
      // 添加唯一标识符
      id: `labels-layer-${Date.now()}`
    })

    // 添加到地图
    map.add(newLabelsLayer)

    // 更新Store中的引用
    mapStore.setLabelsLayer(newLabelsLayer)

    // 等待图层完全添加
    await new Promise(resolve => setTimeout(resolve, 50))

    console.log('🆕 标注图层已重新创建')
  }

  /**
   * 清理资源
   */
  const cleanup = () => {
    const { mapInstance, labelsLayer, infoWindow } = mapStore

    // 清理直接添加的标记
    if (mapStore.directMarkers && mapInstance) {
      mapStore.directMarkers.forEach(marker => {
        mapInstance.remove(marker)
      })
      mapStore.directMarkers = []
    }

    if (labelsLayer) {
      labelsLayer.clear()
    }

    if (infoWindow) {
      infoWindow.close()
    }

    if (mapInstance) {
      mapInstance.destroy()
    }
  }

  return {
    initializeMap,
    loadNodesInBounds,
    createNodeMarkers,
    showNodeInfo,
    panToLocation,
    forceRefreshMarkers,
    createTestMarkers,
    createSimpleTestMarkers,
    createUltraSimpleTest,
    recreateWithCircleMarkers,
    cleanup
  }
}