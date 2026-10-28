import type { Page } from '@playwright/test'

export const userId = '11111111-1111-4111-8111-111111111111'
export const vacancyId = '22222222-2222-4222-8222-222222222222'
export const missingId = '99999999-9999-4999-8999-999999999999'
export const profile = { user_id: userId, username: 'browser-test', is_staff: false }
export const tokens = { access_token: 'test-access', refresh_token: 'test-refresh', token_type: 'bearer' }

export async function mockApi(page: Page, role: 'anonymous' | 'nonstaff' | 'staff' = 'nonstaff') {
  const state = {
    profile: { ...profile, is_staff: role === 'staff' },
    userCalls: [] as string[],
    usersStatus: 0,
    usersDelay: 0,
    meDelay: 0,
    resumes: [] as { id: string; user_id: string; file_url: string; embedding: null; created_at: string; bytes: Buffer; name: string }[],
    vacancies: [] as { id: string; user_id: string; text: string }[],
    expired: false,
    refreshFailure: false,
    offline: false,
    postStatus: 0,
    refreshes: 0,
    posts: 0,
    refreshDelay: 0,
    emptyUsers: false,
    postDelay: 0,
  }
  if (role !== 'anonymous') await page.addInitScript((value) => {
    if (!sessionStorage.getItem('test-seeded')) {
      sessionStorage.setItem('access_token', value.access_token)
      sessionStorage.setItem('refresh_token', value.refresh_token)
      sessionStorage.setItem('test-seeded', 'true')
    }
  }, tokens)
  await page.route(/\/(auth|resumes|vacancies)(\/|$)/, async (route) => {
    const request = route.request()
    const path = new URL(request.url()).pathname
    const respond = (body: unknown, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) })
    if (path.startsWith('/auth/users')) state.userCalls.push(path)
    if (state.offline) return route.abort('connectionrefused')
    if (path === '/auth/register') return respond({ user_id: userId, username: profile.username }, 201)
    if (path === '/auth/login') return respond(tokens)
    if (path === '/auth/refresh') {
      state.refreshes++
      if (state.refreshDelay) await new Promise((resolve) => setTimeout(resolve, state.refreshDelay))
      if (state.refreshFailure) return respond({}, 500)
      state.expired = false
      return respond({ ...tokens, access_token: 'refreshed-access' })
    }
    if (!request.headers().authorization || state.expired) return respond({}, 401)
    if (path === '/auth/me') {
      const current = { ...state.profile }
      if (state.meDelay) await new Promise((resolve) => setTimeout(resolve, state.meDelay))
      return respond(current)
    }
    if (path.startsWith('/auth/users')) {
      const current = { ...state.profile, is_active: true }
      if (state.usersDelay) await new Promise((resolve) => setTimeout(resolve, state.usersDelay))
      if (state.usersStatus || !current.is_staff) return respond({}, state.usersStatus || 403)
      if (path === '/auth/users') return respond(state.emptyUsers ? [] : [current])
      if (path === `/auth/users/${current.user_id}`) return respond(current)
      return respond({}, 404)
    }
    if (path === '/resumes' && request.method() === 'POST') {
      state.posts++
      if (state.postDelay) await new Promise((resolve) => setTimeout(resolve, state.postDelay))
      if (state.postStatus) return respond({}, state.postStatus)
      const body = request.postDataBuffer()!
      const name = body.toString('utf8').match(/filename="([^"]+)"/)?.[1] || 'resume.pdf'
      const start = body.indexOf('\r\n\r\n') + 4
      const boundary = request.headers()['content-type'].split('boundary=')[1]
      const end = body.indexOf(`\r\n--${boundary}`, start)
      const id = `${state.resumes.length + 3}3333333-3333-4333-8333-333333333333`
      state.resumes.push({ id, user_id: userId, file_url: `http://minio:9000/resumes/internal/key/${encodeURIComponent(name)}`, embedding: null, created_at: '2026-10-25T10:00:00Z', bytes: body.subarray(start, end), name })
      return route.fulfill({ status: 201, headers: { Location: `http://resume:8000/resumes/${id}` }, body: '' })
    }
    if (path === '/resumes') return respond(state.resumes.map(({ bytes, name, ...resume }) => { void bytes; void name; return resume }))
    if (path.startsWith('/resumes/')) {
      const resume = state.resumes.find((item) => path.endsWith(item.id))
      return resume ? route.fulfill({ status: 200, body: resume.bytes, headers: { 'Content-Type': resume.name.endsWith('.pdf') ? 'application/pdf' : 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'Content-Disposition': `attachment; filename*=UTF-8''${encodeURIComponent(resume.name)}` } }) : respond({}, 404)
    }
    if (path === '/vacancies' && request.method() === 'POST') {
      state.posts++
      if (state.postDelay) await new Promise((resolve) => setTimeout(resolve, state.postDelay))
      if (state.postStatus) return respond({}, state.postStatus)
      const vacancy = { id: vacancyId, user_id: userId, text: request.postDataJSON().text }
      state.vacancies.push(vacancy)
      return respond(vacancy, 201)
    }
    if (path === '/vacancies') return respond(state.vacancies)
    if (path === `/vacancies/${vacancyId}` && state.vacancies.length) return respond(state.vacancies[0])
    return respond({}, 404)
  })
  return state
}
