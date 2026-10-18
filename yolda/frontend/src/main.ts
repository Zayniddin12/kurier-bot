import { createApp } from 'vue'
import { createPinia } from 'pinia'
import 'leaflet/dist/leaflet.css'
import './styles/tokens.css'
import './styles/base.css'
import App from './App.vue'
import router from './router'

const app = createApp(App)
app.use(createPinia())
app.use(router)
const mods = import.meta.glob(['./components/ui/*.vue', './components/charts/*.vue'], { eager: true }) as Record<string, any>
for (const [path, m] of Object.entries(mods)) app.component(path.split('/').pop()!.replace('.vue', ''), m.default)
app.mount('#app')
