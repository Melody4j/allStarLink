<template>
  <div class="nodes-container">
    <h2 class="page-title">节点列表</h2>
    
    <!-- 搜索和筛选 -->
    <div class="nodes-controls">
      <div class="search-section">
        <el-input
          v-model="searchQuery"
          placeholder="搜索节点ID、呼号、位置..."
          clearable
          style="width: 300px; margin-right: 10px;"
        >
          <template #prepend>
            <el-icon><search /></el-icon>
          </template>
        </el-input>
      </div>
      
      <div class="filter-section">
        <!-- 活跃状态筛选 -->
        <el-select v-model="activeFilter" placeholder="筛选状态" size="small" style="margin-right: 15px;">
          <el-option label="全部节点" value="all" />
          <el-option label="活跃节点" value="active" />
          <el-option label="非活跃节点" value="inactive" />
        </el-select>
        
        <!-- 自定义活跃时间阈值 -->
        <div class="active-time-section">
          <span style="margin-right: 5px; font-size: 14px; color: #606266;">活跃时间:</span>
          <el-input-number
            v-model="activeTimeThreshold"
            :min="1"
            :max="720"
            :step="1"
            size="small"
            style="width: 120px; margin-right: 5px;"
            @change="updateActiveStatus"
          />
          <span style="font-size: 14px; color: #606266;">小时</span>
        </div>
      </div>
      
      <div class="sort-section">
        <el-select v-model="sortBy" placeholder="排序字段" size="small" style="margin-right: 10px;">
          <el-option label="节点ID" value="nodeId" />
          <el-option label="呼号" value="callsign" />
          <el-option label="位置" value="location" />
          <el-option label="最后在线" value="lastSeen" />
        </el-select>
        
        <el-button-group size="small">
          <el-button :icon="sortOrder === 'asc' ? 'el-icon-top' : 'el-icon-bottom'" @click="toggleSortOrder">
            {{ sortOrder === 'asc' ? '升序' : '降序' }}
          </el-button>
        </el-button-group>
      </div>
    </div>
    
    <!-- 节点表格 -->
    <el-card shadow="hover" class="nodes-table-card">
      <el-table 
        :data="filteredNodes" 
        stripe 
        style="width: 100%"
        @row-click="handleRowClick"
        v-loading="loading"
      >
        <el-table-column prop="nodeId" label="节点ID" width="100" sortable />
        <el-table-column prop="callsign" label="呼号" width="120" sortable />
        <el-table-column prop="owner" label="所有者" width="150" />
        <el-table-column prop="location" label="位置" width="250" sortable />
        <el-table-column prop="frequency" label="频率" width="100" />
        <el-table-column prop="tone" label="亚音频" width="100" />
        <el-table-column prop="site" label="站点" width="150" />
        <el-table-column prop="affiliation" label="所属组织" width="150" />
        <el-table-column prop="lastSeen" label="最后在线" width="180" sortable>
          <template #default="scope">
            {{ formatDateTime(scope.row.lastSeen) }}
          </template>
        </el-table-column>
        <el-table-column prop="isActive" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.isActive ? 'success' : 'danger'" size="small">
              {{ scope.row.isActive ? '活跃' : '非活跃' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="features" label="功能" min-width="100">
          <template #default="scope">
            <el-tag v-if="scope.row.features && scope.row.features.includes('Webtransceiver')" size="small" type="info">
              Web
            </el-tag>
            <el-tag v-if="scope.row.features && scope.row.features.includes('Telephone Portal')" size="small" type="warning">
              Phone
            </el-tag>
            <span v-else>无</span>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          background
          layout="total, sizes, prev, pager, next, jumper"
          :total="totalNodes"
          :page-sizes="[10, 20, 50, 100]"
          :page-size="pageSize"
          v-model:current-page="currentPage"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>
    
    <!-- 节点详情弹窗 -->
    <el-dialog
      v-model="nodeDialogVisible"
      title="节点详情"
      width="600px"
    >
      <div v-if="selectedNode" class="node-details">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="节点ID">{{ selectedNode.nodeId }}</el-descriptions-item>
          <el-descriptions-item label="呼号">{{ selectedNode.callsign }}</el-descriptions-item>
          <el-descriptions-item label="所有者">{{ selectedNode.owner }}</el-descriptions-item>
          <el-descriptions-item label="位置">{{ selectedNode.location }}</el-descriptions-item>
          <el-descriptions-item label="频率">{{ selectedNode.frequency }}</el-descriptions-item>
          <el-descriptions-item label="亚音频">{{ selectedNode.tone }}</el-descriptions-item>
          <el-descriptions-item label="站点">{{ selectedNode.site }}</el-descriptions-item>
          <el-descriptions-item label="所属组织">{{ selectedNode.affiliation }}</el-descriptions-item>
          <el-descriptions-item label="最后在线" :span="2">{{ formatDateTime(selectedNode.lastSeen) }}</el-descriptions-item>
          <el-descriptions-item label="状态" :span="2">
            <el-tag :type="selectedNode.isActive ? 'success' : 'danger'" size="large">
              {{ selectedNode.isActive ? '活跃' : '非活跃' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="功能" :span="2">
            <el-tag v-if="selectedNode.features && selectedNode.features.includes('Webtransceiver')" size="large" type="info" style="margin-right: 10px;">
              Webtransceiver
            </el-tag>
            <el-tag v-if="selectedNode.features && selectedNode.features.includes('Telephone Portal')" size="large" type="warning">
              Telephone Portal
            </el-tag>
            <span v-else>无特殊功能</span>
          </el-descriptions-item>
        </el-descriptions>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="nodeDialogVisible = false">关闭</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { getAllNodes, getNodesByPage } from '../utils/api'

// 页面状态
const loading = ref(true)
const nodes = ref([])
const searchQuery = ref('')
const activeFilter = ref('all')
const sortBy = ref('nodeId')
const sortOrder = ref('asc')
const currentPage = ref(1)
const pageSize = ref(20)
const totalNodes = ref(0) // 总节点数，从后端返回
const selectedNode = ref(null)
const nodeDialogVisible = ref(false)

// 格式化日期时间
const formatDateTime = (dateTime) => {
  if (!dateTime) return '未知'
  
  const date = new Date(dateTime)
  return date.toLocaleString('zh-CN')
}

// 过滤和排序但未分页的节点
const totalFilteredNodes = computed(() => {
  let filtered = [...nodes.value]
  
  // 搜索过滤
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(node => 
      node.nodeId.toString().includes(query) ||
      (node.callsign && node.callsign.toLowerCase().includes(query)) ||
      (node.owner && node.owner.toLowerCase().includes(query)) ||
      (node.location && node.location.toLowerCase().includes(query)) ||
      (node.site && node.site.toLowerCase().includes(query)) ||
      (node.affiliation && node.affiliation.toLowerCase().includes(query))
    )
  }
  
  // 状态过滤
  if (activeFilter.value === 'active') {
    filtered = filtered.filter(node => node.isActive)
  } else if (activeFilter.value === 'inactive') {
    filtered = filtered.filter(node => !node.isActive)
  }
  
  // 排序
  filtered.sort((a, b) => {
    let aValue = a[sortBy.value]
    let bValue = b[sortBy.value]
    
    // 处理日期类型
    if (sortBy.value === 'lastSeen') {
      aValue = aValue ? new Date(aValue).getTime() : 0
      bValue = bValue ? new Date(bValue).getTime() : 0
    }
    
    // 处理字符串类型
    if (typeof aValue === 'string') {
      aValue = aValue.toLowerCase()
    }
    if (typeof bValue === 'string') {
      bValue = bValue.toLowerCase()
    }
    
    // 比较
    if (aValue < bValue) return sortOrder.value === 'asc' ? -1 : 1
    if (aValue > bValue) return sortOrder.value === 'asc' ? 1 : -1
    return 0
  })
  
  return filtered
})

// 过滤、排序和分页后的节点
const filteredNodes = computed(() => {
  return totalFilteredNodes.value
})

// 获取节点数据
const fetchNodes = async () => {
  try {
    loading.value = true
    const data = await getNodesByPage(currentPage.value, pageSize.value)
    console.log('获取到的节点数据:', data)
    nodes.value = data.list
    totalNodes.value = data.total
    // 统计活跃节点数量
    const activeCount = nodes.value.filter(node => node.isActive).length
    console.log('活跃节点数量:', activeCount, '总节点数量:', totalNodes.value)
  } catch (error) {
    console.error('获取节点数据失败:', error)
  } finally {
    loading.value = false
  }
}

// 处理行点击
const handleRowClick = (row) => {
  selectedNode.value = row
  nodeDialogVisible.value = true
}

// 切换排序顺序
const toggleSortOrder = () => {
  sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
}

// 处理分页大小变化
const handleSizeChange = (size) => {
  pageSize.value = size
  currentPage.value = 1
}

// 处理当前页变化
const handleCurrentChange = (current) => {
  currentPage.value = current
}

// 页面加载时获取数据
onMounted(() => {
  fetchNodes()
})
</script>

<style scoped>
.nodes-container {
  padding: 0 20px;
}

.page-title {
  font-size: 24px;
  margin-bottom: 20px;
  color: #303133;
}

.nodes-controls {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  padding: 15px;
  background-color: #f5f7fa;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  gap: 20px;
}

.search-section {
  display: flex;
  align-items: center;
}

.filter-section {
  display: flex;
  align-items: center;
}

.active-time-section {
  display: flex;
  align-items: center;
}

.sort-section {
  display: flex;
  align-items: center;
  margin-left: auto;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .nodes-controls {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  
  .search-section,
  .filter-section,
  .sort-section {
    width: 100%;
  }
  
  .active-time-section {
    margin-top: 10px;
  }
  
  .sort-section {
    justify-content: flex-start;
    margin-left: 0;
    margin-top: 10px;
  }
}

.nodes-table-card {
  margin-bottom: 20px;
}

.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

.node-details {
  padding: 10px 0;
}
</style>