import type { Resume, Vacancy } from '../types/api'
import { ApiError, request, requestJson } from './client'
import { getSession } from './session'

export function resumeLocation(location: string | null) {
  if (!location) return null
  try {
    const url = new URL(location, 'http://local.invalid')
    return /^\/resumes\/[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(url.pathname) && !url.search && !url.hash && /^https?:$/.test(url.protocol) ? url.pathname : null
  } catch {
    return null
  }
}

function cleanFilename(value: string) {
  const filename = value.replace(/\\/g, '/').split('/').pop() || ''
  return Array.from(filename).filter((character) => character.charCodeAt(0) >= 32 && character.charCodeAt(0) !== 127).join('').trim()
}

export function resumeName(resume: Resume) {
  try {
    return cleanFilename(decodeURIComponent(new URL(resume.file_url).pathname.split('/').pop() || '')) || 'Резюме'
  } catch {
    return 'Резюме'
  }
}

export function downloadName(disposition: string | null, fallback: string) {
  const encoded = disposition?.match(/filename\*\s*=\s*UTF-8''([^;]+)/i)?.[1]
  if (encoded) {
    try {
      return cleanFilename(decodeURIComponent(encoded.trim())) || fallback
    } catch {
      return fallback
    }
  }
  const plain = disposition?.match(/filename\s*=\s*(?:"([^"]+)"|([^;]+))/i)
  return cleanFilename(plain?.[1] || plain?.[2] || '') || fallback
}

export async function addResume(file: File) {
  const body = new FormData()
  body.append('file', file)
  const response = await request('/resumes', { method: 'POST', body })
  return resumeLocation(response.headers.get('Location'))
}

export const getResumes = (signal?: AbortSignal) => requestJson<Resume[]>('/resumes', { signal })
export const getVacancies = (signal?: AbortSignal) => requestJson<Vacancy[]>('/vacancies', { signal })
export const getVacancy = (id: string, signal?: AbortSignal) => requestJson<Vacancy>(`/vacancies/${id}`, { signal })
export const addVacancy = (text: string) => requestJson<Vacancy>('/vacancies', { method: 'POST', json: { text } })

export async function downloadResume(id: string, fallback: string, signal?: AbortSignal) {
  const generation = getSession().generation
  const response = await request(`/resumes/${id}`, { signal })
  const blob = await response.blob()
  if (signal?.aborted || generation !== getSession().generation) throw new ApiError('Скачивание отменено.')
  const filename = downloadName(response.headers.get('Content-Disposition'), fallback)
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.append(link)
  try {
    link.click()
  } finally {
    link.remove()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
  return filename
}
