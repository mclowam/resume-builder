import assert from 'node:assert/strict'
import { beforeEach, test } from 'node:test'
import { readFile, mkdir, writeFile } from 'node:fs/promises'
import ts from 'typescript'

for (const name of ['api/session', 'api/client', 'api/auth', 'api/documents', 'app/routes']) {
  const source = await readFile(new URL(`../src/${name}.ts`, import.meta.url), 'utf8')
  const output = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 } }).outputText
    .replace(/from '(\.[^']+)'/g, "from '$1.js'")
  const target = new URL(`../.test-build/${name}.js`, import.meta.url)
  await mkdir(new URL('.', target), { recursive: true })
  await writeFile(target, output)
}

const storage = new Map()
globalThis.sessionStorage = { getItem: (key) => storage.get(key) || null, setItem: (key, value) => storage.set(key, value), removeItem: (key) => storage.delete(key) }
const session = await import('../.test-build/api/session.js')
const client = await import('../.test-build/api/client.js')
const auth = await import('../.test-build/api/auth.js')
const documents = await import('../.test-build/api/documents.js')
const routes = await import('../.test-build/app/routes.js')
const oldTokens = { access_token: 'old', refresh_token: 'refresh-old', token_type: 'bearer' }
const newTokens = { access_token: 'new', refresh_token: 'refresh-new', token_type: 'bearer' }
const profile = { user_id: '11111111-1111-4111-8111-111111111111', username: 'test', is_staff: false }
const json = (value, status = 200) => new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json' } })
const deferred = () => { let resolve; const promise = new Promise((done) => { resolve = done }); return { promise, resolve } }
const tick = () => new Promise((resolve) => setImmediate(resolve))

beforeEach(() => {
  session.clearSession()
  session.setTokens(oldTokens, session.getSession().generation)
  session.setUser(profile, session.getSession().generation)
})

test('parallel and late 401 use one refresh and one retry per request', async () => {
  let refreshes = 0
  const calls = []
  const late = deferred()
  globalThis.fetch = async (path, options) => {
    calls.push([path, options.headers.Authorization])
    if (path === '/auth/refresh') {
      refreshes++
      assert.equal(options.headers.Authorization, undefined)
      assert.deepEqual(JSON.parse(options.body), { refresh_token: 'refresh-old' })
      await tick()
      return json(newTokens)
    }
    if (options.headers.Authorization === 'Bearer old') {
      if (path === '/auth/users') return late.promise
      return json({}, 401)
    }
    return json([])
  }
  const first = client.requestJson('/resumes')
  const second = client.requestJson('/vacancies')
  const third = client.requestJson('/auth/users')
  await Promise.all([first, second])
  late.resolve(json({}, 401))
  await third
  assert.equal(refreshes, 1)
  assert.equal(calls.filter(([path]) => path === '/resumes').length, 2)
  assert.equal(calls.filter(([path]) => path === '/auth/users').length, 2)
  assert.equal(session.getTokens().access_token, 'new')
})

for (const failure of [401, 500, 'network', 'malformed']) {
  test(`failed refresh (${failure}) clears session without retry loops`, async () => {
    let refreshes = 0
    globalThis.fetch = async (path) => {
      if (path !== '/auth/refresh') return json({}, 401)
      refreshes++
      await tick()
      if (failure === 'network') throw new TypeError('offline')
      return failure === 'malformed' ? json({}) : json({}, failure)
    }
    const result = await Promise.allSettled([client.request('/resumes'), client.request('/vacancies')])
    assert.ok(result.every((item) => item.status === 'rejected'))
    assert.equal(refreshes, 1)
    assert.equal(session.getTokens(), null)
    assert.equal(session.getSession().user, null)
    assert.match(session.getSession().message, /Войдите/)
  })
}

for (const switchUser of [false, true]) {
  test(`late refresh cannot restore session after ${switchUser ? 'account change' : 'logout'}`, async () => {
    const pending = deferred()
    const started = deferred()
    globalThis.fetch = async (path) => {
      if (path === '/auth/refresh') { started.resolve(); return pending.promise }
      return json({}, 401)
    }
    const result = client.request('/resumes').catch((error) => error)
    await started.promise
    auth.logout()
    if (switchUser) {
      session.setTokens({ ...newTokens, access_token: 'other' }, session.getSession().generation)
      session.setUser({ ...profile, username: 'other' }, session.getSession().generation)
    }
    pending.resolve(json(newTokens))
    assert.ok(await result instanceof client.ApiError)
    assert.equal(session.getTokens()?.access_token, switchUser ? 'other' : undefined)
    assert.equal(session.getSession().user?.username, switchUser ? 'other' : undefined)
  })
}

test('successful login checks /me before publishing user', async () => {
  const calls = []
  globalThis.fetch = async (path, options) => {
    calls.push(path)
    if (path === '/auth/login') {
      assert.equal(options.headers.Authorization, undefined)
      return json(newTokens)
    }
    assert.equal(session.getSession().user, null)
    assert.equal(options.headers.Authorization, 'Bearer new')
    return json(profile)
  }
  await auth.login({ username: 'test', password: 'password' })
  assert.deepEqual(calls, ['/auth/login', '/auth/me'])
  assert.deepEqual(session.getSession().user, profile)
})

test('a second 401 ends session after one refresh', async () => {
  const calls = []
  globalThis.fetch = async (path) => { calls.push(path); return path === '/auth/refresh' ? json(newTokens) : json({}, 401) }
  await assert.rejects(client.request('/resumes'), { status: 401 })
  assert.deepEqual(calls, ['/resumes', '/auth/refresh', '/resumes'])
  assert.equal(session.getTokens(), null)
})

