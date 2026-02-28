<template>
  <div class="app-container">
    <!-- 科技风背景装饰 -->
    <div class="tech-background">
      <div class="tech-grid"></div>
      <div class="tech-particles"></div>
    </div>

    <!-- 导航栏 -->
    <nav class="app-nav tech-nav">
      <div class="nav-logo">
        <span class="logo-icon">◉</span>
        <span class="logo-text">AllStarLink</span>
        <div class="logo-glow"></div>
      </div>
      <ul class="nav-menu">
        <li>
          <router-link to="/" active-class="active">
            <span class="nav-icon">⌘</span>
            <span>首页</span>
          </router-link>
        </li>
        <li>
          <router-link to="/nodes" active-class="active">
            <span class="nav-icon">◯</span>
            <span>节点列表</span>
          </router-link>
        </li>
        <li>
          <router-link to="/stats" active-class="active">
            <span class="nav-icon">▲</span>
            <span>统计分析</span>
          </router-link>
        </li>
        <li>
          <router-link to="/about" active-class="active">
            <span class="nav-icon">ℹ</span>
            <span>关于</span>
          </router-link>
        </li>
      </ul>
    </nav>

    <!-- 主内容区 -->
    <main class="main-content">
      <div class="content-wrapper">
        <router-view />
      </div>
    </main>

    <!-- 页脚 -->
    <footer class="app-footer tech-footer">
      <div class="footer-content">
        <div class="footer-line"></div>
        <p class="footer-text">
          <span class="footer-brand">AllStarLink</span>
          <span class="footer-separator">∘</span>
          <span class="footer-desc">全球节点仪表盘</span>
          <span class="footer-year">© 2026</span>
        </p>
        <div class="footer-tech-indicator">
          <div class="tech-dot"></div>
          <div class="tech-dot"></div>
          <div class="tech-dot"></div>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
// App根组件
</script>

<style>
/* === 应用容器 === */
.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  position: relative;
  background: var(--bg-primary);
  overflow-x: hidden;
}

/* === 科技风背景 === */
.tech-background {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  z-index: -1;
}

.tech-grid {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image:
    linear-gradient(rgba(139, 92, 246, 0.2) 1px, transparent 1px),
    linear-gradient(90deg, rgba(139, 92, 246, 0.2) 1px, transparent 1px);
  background-size: 50px 50px;
  animation: grid-move 20s linear infinite;
}

@keyframes grid-move {
  0% { transform: translate(0, 0); }
  100% { transform: translate(50px, 50px); }
}

.tech-particles {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background:
    radial-gradient(2px 2px at 100px 150px, rgba(139, 92, 246, 0.3), transparent),
    radial-gradient(1px 1px at 300px 250px, rgba(168, 85, 247, 0.2), transparent),
    radial-gradient(1px 1px at 500px 350px, rgba(147, 51, 234, 0.2), transparent),
    radial-gradient(2px 2px at 800px 100px, rgba(139, 92, 246, 0.25), transparent);
  animation: particle-float 15s ease-in-out infinite alternate;
}

@keyframes particle-float {
  0% { opacity: 0.3; transform: translateY(0px); }
  100% { opacity: 0.8; transform: translateY(-10px); }
}

/* === 科技风导航栏 === */
.tech-nav {
  background: rgba(58, 43, 82, 0.95);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--border-primary);
  box-shadow:
    0 4px 20px rgba(139, 92, 246, 0.3),
    inset 0 1px 0 rgba(139, 92, 246, 0.2);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 var(--spacing-xl);
  height: 70px;
  position: relative;
  z-index: 100;
}

.tech-nav::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: var(--primary-gradient);
  opacity: 0.6;
}

/* === Logo 设计 === */
.nav-logo {
  display: flex;
  align-items: center;
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  position: relative;
  cursor: pointer;
  transition: all var(--duration-normal);
}

.logo-icon {
  font-size: 28px;
  color: var(--primary-color);
  margin-right: var(--spacing-sm);
  animation: logo-pulse 3s ease-in-out infinite;
  text-shadow: 0 0 10px rgba(108, 92, 231, 0.5);
}

@keyframes logo-pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

.logo-text {
  background: var(--primary-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: -0.5px;
}

.logo-glow {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 100%;
  height: 100%;
  background: var(--primary-gradient);
  opacity: 0;
  border-radius: var(--radius-lg);
  filter: blur(20px);
  transition: opacity var(--duration-normal);
  z-index: -1;
}

.nav-logo:hover .logo-glow {
  opacity: 0.2;
}

/* === 导航菜单 === */
.nav-menu {
  display: flex;
  list-style: none;
  align-items: center;
  gap: var(--spacing-lg);
}

.nav-menu li {
  position: relative;
}

.nav-menu a {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  text-decoration: none;
  color: var(--text-secondary);
  font-size: 16px;
  font-weight: 500;
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-md);
  transition: all var(--duration-normal);
  position: relative;
  overflow: hidden;
}

