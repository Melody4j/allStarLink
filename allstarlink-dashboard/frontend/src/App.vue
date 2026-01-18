<template>
  <div class="app-container">
    <!-- 导航栏 -->
    <nav class="app-nav">
      <div class="nav-logo">AllStarLink</div>
      <ul class="nav-menu">
        <li>
          <router-link to="/" active-class="active">首页</router-link>
        </li>
        <li>
          <router-link to="/nodes" active-class="active">节点列表</router-link>
        </li>
        <li>
          <router-link to="/stats" active-class="active">统计分析</router-link>
        </li>
        <li>
          <router-link to="/about" active-class="active">关于</router-link>
        </li>
      </ul>
    </nav>

    <!-- 主内容区 -->
    <main class="main-content">
      <router-view />
    </main>

    <!-- 页脚 -->
    <footer class="app-footer">
      <p>AllStarLink节点仪表盘 &copy; 2026</p>
    </footer>
  </div>
</template>

<script setup>
// App根组件
</script>

<style>
/* 全局样式 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
  background-color: #f5f7fa;
  color: #303133;
}

/* 应用容器 */
.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* 导航栏 */
.app-nav {
  background-color: #fff;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  height: 60px;
}

.nav-logo {
  font-size: 20px;
  font-weight: bold;
  color: #409EFF;
}

.nav-menu {
  display: flex;
  list-style: none;
}

.nav-menu li {
  margin-left: 30px;
}

.nav-menu a {
  text-decoration: none;
  color: #606266;
  font-size: 16px;
  transition: color 0.3s;
}

.nav-menu a:hover,
.nav-menu a.active {
  color: #409EFF;
}

/* 主内容区 */
.main-content {
  flex: 1;
  padding: 20px;
}

/* 页脚 */
.app-footer {
  background-color: #fff;
  text-align: center;
  padding: 20px;
  color: #909399;
  font-size: 14px;
  border-top: 1px solid #ebeef5;
}
</style>