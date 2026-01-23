<template>
  <div class="node-list-container">
    <el-card shadow="hover">
      <template #header>
        <div class="table-header">
          <h3>节点列表</h3>
          <div class="header-controls">
            <el-button
              type="primary"
              size="small"
              @click="refreshData"
              :loading="loading"
            >
              刷新数据
            </el-button>
          </div>
        </div>
      </template>

      <!-- 查询表单 -->
      <div class="query-form">
        <el-form :model="queryForm" inline size="small">
          <el-form-item label="呼号">
            <el-input
              v-model="queryForm.callsign"
              placeholder="输入呼号"
              clearable
              @keyup.enter="handleSearch"
            />
          </el-form-item>
          <el-form-item label="国家">
            <el-input
              v-model="queryForm.country"
              placeholder="输入国家"
              clearable
              @keyup.enter="handleSearch"
            />
          </el-form-item>
          <el-form-item label="组织类型">
            <el-select v-model="queryForm.affiliationType" placeholder="选择类型" clearable>
              <el-option label="个人" value="Personal" />
              <el-option label="俱乐部" value="Club" />
              <el-option label="系统" value="System" />
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="queryForm.isActive" placeholder="选择状态" clearable>
              <el-option label="在线" :value="true" />
              <el-option label="离线" :value="false" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleSearch" size="small">
              搜索
            </el-button>
            <el-button @click="handleReset" size="small">
              重置
            </el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 数据表格 -->
      <el-table
        :data="tableData"
        v-loading="loading"
        border
        stripe
        height="600"
        @sort-change="handleSortChange"
        class="node-table"
      >
        <el-table-column
          prop="nodeId"
          label="节点ID"
          width="100"
          sortable="custom"
          align="center"
        />
        <el-table-column
          prop="callsign"
          label="呼号"
          width="120"
          sortable="custom"
        />
        <el-table-column
          prop="owner"
          label="所有者"
          width="150"
          show-overflow-tooltip
        />
        <el-table-column
          prop="country"
          label="国家"
          width="120"
          sortable="custom"
        />
        <el-table-column
          prop="affiliationType"
          label="组织类型"
          width="100"
          align="center"
        >
          <template #default="{ row }">
            <el-tag
              :type="getAffiliationTypeTagType(row.affiliationType)"
              size="small"
            >
              {{ getAffiliationTypeText(row.affiliationType) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="nodeRank"
          label="节点等级"
          width="100"
          align="center"
        >
          <template #default="{ row }">
            <el-tag
              :type="getNodeRankTagType(row.nodeRank)"
              size="small"
            >
              {{ row.nodeRank }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="isActive"
          label="状态"
          width="80"
          align="center"
        >
          <template #default="{ row }">
            <el-tag
              :type="row.isActive ? 'success' : 'info'"
              size="small"
            >
              {{ row.isActive ? '在线' : '离线' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="activityRate24h"
          label="24h活跃率"
          width="100"
          align="center"
          sortable="custom"
        >
          <template #default="{ row }">
            <span :style="{ color: getActivityRateColor(row.activityRate24h) }">
              {{ row.activityRate24h ? row.activityRate24h + '%' : '0%' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column
          prop="lastSeen"
          label="最后在线"
          width="150"
          sortable="custom"
        >
          <template #default="{ row }">
            {{ formatDateTime(row.lastSeen) }}
          </template>
        </el-table-column>
        <el-table-column
          label="操作"
          width="120"
          align="center"
          fixed="right"
        >
          <template #default="{ row }">
            <el-button
              type="primary"
              size="small"
              text
              @click="handleLocateNode(row)"
              :disabled="!row.latitude || !row.longitude"
            >
              定位
            </el-button>
            <el-button
              type="info"
              size="small"
              text
              @click="handleViewDetail(row)"
            >
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.current"
          v-model:page-size="pagination.size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { nodeApi } from '@/api/nodeApi'
import { ElMessage } from 'element-plus'

// Props & Emits
const emit = defineEmits(['locateNode', 'viewDetail'])

// 响应式数据
const loading = ref(false)
const tableData = ref([])

// 查询表单
const queryForm = reactive({
  callsign: '',
  country: '',
  affiliationType: '',
  isActive: null
})

// 分页信息
const pagination = reactive({
  current: 1,
  size: 20,
  total: 0
})

// 排序信息
const sortInfo = reactive({
  sortField: 'updateTime',
  sortOrder: 'desc'
})

// 获取节点列表数据
const fetchData = async () => {
  try {
    loading.value = true

    const params = {
      current: pagination.current,
      size: pagination.size,
      sortField: sortInfo.sortField,
      sortOrder: sortInfo.sortOrder,
      ...queryForm
    }

    const result = await nodeApi.getNodeListByPage(params)

    if (result) {
      tableData.value = result.records || []
      pagination.total = result.total || 0
    }
  } catch (error) {
    console.error('获取节点列表失败:', error)
    ElMessage.error('获取节点列表失败')
  } finally {
    loading.value = false
  }
}

// 搜索
const handleSearch = () => {
  pagination.current = 1
  fetchData()
}

// 重置
const handleReset = () => {
  Object.assign(queryForm, {
    callsign: '',
    country: '',
    affiliationType: '',
    isActive: null
  })
  pagination.current = 1
  fetchData()
}

// 刷新数据
const refreshData = () => {
  fetchData()
}

// 排序变化
const handleSortChange = ({ prop, order }) => {
  if (prop) {
    sortInfo.sortField = prop
    sortInfo.sortOrder = order === 'ascending' ? 'asc' : 'desc'
    pagination.current = 1
    fetchData()
  }
}

// 分页大小变化
const handleSizeChange = (size) => {
  pagination.size = size
  pagination.current = 1
  fetchData()
}

// 页码变化
const handleCurrentChange = (current) => {
  pagination.current = current
  fetchData()
}

// 定位节点
const handleLocateNode = (row) => {
  if (row.latitude && row.longitude) {
    emit('locateNode', row.longitude, row.latitude, row)
    ElMessage.success(`正在定位节点 ${row.callsign}`)
  } else {
    ElMessage.warning('该节点没有位置信息')
  }
}

// 查看详情
const handleViewDetail = (row) => {
  emit('viewDetail', row)
  // 可以在这里实现详情弹窗或跳转
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

// 组件挂载时获取数据
onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.node-list-container {
  width: 100%;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.table-header h3 {
  margin: 0;
  color: #303133;
  font-size: 18px;
}

.query-form {
  margin-bottom: 20px;
  padding: 15px;
  background: #f8f9fa;
  border-radius: 6px;
}

.node-table {
  margin-bottom: 20px;
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
  padding: 20px 0;
}

/* 深度定制样式 */
:deep(.el-table__header-wrapper) {
  background: #f5f7fa;
}

:deep(.el-table__header) {
  color: #606266;
  font-weight: 600;
}

:deep(.el-table__row:hover) {
  background-color: #f5f7fa;
}

:deep(.el-button--text) {
  padding: 5px 8px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .table-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .query-form :deep(.el-form--inline .el-form-item) {
    display: block;
    margin-bottom: 10px;
  }

  .pagination-container {
    justify-content: center;
  }

  :deep(.el-pagination) {
    flex-wrap: wrap;
    justify-content: center;
  }
}

@media (max-width: 480px) {
  .node-table {
    font-size: 12px;
  }

  :deep(.el-table__cell) {
    padding: 8px 5px;
  }

  :deep(.el-tag--small) {
    font-size: 10px;
    padding: 0 5px;
  }
}
</style>