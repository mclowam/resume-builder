import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const authApiUrl = loadEnv(mode, '.', 'AUTH_API_URL').AUTH_API_URL || 'http://localhost:8001'
  const resumeApiUrl = loadEnv(mode, '.', 'RESUME_API_URL').RESUME_API_URL || 'http://localhost:8002'

  return {
    plugins: [react()],
    server: {
      proxy: {
        '/auth': authApiUrl,
        '/resumes': resumeApiUrl,
        '/vacancies': resumeApiUrl,
      },
    },
  }
})