.nav-menu a::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: var(--primary-gradient);
  opacity: 0.1;
  transition: left var(--duration-normal);
}

.nav-menu a:hover::before {
  left: 0;
}

.nav-icon {
  font-size: 18px;
  color: var(--primary-color);
  transition: all var(--duration-normal);
}

.nav-menu a:hover,
.nav-menu a.active {
  color: var(--text-primary);
  background: rgba(108, 92, 231, 0.1);
  box-shadow: var(--glow-primary);
  transform: translateY(-2px);
}

.nav-menu a:hover .nav-icon,
.nav-menu a.active .nav-icon {
  color: var(--primary-light);
  text-shadow: var(--glow-primary);
}

.nav-menu a.active {
  background: var(--primary-gradient);
  color: var(--text-primary);
  box-shadow: var(--shadow-md), var(--glow-primary);
}

.nav-menu a.active .nav-icon {
  color: var(--text-primary);
}

/* === 主内容区 === */
.main-content {
  flex: 1;
  padding: var(--spacing-xl);
  position: relative;
  z-index: 1;
}

.content-wrapper {
  max-width: 1400px;
  margin: 0 auto;
  animation: content-fade-in 0.8s ease-out;
}

@keyframes content-fade-in {
  0% {
    opacity: 0;
    transform: translateY(20px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

/* === 科技风页脚 === */
.tech-footer {
  background: rgba(58, 43, 82, 0.95);
  backdrop-filter: blur(20px);
  border-top: 1px solid var(--border-primary);
  padding: var(--spacing-xl);
  position: relative;
}

.tech-footer::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: var(--primary-gradient);
  opacity: 0.4;
}

.footer-content {
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-md);
}

.footer-line {
  width: 60px;
  height: 2px;
  background: var(--primary-gradient);
  border-radius: var(--radius-full);
  margin-bottom: var(--spacing-sm);
}

.footer-text {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  color: var(--text-secondary);
  font-size: 14px;
  margin: 0;
}

.footer-brand {
  color: var(--primary-color);
  font-weight: 600;
  text-shadow: var(--glow-primary);
}

.footer-separator {
  color: var(--primary-light);
  font-size: 12px;
}

.footer-desc {
  color: var(--text-secondary);
}

.footer-year {
  color: var(--text-disabled);
  font-size: 12px;
}

.footer-tech-indicator {
  display: flex;
  gap: var(--spacing-sm);
  align-items: center;
}

.tech-dot {
  width: 6px;
  height: 6px;
  background: var(--primary-color);
  border-radius: 50%;
  animation: tech-dot-pulse 2s ease-in-out infinite;
  box-shadow: var(--glow-primary);
}

.tech-dot:nth-child(2) {
  animation-delay: 0.5s;
}

.tech-dot:nth-child(3) {
  animation-delay: 1s;
}

@keyframes tech-dot-pulse {
  0%, 100% {
    opacity: 0.4;
    transform: scale(0.8);
  }
  50% {
    opacity: 1;
    transform: scale(1.2);
  }
}

/* === 响应式设计 === */
@media (max-width: 768px) {
  .tech-nav {
    padding: 0 var(--spacing-md);
    height: 60px;
    flex-direction: column;
    align-items: stretch;
    height: auto;
    min-height: 60px;
  }

  .nav-logo {
    font-size: 20px;
    justify-content: center;
    padding: var(--spacing-md) 0;
  }

  .nav-menu {
    justify-content: center;
    flex-wrap: wrap;
    gap: var(--spacing-md);
    padding-bottom: var(--spacing-md);
  }

  .nav-menu a {
    font-size: 14px;
    padding: var(--spacing-sm);
  }

  .main-content {
    padding: var(--spacing-md);
  }

  .footer-text {
    flex-direction: column;
    gap: var(--spacing-sm);
    text-align: center;
  }

  .tech-grid {
    background-size: 30px 30px;
  }
}

@media (max-width: 480px) {
  .nav-menu {
    gap: var(--spacing-sm);
  }

  .nav-menu a span:not(.nav-icon) {
    display: none;
  }

  .logo-text {
    font-size: 18px;
  }

  .main-content {
    padding: var(--spacing-sm);
  }
}

/* === 滚动条优化 === */
.content-wrapper {
  scrollbar-width: thin;
  scrollbar-color: var(--primary-color) var(--bg-secondary);
}

/* === 加载动画 === */
.loading-shimmer {
  background: linear-gradient(
    90deg,
    transparent,
    rgba(108, 92, 231, 0.1),
    transparent
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% {
    background-position: -200% center;
  }
  100% {
    background-position: 200% center;
  }
}
</style>