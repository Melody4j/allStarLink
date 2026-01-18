<template>
  <div class="stats-card" :class="cardClass">
    <div class="card-icon">
      <i :class="icon"></i>
    </div>
    <div class="card-content">
      <div class="card-title">{{ title }}</div>
      <div class="card-count">
        <span v-if="isPercentage">{{ formatPercentage(count) }}</span>
        <span v-else>{{ formatCount(count) }}</span>
        <span v-if="suffix" class="card-suffix">{{ suffix }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

// 组件属性
const props = defineProps({
  title: {
    type: String,
    required: true
  },
  count: {
    type: [Number, String],
    required: true
  },
  icon: {
    type: String,
    default: 'el-icon-data-line'
  },
  color: {
    type: String,
    default: '#409EFF'
  },
  isPercentage: {
    type: Boolean,
    default: false
  },
  suffix: {
    type: String,
    default: ''
  }
})

// 计算卡片类名
const cardClass = computed(() => {
  // 生成基于颜色的类名
  const colorClass = `stats-card-${props.color.replace('#', '')}`
  return [colorClass]
})

// 格式化数字
const formatCount = (count) => {
  if (typeof count !== 'number') {
    return count
  }
  
  if (count >= 1000000) {
    return (count / 1000000).toFixed(2) + 'M'
  } else if (count >= 1000) {
    return (count / 1000).toFixed(2) + 'K'
  }
  return count.toLocaleString()
}

// 格式化百分比
const formatPercentage = (value) => {
  if (typeof value !== 'number') {
    return value
  }
  return value.toFixed(2) + '%'
}
</script>

<style scoped>
.stats-card {
  background-color: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.stats-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 4px 16px 0 rgba(0, 0, 0, 0.15);
}

.card-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  margin-right: 16px;
  color: white;
  background-color: #409EFF;
}

.card-content {
  flex: 1;
}

.card-title {
  font-size: 14px;
  color: #606266;
  margin-bottom: 8px;
}

.card-count {
  font-size: 28px;
  font-weight: 600;
  color: #303133;
}

.card-suffix {
  font-size: 16px;
  color: #606266;
  margin-left: 4px;
}

/* 颜色主题 */
.stats-card-409EFF .card-icon {
  background-color: #409EFF;
}

.stats-card-67C23A .card-icon {
  background-color: #67C23A;
}

.stats-card-E6A23C .card-icon {
  background-color: #E6A23C;
}

.stats-card-F56C6C .card-icon {
  background-color: #F56C6C;
}

.stats-card-909399 .card-icon {
  background-color: #909399;
}

.stats-card-722ED1 .card-icon {
  background-color: #722ED1;
}

.stats-card-13C2C2 .card-icon {
  background-color: #13C2C2;
}
</style>