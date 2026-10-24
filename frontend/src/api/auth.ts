type Credentials = {
  username: string
  password: string
}

type LoginResponse = {
  access_token: string
  refresh_token: string
  token_type: string
}

type RegisterResponse = {
  user_id: string
  username: string
}

async function postAuth<T>(path: string, credentials: Credentials): Promise<T> {
  let response: Response

  try {
    response = await fetch(`/auth/${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(credentials),
    })
  } catch {
    throw new Error('Не удалось связаться с сервером. Попробуйте позже.')
  }

  if (!response.ok) {
    if (path === 'login' && response.status === 401) {
      throw new Error('Неверное имя пользователя или пароль.')
    }

    if (path === 'register' && response.status === 400) {
      throw new Error('Это имя пользователя уже занято.')
    }

    throw new Error('Не удалось выполнить запрос. Попробуйте позже.')
  }

  return response.json() as Promise<T>
}

export function login(credentials: Credentials) {
  return postAuth<LoginResponse>('login', credentials)
}

export function register(credentials: Credentials) {
  return postAuth<RegisterResponse>('register', credentials)
}
