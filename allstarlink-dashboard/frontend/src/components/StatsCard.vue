<template>
  <div class="stats-card tech-card" :class="cardClass">
    <!-- 科技风背景装饰 -->
    <div class="card-bg-effect">
      <div class="bg-grid"></div>
      <div class="bg-glow"></div>
      <div class="scan-line"></div>
    </div>

    <!-- 图标区域 -->
    <div class="card-icon" :style="{ background: iconGradient }">
      <div class="icon-wrapper">
        <i :class="icon"></i>
        <div class="icon-pulse"></div>
      </div>
      <div class="icon-corner"></div>
    </div>

    <!-- 内容区域 -->
    <div class="card-content">
      <div class="card-title">
        <span class="title-text">{{ title }}</span>
        <div class="title-underline"></div>
      </div>
      <div class="card-count">
        <div class="count-wrapper">
          <span v-if="isPercentage" class="count-value">{{ formatPercentage(count) }}</span>
          <span v-else class="count-value">{{ formatCount(count) }}</span>
          <span v-if="suffix" class="card-suffix">{{ suffix }}</span>
        </div>
        <div class="count-indicator">
          <div class="indicator-dot"></div>
          <div class="indicator-line"></div>
        </div>
      </div>
    </div>

    <!-- 科技角标 -->
    <div class="tech-corner">
      <div class="corner-line-1"></div>
      <div class="corner-line-2"></div>
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
    default: '#6C5CE7'
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

// 颜色映射表 - 科技紫色系
const colorMap = {
  '#409EFF': { primary: '#6C5CE7', secondary: '#74B9FF' }, // 蓝色 -> 紫蓝
  '#67C23A': { primary: '#00B894', secondary: '#00CEC9' }, // 绿色 -> 科技绿
  '#E6A23C': { primary: '#FDCB6E', secondary: '#E17055' }, // 橙色 -> 科技橙
  '#F56C6C': { primary: '#E17055', secondary: '#FD79A8' }, // 红色 -> 科技红
  '#909399': { primary: '#636E72', secondary: '#74B9FF' }, // 灰色 -> 科技灰
  '#722ED1': { primary: '#6C5CE7', secondary: '#A29BFE' }, // 紫色 -> 主紫色
  '#13C2C2': { primary: '#00CEC9', secondary: '#74B9FF' }  // 青色 -> 科技青
}

// 计算卡片类名
const cardClass = computed(() => {
  const colorClass = `stats-card-${props.color.replace('#', '')}`
  return [colorClass]
})

