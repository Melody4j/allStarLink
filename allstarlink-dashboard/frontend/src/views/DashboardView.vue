<template>
  <div class="dashboard">
    <div class="page-header">
      <h1>✓ AllStarLink 节点仪表盘</h1>
      <p class="header-description">
        实时监控全球 AllStarLink 业余无线电网络节点状态和分布
      </p>
    </div>

    <!-- 统计概览卡片 -->
    <div class="overview-cards">
      <el-row :gutter="20">
        <el-col :xs="12" :sm="6" :md="6" :lg="6">
          <stats-card
            title="总节点数"
            :count="globalStats.totalNodes || 0"
            icon="📊"
            color="#409EFF"
          />
        </el-col>
        <el-col :xs="12" :sm="6" :md="6" :lg="6">
          <stats-card
            title="活跃节点"
            :count="globalStats.activeNodes || 0"
            icon="🟢"
            color="#67C23A"
          />
        </el-col>
        <el-col :xs="12" :sm="6" :md="6" :lg="6">
          <stats-card
            title="全球活跃率"
            :count="globalStats.globalActiveRate || 0"
            icon="📈"
            color="#E6A23C"
            :is-percentage="true"
          />
        </el-col>
        <el-col :xs="12" :sm="6" :md="6" :lg="6">
          <stats-card
            title="覆盖大洲"
            :count="globalStats.activeContinents || 0"
            icon="🌍"
            color="#F56C6C"
            suffix="个"
          />
        </el-col>
      </el-row>
    </div>

    <!-- 统计图表区域 -->
    <div class="stats-section">
      <stats-chart @region-click="handleRegionClick" />
    </div>

    <!-- 地图展示区域 -->
    <div class="map-section">
      <el-card shadow="hover" class="map-card">
        <template #header>
          <div class="card-header">
            <span>🗺️ 节点分布地图</span>
            <el-button
              type="text"
              size="small"
              @click="refreshMap"
              :loading="isRefreshing"
            >
              刷新
            </el-button>
          </div>
        </template>
        <map-container
          ref="mapContainerRef"
          style="height: 600px;"
        />
      </el-card>
    </div>

    <!-- 节点列表 -->
    <div class="node-list-section">
      <node-list-table
        @locate-node="handleLocateNode"
        @view-detail="handleViewDetail"
      />
    </div>

    <!-- 节点详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="节点详情"
      width="600px"
      :before-close="handleCloseDetail"
    >
      <div v-if="selectedNodeDetail" class="node-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="节点ID">
            {{ selectedNodeDetail.nodeId }}
          </el-descriptions-item>
          <el-descriptions-item label="呼号">
            {{ selectedNodeDetail.callsign }}
          </el-descriptions-item>
          <el-descriptions-item label="所有者">
            {{ selectedNodeDetail.owner || '未知' }}
          </el-descriptions-item>
          <el-descriptions-item label="组织名称">
            {{ selectedNodeDetail.affiliation || '未知' }}
          </el-descriptions-item>
          <el-descriptions-item label="组织类型">
            <el-tag :type="getAffiliationTypeTagType(selectedNodeDetail.affiliationType)">
              {{ getAffiliationTypeText(selectedNodeDetail.affiliationType) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="节点等级">
            <el-tag :type="getNodeRankTagType(selectedNodeDetail.nodeRank)">
              {{ selectedNodeDetail.nodeRank }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="当前状态">
            <el-tag :type="selectedNodeDetail.isActive ? 'success' : 'info'">
              {{ selectedNodeDetail.isActive ? '在线' : '离线' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="24h活跃率">
            <span :style="{ color: getActivityRateColor(selectedNodeDetail.activityRate24h) }">
              {{ selectedNodeDetail.activityRate24h ? selectedNodeDetail.activityRate24h + '%' : '0%' }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="位置">
            {{ selectedNodeDetail.country }}, {{ selectedNodeDetail.continent }}
          </el-descriptions-item>
          <el-descriptions-item label="移动属性">
            {{ selectedNodeDetail.mobilityType === 'Fixed' ? '固定' : '移动' }}
          </el-descriptions-item>
          <el-descriptions-item label="坐标">
            {{ selectedNodeDetail.latitude?.toFixed(4) || 0 }}, {{ selectedNodeDetail.longitude?.toFixed(4) || 0 }}
          </el-descriptions-item>
          <el-descriptions-item label="首次入网">
            {{ formatDateTime(selectedNodeDetail.firstSeenAt) }}
          </el-descriptions-item>
          <el-descriptions-item label="最后在线">
            {{ formatDateTime(selectedNodeDetail.lastSeen) }}
          </el-descriptions-item>
          <el-descriptions-item label="更新时间">
            {{ formatDateTime(selectedNodeDetail.updateTime) }}
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="detailDialogVisible = false">
            关闭
          </el-button>
          <el-button
            type="primary"
            @click="handleLocateFromDetail"
            :disabled="!selectedNodeDetail?.latitude || !selectedNodeDetail?.longitude"
          >
            地图定位
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useMapStore } from '@/stores/mapStore'
import { nodeApi } from '@/api/nodeApi'
import MapContainer from '@/components/MapContainer.vue'
import StatsChart from '@/components/StatsChart.vue'
import NodeListTable from '@/components/NodeListTable.vue'
import StatsCard from '@/components/StatsCard.vue'
import {
  ElRow,
  ElCol,
  ElCard,
  ElButton,
  ElDialog,
  ElDescriptions,
  ElDescriptionsItem,
  ElTag,
  ElMessage
} from 'element-plus'

const mapStore = useMapStore()
const mapContainerRef = ref()
const isRefreshing = ref(false)

// 节点详情对话框
const detailDialogVisible = ref(false)
const selectedNodeDetail = ref(null)

// 全局统计数据
const globalStats = computed(() => mapStore.globalStats)

// 处理区域点击 - 联动地图定位
const handleRegionClick = async (regionName, dimension) => {
  console.log(`点击了${dimension === 'continent' ? '大洲' : '国家'}: ${regionName}`)

  // 根据区域名称获取对应的坐标进行定位
  const regionCoordinates = getRegionCoordinates(regionName, dimension)

  if (regionCoordinates && mapContainerRef.value) {
    mapContainerRef.value.panToLocation(
      regionCoordinates.longitude,
      regionCoordinates.latitude,
      dimension === 'continent' ? 4 : 6
    )
    ElMessage.success(`正在定位到 ${regionName}`)
  } else {
    ElMessage.info(`暂无 ${regionName} 的位置信息`)
  }
}

// 处理节点定位
const handleLocateNode = (longitude, latitude, nodeInfo) => {
  if (mapContainerRef.value) {
    mapContainerRef.value.panToLocation(longitude, latitude, 12)
    if (nodeInfo) {
      ElMessage.success(`定位到节点 ${nodeInfo.callsign || nodeInfo.nodeId}`)
    }
  }
}

// 处理查看节点详情
const handleViewDetail = (nodeDetail) => {
  selectedNodeDetail.value = nodeDetail
  detailDialogVisible.value = true
}

// 从详情页面定位
const handleLocateFromDetail = () => {
  if (selectedNodeDetail.value) {
    handleLocateNode(
      selectedNodeDetail.value.longitude,
      selectedNodeDetail.value.latitude,
      selectedNodeDetail.value
    )
    detailDialogVisible.value = false
  }
}

// 关闭详情对话框
const handleCloseDetail = () => {
  detailDialogVisible.value = false
  selectedNodeDetail.value = null
}

// 刷新地图
const refreshMap = async () => {
  isRefreshing.value = true
  try {
    // 这里可以重新加载地图数据
    ElMessage.success('地图数据刷新成功')
  } catch (error) {
    ElMessage.error('地图数据刷新失败')
  } finally {
    isRefreshing.value = false
  }
}

// 获取区域坐标 (示例数据，实际应该从API获取或配置文件读取)
const getRegionCoordinates = (regionName, dimension) => {
  const coordinates = {
    // 大洲坐标
    'North America': { longitude: -95.7129, latitude: 37.0902 },
    'Europe': { longitude: 10.4515, latitude: 51.1657 },
    'Asia': { longitude: 103.8198, latitude: 1.3521 },
    'South America': { longitude: -60.0583, latitude: -15.5994 },
    'Africa': { longitude: 17.8739, latitude: -3.3398 },
    'Oceania': { longitude: 138.2529, latitude: -26.4390 },

    // 国家坐标示例
    'United States': { longitude: -95.7129, latitude: 39.8283 },
    'China': { longitude: 104.1954, latitude: 35.8617 },
    'Japan': { longitude: 138.2529, latitude: 36.2048 },
    'Germany': { longitude: 10.4515, latitude: 51.1657 },
    'United Kingdom': { longitude: -3.4360, latitude: 55.3781 },
    'Canada': { longitude: -106.3468, latitude: 56.1304 },
    'Australia': { longitude: 133.7751, latitude: -25.2744 },
    'France': { longitude: 2.2137, latitude: 46.2276 },
    'Italy': { longitude: 12.5674, latitude: 41.8719 },
    'Spain': { longitude: -3.7492, latitude: 40.4637 }
  }

  return coordinates[regionName]
}

// 获取组织类型标签类型
const getAffiliationTypeTagType = (type) => {
  switch (type) {
    case 'Personal': return 'info'
    case 'Club': return 'success'
    case 'System': return 'warning'
    default: return ''
  }
}

// 获取组织类型文本
const getAffiliationTypeText = (type) => {
  switch (type) {
    case 'Personal': return '个人'
    case 'Club': return '俱乐部'
    case 'System': return '系统'
    default: return type || '未知'
  }
}

// 获取节点等级标签类型
const getNodeRankTagType = (rank) => {
  switch (rank) {
    case 'Core': return 'danger'
    case 'Active': return 'success'
    case 'Transient': return 'info'
    default: return ''
  }
}

// 获取活跃率颜色
const getActivityRateColor = (rate) => {
  if (!rate) return '#909399'
  if (rate >= 80) return '#67C23A'
  if (rate >= 50) return '#E6A23C'
  return '#F56C6C'
}

// 格式化日期时间
const formatDateTime = (dateStr) => {
  if (!dateStr) return '-'
  try {
    const date = new Date(dateStr)
    return date.toLocaleString('zh-CN')
  } catch {
    return dateStr
  }
}

// 加载初始数据
const loadInitialData = async () => {
  try {
    const stats = await nodeApi.getStatsOverview()
    if (stats) {
      mapStore.updateGlobalStats(stats)
    }
  } catch (error) {
    console.error('加载初始数据失败:', error)
  }
}

// 组件挂载时加载数据
onMounted(() => {
  loadInitialData()
})
</script>

<style scoped>
.dashboard {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  text-align: center;
  margin-bottom: 30px;
}

.page-header h1 {
  color: #409EFF;
  font-size: 32px;
  margin: 0 0 10px 0;
  font-weight: 600;
}

.header-description {
  color: #606266;
  font-size: 16px;
  margin: 0;
}

.overview-cards {
  margin-bottom: 30px;
}

.stats-section {
  margin-bottom: 30px;
}

.map-section {
  margin-bottom: 30px;
}

.map-card {
  width: 100%;
}

.map-card .el-card__body {
  padding: 0;
  position: relative;
  overflow: hidden;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.node-list-section {
  margin-top: 20px;
}

.node-detail {
  padding: 10px 0;
}

.dialog-footer {
  text-align: right;
}

/* 深度定制样式 */
:deep(.el-card__header) {
  padding: 18px 20px;
  background: #f8f9fa;
  border-bottom: 1px solid #EBEEF5;
}

:deep(.el-card__body) {
  padding: 20px;
}

:deep(.el-descriptions__label) {
  font-weight: 600;
  color: #606266;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .dashboard {
    padding: 10px;
  }

  .page-header h1 {
    font-size: 24px;
  }

  .header-description {
    font-size: 14px;
  }

  .main-content {
    margin-bottom: 20px;
  }

  .main-content .el-col {
    margin-bottom: 15px;
  }

  :deep(.el-descriptions) {
    font-size: 12px;
  }

  :deep(.el-dialog) {
    width: 95% !important;
    margin: 5vh auto;
  }
}

@media (max-width: 480px) {
  .dashboard {
    padding: 5px;
  }

  .page-header h1 {
    font-size: 20px;
  }

  .overview-cards :deep(.el-col) {
    margin-bottom: 10px;
  }

  :deep(.el-descriptions__cell) {
    padding: 8px 10px;
  }
}
</style>