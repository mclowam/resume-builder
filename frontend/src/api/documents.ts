export class DocumentApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

type Vacancy = {
  id: string
  text: string
}

async function sendDocument(path: string, body: BodyInit, contentType?: string) {
  const token = sessionStorage.getItem('access_token')

  if (!token) {
    throw new DocumentApiError('Войдите в аккаунт, чтобы продолжить.', 401)
  }

  let response: Response

  try {
    response = await fetch(path, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        ...(contentType ? { 'Content-Type': contentType } : {}),
      },
      body,
    })
  } catch {
    throw new Error('Не удалось связаться с сервером. Попробуйте позже.')
  }

  if (response.status === 401) {
    throw new DocumentApiError('Сессия истекла. Войдите снова.', 401)
  }

  if (!response.ok) {
    const message = response.status === 422
      ? path === '/resumes'
        ? 'Файл должен быть действительным PDF или DOCX.'
        : 'Проверьте текст вакансии.'
      : response.status === 413
        ? 'Файл слишком большой.'
        : 'Не удалось сохранить данные. Попробуйте позже.'

    throw new DocumentApiError(message, response.status)
  }

  return response
}

export async function addResume(file: File) {
  const body = new FormData()
  body.append('file', file)
  await sendDocument('/resumes', body)
}

export async function addVacancy(text: string): Promise<Vacancy> {
  const response = await sendDocument('/vacancies', JSON.stringify({ text }), 'application/json')
  return response.json() as Promise<Vacancy>
}
