<template>
  <div class="about-container">
    <h2 class="page-title">关于AllStarLink节点仪表盘</h2>
    
    <el-card shadow="hover" class="about-card">
      <template #header>
        <div class="card-header">
          <span>项目介绍</span>
        </div>
      </template>
      <div class="about-content">
        <p>AllStarLink节点仪表盘是一个用于可视化AllStarLink网络节点数据的Web应用程序。它提供了实时的节点分布、活跃度统计和地理可视化功能。</p>
        <p>该项目旨在帮助用户更好地了解AllStarLink网络的状态和分布情况，便于网络管理员和用户监控节点活动。</p>
      </div>
    </el-card>

    <el-card shadow="hover" class="about-card">
      <template #header>
        <div class="card-header">
          <span>技术栈</span>
        </div>
      </template>
      <div class="tech-stack">
        <div class="tech-item">
          <h4>前端</h4>
          <ul>
            <li>Vue 3 - 渐进式JavaScript框架</li>
            <li>Element Plus - UI组件库</li>
            <li>Leaflet - 开源JavaScript地图库</li>
            <li>ECharts - 数据可视化图表库</li>
            <li>Vue Router - 路由管理</li>
            <li>Pinia - 状态管理</li>
            <li>Vite - 构建工具</li>
          </ul>
        </div>
        <div class="tech-item">
          <h4>后端</h4>
          <ul>
            <li>Spring Boot 2.7 - Java Web框架</li>
            <li>Spring Data JPA - 数据库访问</li>
            <li>MySQL - 关系型数据库</li>
            <li>Redis - 缓存系统</li>
            <li>Maven - 项目管理工具</li>
          </ul>
        </div>
        <div class="tech-item">
          <h4>爬虫</h4>
          <ul>
            <li>Python 3 - 编程语言</li>
            <li>Requests - HTTP请求库</li>
            <li>BeautifulSoup - HTML解析库</li>
            <li>pymysql - MySQL数据库驱动</li>
            <li>Schedule - 定时任务库</li>
          </ul>
        </div>
      </div>
    </el-card>

    <el-card shadow="hover" class="about-card">
      <template #header>
        <div class="card-header">
          <span>功能特性</span>
        </div>
      </template>
      <div class="features">
        <el-row :gutter="20">
          <el-col :span="8">
            <div class="feature-item">
              <div class="feature-icon">
                <el-icon><data-line /></el-icon>
              </div>
              <h4>实时统计</h4>
              <p>查看节点总数、活跃节点数和活跃比例</p>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="feature-item">
              <div class="feature-icon">
                <el-icon><location /></el-icon>
              </div>
              <h4>地理分布</h4>
              <p>在地图上可视化节点的地理位置分布</p>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="feature-item">
              <div class="feature-icon">
                <el-icon><pie-chart /></el-icon>
              </div>
              <h4>数据图表</h4>
              <p>通过柱状图和饼图展示节点分布情况</p>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="feature-item">
              <div class="feature-icon">
                <el-icon><timer /></el-icon>
              </div>
              <h4>时间范围</h4>
              <p>支持不同时间范围的活跃节点统计</p>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="feature-item">
              <div class="feature-icon">
                <el-icon><document /></el-icon>
              </div>
              <h4>节点详情</h4>
              <p>查看单个节点的详细信息</p>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="feature-item">
              <div class="feature-icon">
                <el-icon><refresh /></el-icon>
              </div>
              <h4>定时更新</h4>
              <p>自动定时从AllStarLink服务器获取最新数据</p>
            </div>
          </el-col>
        </el-row>
      </div>
    </el-card>

    <el-card shadow="hover" class="about-card">
      <template #header>
        <div class="card-header">
          <span>项目信息</span>
        </div>
      </template>
      <div class="project-info">
        <p><strong>版本：</strong>1.0.0</p>
        <p><strong>作者：</strong>AllStarLink节点仪表盘开发团队</p>
        <p><strong>开源协议：</strong>MIT License</p>
        <p><strong>更新日期：</strong>2026年1月</p>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { DataLine, Location, PieChart, Timer, Document, Refresh } from '@element-plus/icons-vue'
</script>

<style scoped>
.about-container {
  padding: 0 20px;
}

.page-title {
  font-size: 24px;
  margin-bottom: 20px;
  color: #303133;
}

.about-card {
  margin-bottom: 20px;
}

.about-content p {
  margin-bottom: 15px;
  line-height: 1.8;
  color: #606266;
}

/* 技术栈 */
.tech-stack {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
}

.tech-item h4 {
  margin-bottom: 10px;
  color: #303133;
  font-size: 16px;
}

.tech-item ul {
  list-style-type: disc;
  padding-left: 20px;
}

.tech-item li {
  margin-bottom: 8px;
  color: #606266;
}

/* 功能特性 */
.features {
  padding: 10px 0;
}

.feature-item {
  text-align: center;
  padding: 20px;
  background-color: #f5f7fa;
  border-radius: 8px;
  transition: transform 0.3s, box-shadow 0.3s;
}

.feature-item:hover {
  transform: translateY(-5px);
  box-shadow: 0 12px 20px rgba(0, 0, 0, 0.1);
}

.feature-icon {
  font-size: 48px;
  margin-bottom: 15px;
  color: #409EFF;
}

.feature-item h4 {
  margin-bottom: 10px;
  color: #303133;
}

.feature-item p {
  color: #606266;
  font-size: 14px;
}

/* 项目信息 */
.project-info p {
  margin-bottom: 10px;
  color: #606266;
}

.project-info strong {
  color: #303133;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .tech-stack {
    grid-template-columns: 1fr;
  }
  
  .feature-item {
    margin-bottom: 20px;
  }
}
</style>