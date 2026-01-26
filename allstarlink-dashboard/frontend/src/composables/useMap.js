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

      // 创建标注图层 (Canvas 模式，支持海量点位渲染）
      const labelsLayer = new AMap.LabelsLayer({
        zIndex: 1000,
        collision: true, // 开启避让，避免标记重叠
        allowCollision: true,
        // 优化渲染性能
        animation: false,
        autoHide: false,
        // 设置碰撞检测的像素距离
        collisionSize: [40, 40]
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
    // 标记是否正在加载
    let isLoading = false

    // 防抖加载函数
    const debouncedLoad = debounce(async () => {
      // 如果已经在加载中，跳过这次请求
      if (isLoading) {
        console.log('⏳ 正在加载中，跳过本次请求')
        return
      }

      try {
        isLoading = true
        await loadNodesSmart(map)
      } finally {
        isLoading = false
      }
    }, 300)

    // 监听地图移动结束事件
    map.on('moveend', debouncedLoad)

    // 监听地图缩放结束事件
    map.on('zoomend', debouncedLoad)

    // 监听地图完成事件
    map.on('complete', debouncedLoad)

    // 监听缩放开始事件，防止连续缩放触发多次请求
    map.on('zoomstart', () => {
      // 缩放开始时，取消任何待处理的加载请求
      debouncedLoad.cancel()
    })
  }

  /**
   * 加载初始节点数据
   */
  const loadInitialNodes = async (map) => {
    try {
      // 首次加载全量地图节点
      if (!mapStore.fullMapNodes || mapStore.fullMapNodes.length === 0) {
        console.log('📦 首次加载全量地图节点')
        mapStore.fullMapNodes = await nodeApi.getAllMapNodes()
        console.log(`📦 全量地图节点已加载，数量: ${mapStore.fullMapNodes.length}`)
      }

      // 根据当前地图边界过滤节点
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

        // 过滤可视区域内的节点
        const visibleNodes = filterByBounds(mapStore.fullMapNodes, boundsQuery)

        // 更新 Store 中的节点数据
        mapStore.updateMapNodes(visibleNodes)

        // 渲染标记
        await createNodeMarkers(visibleNodes)

        console.log(`🎯 显示 ${visibleNodes.length} 个节点 (缩放级别: ${boundsQuery.zoomLevel})`)
      }
    } catch (error) {
      console.error('加载初始节点数据失败:', error)
      ElMessage.error('节点数据加载失败')
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
   * 智能加载节点
   * 使用全量地图节点数据，根据当前地图边界过滤显示
   */
  const loadNodesSmart = async (map) => {
    try {
      // 确保全量地图节点已加载
      if (!mapStore.fullMapNodes || mapStore.fullMapNodes.length === 0) {
        console.log('📦 首次加载全量地图节点')
        mapStore.fullMapNodes = await nodeApi.getAllMapNodes()
        console.log(`📦 全量地图节点已加载，数量: ${mapStore.fullMapNodes.length}`)
      }

      // 获取当前地图边界
      const bounds = map.getBounds()
      if (!bounds) return

      const sw = bounds.getSouthWest()
      const ne = bounds.getNorthEast()
      const zoom = map.getZoom()
      const zoomLevel = Math.round(Math.max(1, Math.min(18, zoom)))

      const boundsQuery = {
        minLng: Math.max(-180, Math.min(180, sw.lng)),
        maxLng: Math.max(-180, Math.min(180, ne.lng)),
        minLat: Math.max(-90, Math.min(90, sw.lat)),
        maxLat: Math.max(-90, Math.min(90, ne.lat)),
        zoomLevel
      }

      // 更新当前边界到 Store
      mapStore.updateCurrentBounds(boundsQuery)

      // 过滤可视区域内的节点
      const visibleNodes = filterByBounds(mapStore.fullMapNodes, boundsQuery)

      // 更新 Store 中的节点数据
      mapStore.updateMapNodes(visibleNodes)

      // 渲染标记（使用聚合机制）
      await createNodeMarkers(visibleNodes)

      console.log(`🎯 显示 ${visibleNodes.length} 个节点 (缩放级别: ${zoomLevel})`)
    } catch (error) {
      console.error('加载节点数据失败:', error)
      ElMessage.error('节点数据加载失败')
    }
  }

  /**
   * 使用全量索引加载（低缩放级别）
   */
  const loadWithFullIndex = async (boundsQuery) => {
    try {
      // 首次加载全量索引
      if (!mapStore.fullNodeIndex || mapStore.fullNodeIndex.length === 0) {
        console.log('📦 首次加载全量节点索引')
        mapStore.fullNodeIndex = await nodeApi.getAllNodesIndex()
        console.log(`📦 全量节点索引已加载，数量: ${mapStore.fullNodeIndex.length}`)
      }

      // 根据缩放级别抽稀
      const density = getDensityByZoom(boundsQuery.zoomLevel)
      const nodes = thinOutNodes(mapStore.fullNodeIndex, boundsQuery, density)

      // 更新 Store 中的节点数据
      mapStore.updateMapNodes(nodes)

      // 渲染标记
      await createNodeMarkers(nodes)

      console.log(`🎯 抽稀后显示 ${nodes.length} 个节点 (缩放级别: ${boundsQuery.zoomLevel}, 密度: ${density})`)
    } catch (error) {
      console.error('加载全量索引失败:', error)
      ElMessage.error('节点数据加载失败')
    }
  }

  /**
   * 使用分级缓存加载（中等缩放级别）
   */
  const loadWithLevelCache = async (boundsQuery) => {
    try {
      // 计算缓存级别
      const cacheLevel = calculateCacheLevel(boundsQuery.zoomLevel)

      // 检查缓存
      const cacheKey = `zoom_${cacheLevel}`
      if (!mapStore.levelCache || !mapStore.levelCache[cacheKey]) {
        console.log(`📦 从后端加载缩放级别 ${cacheLevel} 的节点`)
        const nodes = await nodeApi.getNodesByZoomLevel(cacheLevel)

        // 初始化缓存
        if (!mapStore.levelCache) {
          mapStore.levelCache = {}
        }
        mapStore.levelCache[cacheKey] = nodes

        console.log(`📦 缩放级别 ${cacheLevel} 的节点已缓存，数量: ${nodes.length}`)
      }

      // 过滤可视区域
      const nodes = filterByBounds(mapStore.levelCache[cacheKey], boundsQuery)

      // 更新 Store 中的节点数据
      mapStore.updateMapNodes(nodes)

      // 渲染标记
      await createNodeMarkers(nodes)

      console.log(`🎯 显示 ${nodes.length} 个节点 (缩放级别: ${boundsQuery.zoomLevel}, 缓存级别: ${cacheLevel})`)
    } catch (error) {
      console.error('加载分级缓存失败:', error)
      ElMessage.error('节点数据加载失败')
    }
  }

  /**
   * 节点抽稀算法
   * 使用网格抽稀，避免节点重叠
   */
  const thinOutNodes = (nodes, boundsQuery, density) => {
    // 过滤可视区域
    const visibleNodes = nodes.filter(node => 
      node.latitude >= boundsQuery.minLat &&
      node.latitude <= boundsQuery.maxLat &&
      node.longitude >= boundsQuery.minLng &&
      node.longitude <= boundsQuery.maxLng
    )

    // 如果节点数量不多，不需要抽稀
    if (visibleNodes.length <= density) {
      return visibleNodes
    }

    // 网格抽稀
    const gridSize = calculateGridSize(boundsQuery, density)
    const grid = new Map()

    visibleNodes.forEach(node => {
      const gridKey = getGridKey(node, gridSize)
      const existingNode = grid.get(gridKey)

      // 网格内只保留优先级最高的节点
      if (!existingNode || getNodePriority(node) > getNodePriority(existingNode)) {
        grid.set(gridKey, node)
      }
    })

    return Array.from(grid.values())
  }

  /**
   * 计算网格大小
   */
  const calculateGridSize = (boundsQuery, density) => {
    const latRange = boundsQuery.maxLat - boundsQuery.minLat
    const lngRange = boundsQuery.maxLng - boundsQuery.minLng
    const area = latRange * lngRange

    // 根据区域面积和目标密度计算网格大小
    const gridSize = Math.sqrt(area / density)
    return Math.max(gridSize, 0.1) // 最小0.1度
  }

  /**
   * 获取网格键
   */
  const getGridKey = (node, gridSize) => {
    const latIndex = Math.floor(node.latitude / gridSize)
    const lngIndex = Math.floor(node.longitude / gridSize)
    return `${latIndex}_${lngIndex}`
  }

  /**
   * 获取节点优先级
   */
  const getNodePriority = (node) => {
    let priority = 0
    if (node.nodeRank === 'Core') priority += 100
    if (node.nodeRank === 'Active') priority += 50
    if (node.affiliationType === 'System') priority += 30
    if (node.isActive) priority += 20
    return priority
  }

  /**
   * 根据缩放级别获取目标密度
   */
  const getDensityByZoom = (zoomLevel) => {
    if (zoomLevel <= 2) return 100   // 全球视图：100个节点
    if (zoomLevel <= 4) return 300   // 大洲视图：300个节点
    if (zoomLevel <= 6) return 500   // 国家视图：500个节点
    return 800                           // 其他：800个节点
  }

  /**
   * 计算缓存级别
   */
  const calculateCacheLevel = (zoomLevel) => {
    if (zoomLevel <= 4) return 4
    if (zoomLevel <= 6) return 6
    if (zoomLevel <= 8) return 8
    return 10
  }

  /**
   * 过滤可视区域
   */
  const filterByBounds = (nodes, boundsQuery) => {
    return nodes.filter(node => 
      node.latitude >= boundsQuery.minLat &&
      node.latitude <= boundsQuery.maxLat &&
      node.longitude >= boundsQuery.minLng &&
      node.longitude <= boundsQuery.maxLng
    )
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

      // 使用 requestAnimationFrame 确保在下一帧渲染，避免阻塞主线程
      await new Promise(resolve => {
        requestAnimationFrame(() => {
          // 重新渲染标记
          createNodeMarkers(Array.isArray(nodes) ? nodes : []).then(resolve)
        })
      })

      console.log(`🎯 加载了 ${nodes?.length || 0} 个节点 (缩放级别: ${query.zoomLevel})`)
    } catch (error) {
      console.error('加载节点数据失败:', error)
      ElMessage.error('节点数据加载失败')
    } finally {
      // 使用 setTimeout 确保在所有渲染完成后才重置加载状态
      setTimeout(() => {
        mapStore.isMapLoading = false
      }, 100)
    }
  }

  /**
   * 创建节点标记 (使用LabelMarker实现聚合优化)
   */
  const createNodeMarkers = async (nodes) => {
    const { mapInstance, labelsLayer } = mapStore
    if (!labelsLayer || !mapInstance) return

    // 清除旧的标记
    labelsLayer.clear()

    if (!Array.isArray(nodes) || nodes.length === 0) {
      return
    }

    console.log(`🎨 开始创建 ${nodes.length} 个节点标记，使用LabelMarker`)

    // 获取当前缩放级别
    const zoomLevel = mapInstance.getZoom()

    // 根据缩放级别决定是否聚合
    const shouldCluster = zoomLevel <= 6

    if (shouldCluster) {
      // 聚合状态：使用聚合标记
      await createClusterMarkers(nodes, zoomLevel)
    } else {
      // 散列状态：直接渲染所有节点
      await createLabelMarkers(nodes)
    }
  }

  /**
   * 创建聚合标记（低缩放级别）
   */
  const createClusterMarkers = async (nodes, zoomLevel) => {
    const { labelsLayer } = mapStore

    // 计算网格大小，根据缩放级别动态调整
    const gridSize = getClusterGridSize(zoomLevel)

    // 创建聚合网格
    const clusters = new Map()

    nodes.forEach(node => {
      if (!node.longitude || !node.latitude) return

      // 计算网格键
      const latIndex = Math.floor(node.latitude / gridSize)
      const lngIndex = Math.floor(node.longitude / gridSize)
      const gridKey = `${latIndex}_${lngIndex}`

      // 获取或创建聚合点
      let cluster = clusters.get(gridKey)
      if (!cluster) {
        cluster = {
          centerLat: node.latitude,
          centerLng: node.longitude,
          nodes: [],
          count: 0,
          isActive: false
        }
        clusters.set(gridKey, cluster)
      }

      // 更新聚合点
      cluster.nodes.push(node)
      cluster.count++
      cluster.centerLat = (cluster.centerLat * (cluster.count - 1) + node.latitude) / cluster.count
      cluster.centerLng = (cluster.centerLng * (cluster.count - 1) + node.longitude) / cluster.count

      // 更新状态
      if (node.isActive) cluster.isActive = true
    })

    // 创建聚合标记
    const markers = []
    clusters.forEach((cluster, key) => {
      const color = cluster.isActive ? '#00D084' : '#BDC3C7'
      const size = getClusterSize(cluster.count)

      // 创建定位图标SVG
      const svgIcon = getClusterIconUrl(color, size)

      const marker = new AMap.LabelMarker({
        position: [cluster.centerLng, cluster.centerLat],
        zIndex: cluster.isActive ? 100 : 1,
        icon: {
          type: 'image',
          image: svgIcon,
          size: [size * 2, size * 2],
          anchor: 'center'
        }
      })

      // 绑定点击事件
      marker.on('click', () => {
        // 聚合点点击时，可以展开显示该区域内的所有节点
        console.log(`聚合点点击，包含 ${cluster.count} 个节点`)
      })

      markers.push(marker)
    })

    // 批量添加到图层
    labelsLayer.add(markers)

    console.log(`📍 已创建 ${markers.length} 个聚合标记，覆盖 ${nodes.length} 个节点`)
  }

  /**
   * 创建散列标记（高缩放级别）
   */
  const createLabelMarkers = async (nodes) => {
    const { labelsLayer } = mapStore

    // 分批创建标记
    const markers = []
    const batchSize = 500
    let currentIndex = 0

    const processBatch = () => {
      const endIndex = Math.min(currentIndex + batchSize, nodes.length)

      for (let i = currentIndex; i < endIndex; i++) {
        const node = nodes[i]
        if (!node.longitude || !node.latitude) continue

        const color = getNodeColor(node)
        const size = getNodeSize(node)

        // 创建定位图标SVG
        const svgIcon = getNodeIconUrl(color, size)

        const marker = new AMap.LabelMarker({
          position: [node.longitude, node.latitude],
          zIndex: getNodeZIndex(node),
          icon: {
            type: 'image',
            image: svgIcon,
            size: [size * 2, size * 2],
            anchor: 'center'
          },
          text: {
            content: node.callsign || node.nodeId?.toString() || '',
            direction: 'bottom',
            offset: [0, size + 2],
            style: {
              fontSize: 11,
              fontWeight: 'bold',
              fillColor: '#2c3e50',
              strokeColor: '#ffffff',
              strokeWidth: 2
            }
          }
        })

        marker.on('click', () => {
          showNodeInfo(node, [node.longitude, node.latitude])
          mapStore.setSelectedNode(node)
        })

        markers.push(marker)
      }

      currentIndex = endIndex

      if (currentIndex < nodes.length) {
        requestAnimationFrame(processBatch)
      } else {
        labelsLayer.add(markers)
        console.log(`📍 已创建 ${markers.length} 个散列标记`)
      }
    }

    processBatch()
  }

  /**
   * 获取聚合网格大小
   */
  const getClusterGridSize = (zoomLevel) => {
    if (zoomLevel <= 3) return 10   // 全球视图：10度网格
    if (zoomLevel <= 5) return 5    // 大洲视图：5度网格
    if (zoomLevel <= 6) return 2    // 国家视图：2度网格
    return 1                         // 其他：1度网格
  }

  /**
   * 获取聚合标记大小（根据节点数量动态调整）
   */
  const getClusterSize = (count) => {
    if (count <= 5) return 20
    if (count <= 10) return 25
    if (count <= 20) return 30
    if (count <= 50) return 35
    if (count <= 100) return 40
    if (count <= 200) return 45
    if (count <= 500) return 50
    if (count <= 1000) return 55
    if (count <= 2000) return 60
    return 65
  }

  /**
   * 获取聚合标记颜色
   */
  const getClusterColor = (cluster) => {
    // 聚合标记中有活跃节点显示为绿色，否则显示为灰色
    return cluster.isActive ? '#00D084' : '#BDC3C7'
  }

  /**
   * 获取聚合图标URL（使用base64编码的SVG）
   */
  const getClusterIconUrl = (color, size) => {
    const svgSize = size * 2
    // 根据大小调整内部圆点的大小
    const innerCircleRadius = Math.max(2, Math.min(4, size / 10))
    const strokeWidth = Math.max(2, Math.min(3, size / 15))

    const svg = `
      <svg width="${svgSize}" height="${svgSize}" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="1" dy="2" stdDeviation="2" flood-opacity="0.3"/>
          </filter>
        </defs>
        <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z"
              fill="${color}"
              stroke="#ffffff"
              stroke-width="${strokeWidth}"
              filter="url(#shadow)"/>
        <circle cx="12" cy="9" r="${innerCircleRadius}" fill="#ffffff" opacity="0.8"/>
      </svg>
    `.trim()

    return 'data:image/svg+xml;base64,' + btoa(svg)
  }

  /**
   * 获取聚合字体大小
   */
  const getClusterFontSize = (count) => {
    if (count <= 10) return 12
    if (count <= 50) return 14
    if (count <= 100) return 16
    if (count <= 500) return 18
    return 20
  }

  /**
   * 获取节点图标URL（使用base64编码的SVG）
   */
  const getNodeIconUrl = (color, size) => {
    const svgSize = size * 2
    const svg = `
      <svg width="${svgSize}" height="${svgSize}" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="1" dy="2" stdDeviation="2" flood-opacity="0.3"/>
          </filter>
        </defs>
        <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z"
              fill="${color}"
              stroke="#ffffff"
              stroke-width="2"
              filter="url(#shadow)"/>
        <circle cx="12" cy="9" r="2.5" fill="#ffffff" opacity="0.8"/>
      </svg>
    `.trim()

    return 'data:image/svg+xml;base64,' + btoa(svg)
  }

  /**
   * 获取节点颜色
   */
  const getNodeColor = (node) => {
    // 离线节点显示为灰色
    if (!node.isActive) return '#BDC3C7'

    // 在线节点统一显示为绿色
    return '#00D084'
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
    // 在线节点的层级高于离线节点
    return node.isActive ? 100 : 1
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
    loadNodesSmart,
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