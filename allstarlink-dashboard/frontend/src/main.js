import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'leaflet/dist/leaflet.css'
import './styles/theme.css'
import './styles/element-theme.css'
import './styles/table-fix.css'
import './styles/global-overrides.css'

// 创建Vue应用实例
const app = createApp(App)

// 创建并注册Pinia
const pinia = createPinia()
app.use(pinia)

// 注册插件
app.use(router)
app.use(ElementPlus)

// 挂载应用
app.mount('#app')