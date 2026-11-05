/// <reference types="vite/client" />

import 'vue-router'

declare module 'vue-router' {
  interface RouteMeta {
    public?: boolean
    bare?: boolean
    admin?: boolean
    allowNoWorkspace?: boolean
  }
}

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}