test('refresh-only session does not refresh again if its access token is rejected', async () => {
  session.setTokens({ ...oldTokens, access_token: '' }, session.getSession().generation)
  const calls = []
  globalThis.fetch = async (path) => { calls.push(path); return path === '/auth/refresh' ? json(newTokens) : json({}, 401) }
  await assert.rejects(client.request('/resumes'), { status: 401 })
  assert.deepEqual(calls, ['/auth/refresh', '/resumes'])
})

for (const failure of [500, 'network']) {
  test(`POST is not repeated after ${failure}`, async () => {
    let calls = 0
    globalThis.fetch = async () => { calls++; if (failure === 'network') throw new TypeError('offline'); return json({}, 500) }
    await assert.rejects(documents.addVacancy('Full text'), { uncertain: true })
    assert.equal(calls, 1)
  })
}

test('POST resume accepts empty 201 and only extracts a safe relative Location', async () => {
  globalThis.fetch = async (path, options) => {
    assert.equal(path, '/resumes')
    assert.equal(options.method, 'POST')
    assert.equal(options.headers.Authorization, 'Bearer old')
    assert.equal(options.headers['Content-Type'], undefined)
    assert.equal(options.body.get('file').name, 'cv.pdf')
    assert.equal(options.redirect, 'error')
    return new Response(null, { status: 201, headers: { Location: `http://resume:8000/resumes/${profile.user_id}` } })
  }
  assert.equal(await documents.addResume(new File(['%PDF'], 'cv.pdf')), `/resumes/${profile.user_id}`)
  for (const value of [null, 'javascript:alert(1)', '/auth/me', '/resumes/../auth/me', `/resumes/${profile.user_id}?token=secret`, 'https://evil.invalid/steal']) assert.equal(documents.resumeLocation(value), null)
  assert.equal(documents.resumeLocation(`https://evil.invalid/resumes/${profile.user_id}`), `/resumes/${profile.user_id}`)
  await assert.rejects(client.request('https://evil.invalid/resumes'), /Недопустимый/)
  await assert.rejects(client.request('/internal/resumes'), /Недопустимый/)
})

test('POST retries only its rejected 401 and preserves the complete text', async () => {
  const text = 'Full vacancy\n\nUnchanged whitespace  '
  const calls = []
  globalThis.fetch = async (path, options) => {
    calls.push(path)
    if (path === '/auth/refresh') return json(newTokens)
    assert.deepEqual(JSON.parse(options.body), { text })
    return options.headers.Authorization === 'Bearer old' ? json({}, 401) : json({ id: profile.user_id, user_id: profile.user_id, text }, 201)
  }
  assert.equal((await documents.addVacancy(text)).text, text)
  assert.deepEqual(calls, ['/vacancies', '/auth/refresh', '/vacancies'])
})

test('authorized Blob download preserves bytes, UTF-8 filename and revokes URL', async () => {
  const bytes = new Uint8Array([37, 80, 68, 70, 0, 255])
  const filename = 'Моё резюме.pdf'
  let createdBlob, clicked = false, removed = false, revoked = false
  const link = { href: '', download: '', click: () => { clicked = true }, remove: () => { removed = true } }
  const create = URL.createObjectURL
  const revoke = URL.revokeObjectURL
  URL.createObjectURL = (blob) => { createdBlob = blob; return 'blob:test' }
  URL.revokeObjectURL = (url) => { assert.equal(url, 'blob:test'); revoked = true }
  globalThis.document = { createElement: () => link, body: { append: () => {} } }
  globalThis.fetch = async (path, options) => {
    assert.equal(path, `/resumes/${profile.user_id}`)
    assert.equal(options.headers.Authorization, 'Bearer old')
    return new Response(bytes, { headers: { 'Content-Type': 'application/pdf', 'Content-Disposition': `attachment; filename*=UTF-8''${encodeURIComponent(filename)}` } })
  }
  try {
    assert.equal(await documents.downloadResume(profile.user_id, 'fallback.pdf'), filename)
    assert.equal(link.download, filename)
    assert.ok(clicked && removed)
    assert.equal(createdBlob.type, 'application/pdf')
    assert.deepEqual(new Uint8Array(await createdBlob.arrayBuffer()), bytes)
    await new Promise((resolve) => setTimeout(resolve, 1100))
    assert.equal(revoked, true)
  } finally {
    URL.createObjectURL = create
    URL.revokeObjectURL = revoke
  }
})

test('late successful private response is discarded after logout', async () => {
  const pending = deferred()
  globalThis.fetch = () => pending.promise
  const result = client.requestJson('/vacancies').catch((error) => error)
  auth.logout()
  pending.resolve(json([{ text: 'private' }]))
  assert.ok(await result instanceof client.ApiError)
})

test('UI navigation avoids API prefixes and only accepts allowed return paths', () => {
  const paths = ['/my-resumes', '/my-vacancies', '/add-resume', '/add-vacancy', '/profile', '/users', `/users/${profile.user_id}`, `/my-vacancies/${profile.user_id}`]
  for (const path of paths) {
    assert.ok(routes.matchRoute(path).protected)
    assert.equal(routes.safeReturnPath(path), path)
    assert.equal(/^\/(auth|resumes|vacancies)/.test(path), false)
  }
  for (const path of ['//evil.invalid', 'https://evil.invalid', '/\\evil.invalid', '/auth/me', '/login', '/unknown', '/users/not-a-uuid', '/my-resumes?next=//evil.invalid']) assert.equal(routes.safeReturnPath(path), '/my-resumes')
  assert.equal(routes.matchRoute('/missing'), null)
})
