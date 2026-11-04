import type { Adaptation, Vacancy } from '../types/api'

type Draft = { userId: string; vacancy: string; savedVacancy: Vacancy | null; resume: File | null; sourceId: string; versions: (Adaptation & { title?: string })[] }
let draft: Draft = { userId: '', vacancy: '', savedVacancy: null, resume: null, sourceId: '', versions: [] }
const listeners = new Set<() => void>()

export function subscribeDrafts(listener: () => void) {
  listeners.add(listener)
  return () => { listeners.delete(listener) }
}

export function getDraft(userId: string) {
  if (draft.userId !== userId) draft = { userId, vacancy: '', savedVacancy: null, resume: null, sourceId: '', versions: [] }
  return draft
}

export function clearDrafts() {
  draft = { userId: '', vacancy: '', savedVacancy: null, resume: null, sourceId: '', versions: [] }
  listeners.forEach((listener) => listener())
}

export function rememberVersion(userId: string, version: Adaptation, title?: string) {
  const current = getDraft(userId)
  const existing = current.versions.find((item) => item.id === version.id)
  const name = title || existing?.title
  current.versions = [name ? { ...version, title: name } : version, ...current.versions.filter((item) => item.id !== version.id)]
  listeners.forEach((listener) => listener())
}
