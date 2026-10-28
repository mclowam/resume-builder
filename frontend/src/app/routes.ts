const uuid = '[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}'
const detail = new RegExp(`^/(my-vacancies|users)/(${uuid})$`, 'i')
const protectedPaths = ['/my-resumes', '/my-vacancies', '/add-resume', '/add-vacancy', '/profile', '/users']

export function matchRoute(path: string) {
  if (['/', '/login', '/register', ...protectedPaths].includes(path)) return { path, id: null, protected: protectedPaths.includes(path), staff: path === '/users' }
  const match = path.match(detail)
  return match ? { path: `/${match[1]}/:id`, id: match[2], protected: true, staff: match[1] === 'users' } : null
}

export function safeReturnPath(value: string | null) {
  if (!value || !matchRoute(value)?.protected) return '/my-resumes'
  return value
}

export function authPath(mode: 'login' | 'register', next: string) {
  return `/${mode}?next=${encodeURIComponent(safeReturnPath(next))}`
}
