let draft: { userId: string; vacancy: string; resume: File | null } = { userId: '', vacancy: '', resume: null }

export function getDraft(userId: string) {
  if (draft.userId !== userId) draft = { userId, vacancy: '', resume: null }
  return draft
}

export function clearDrafts() {
  draft = { userId: '', vacancy: '', resume: null }
}