// 计算图标渐变
const iconGradient = computed(() => {
  const colors = colorMap[props.color] || { primary: props.color, secondary: props.color }
  return `linear-gradient(135deg, ${colors.primary} 0%, ${colors.secondary} 100%)`
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
/* === 主卡片样式 === */
.stats-card {
  background: var(--bg-card);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  box-shadow: var(--shadow-md);
  display: flex;
  align-items: center;
  position: relative;
  transition: all var(--duration-normal);
  overflow: hidden;
  backdrop-filter: blur(10px);
  cursor: pointer;
}

.stats-card:hover {
  transform: translateY(-8px);
  box-shadow: var(--shadow-xl), var(--glow-primary);
  border-color: var(--primary-color);
  background: var(--bg-card-hover);
}

/* === 背景特效 === */
.card-bg-effect {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  opacity: 0.1;
}

.bg-grid {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image:
    linear-gradient(rgba(108, 92, 231, 0.1) 1px, transparent 1px),
    linear-gradient(90deg, rgba(108, 92, 231, 0.1) 1px, transparent 1px);
  background-size: 20px 20px;
  animation: grid-shift 10s linear infinite;
}

@keyframes grid-shift {
  0% { transform: translate(0, 0); }
  100% { transform: translate(20px, 20px); }
}

.bg-glow {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 200px;
  height: 200px;
  background: radial-gradient(circle, rgba(108, 92, 231, 0.1) 0%, transparent 70%);
  animation: glow-pulse 4s ease-in-out infinite;
}

@keyframes glow-pulse {
  0%, 100% { opacity: 0.3; transform: translate(-50%, -50%) scale(0.8); }
  50% { opacity: 0.6; transform: translate(-50%, -50%) scale(1.2); }
}

.scan-line {
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 2px;
  background: var(--primary-gradient);
  animation: scan 3s ease-in-out infinite;
  opacity: 0.6;
}

@keyframes scan {
  0% { left: -100%; }
  100% { left: 100%; }
}

/* === 图标区域 === */
.card-icon {
  width: 72px;
  height: 72px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: var(--spacing-lg);
  position: relative;
  box-shadow: var(--shadow-lg);
  overflow: hidden;
}

.icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  color: var(--text-primary);
  position: relative;
  z-index: 2;
  text-shadow: 0 0 10px rgba(255, 255, 255, 0.3);
}

.icon-pulse {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 40px;
  height: 40px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  animation: icon-pulse 2s ease-in-out infinite;
}

@keyframes icon-pulse {
  0%, 100% { opacity: 0.4; transform: translate(-50%, -50%) scale(0.8); }
  50% { opacity: 0.8; transform: translate(-50%, -50%) scale(1.2); }
}

.icon-corner {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 8px;
  height: 8px;
  border-top: 2px solid rgba(255, 255, 255, 0.4);
  border-right: 2px solid rgba(255, 255, 255, 0.4);
}

/* === 内容区域 === */
.card-content {
  flex: 1;
  position: relative;
  z-index: 2;
}

.card-title {
  margin-bottom: var(--spacing-md);
  position: relative;
}

.title-text {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 1px;
  transition: color var(--duration-normal);
}

.stats-card:hover .title-text {
  color: var(--text-primary);
}

.title-underline {
  position: absolute;
  bottom: -4px;
  left: 0;
  height: 2px;
  width: 0;
  background: var(--primary-gradient);
  transition: width var(--duration-normal);
}

.stats-card:hover .title-underline {
  width: 100%;
}

/* === 数字区域 === */
.card-count {
  display: flex;
  align-items: baseline;
  gap: var(--spacing-md);
}

.count-wrapper {
  display: flex;
  align-items: baseline;
  gap: var(--spacing-xs);
}

.count-value {
  font-size: 32px;
  font-weight: 700;
  color: var(--text-primary);
  font-family: var(--font-mono);
  text-shadow: 0 0 10px rgba(108, 92, 231, 0.3);
  transition: all var(--duration-normal);
}

.stats-card:hover .count-value {
  color: var(--primary-light);
  transform: scale(1.05);
}

.card-suffix {
  font-size: 16px;
  color: var(--text-secondary);
  font-weight: 500;
  margin-left: var(--spacing-xs);
}

/* === 指示器 === */
.count-indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  margin-top: var(--spacing-sm);
}

.indicator-dot {
  width: 6px;
  height: 6px;
  background: var(--primary-color);
  border-radius: 50%;
  animation: indicator-pulse 2s ease-in-out infinite;
  box-shadow: var(--glow-primary);
}

@keyframes indicator-pulse {
  0%, 100% { opacity: 0.4; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1.2); }
}

.indicator-line {
  width: 1px;
  height: 20px;
  background: linear-gradient(to bottom, var(--primary-color), transparent);
  opacity: 0.6;
}

/* === 科技角标 === */
.tech-corner {
  position: absolute;
  top: 0;
  right: 0;
  width: 20px;
  height: 20px;
  pointer-events: none;
}

.corner-line-1,
.corner-line-2 {
  position: absolute;
  background: var(--primary-color);
  opacity: 0.6;
  transition: all var(--duration-normal);
}

.corner-line-1 {
  top: 0;
  right: 0;
  width: 20px;
  height: 1px;
}

.corner-line-2 {
  top: 0;
  right: 0;
  width: 1px;
  height: 20px;
}

.stats-card:hover .corner-line-1,
.stats-card:hover .corner-line-2 {
  opacity: 1;
  background: var(--primary-light);
  box-shadow: var(--glow-primary);
}

/* === 响应式设计 === */
@media (max-width: 768px) {
  .stats-card {
    padding: var(--spacing-md);
  }

  .card-icon {
    width: 60px;
    height: 60px;
    margin-right: var(--spacing-md);
  }

  .icon-wrapper {
    font-size: 24px;
  }

  .count-value {
    font-size: 28px;
  }

  .title-text {
    font-size: 12px;
  }
}

@media (max-width: 480px) {
  .stats-card {
    padding: var(--spacing-sm);
    flex-direction: column;
    text-align: center;
  }

  .card-icon {
    margin-right: 0;
    margin-bottom: var(--spacing-md);
  }

  .count-indicator {
    display: none;
  }
}

/* === 加载状态 === */
.stats-card.loading {
  pointer-events: none;
}

.stats-card.loading .count-value {
  background: var(--loading-shimmer);
  color: transparent;
  border-radius: var(--radius-sm);
  animation: shimmer 1.5s infinite;
}

.stats-card.loading .title-text {
  background: var(--loading-shimmer);
  color: transparent;
  border-radius: var(--radius-sm);
  animation: shimmer 1.5s infinite;
  animation-delay: 0.2s;
}
</style>