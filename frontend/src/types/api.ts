export type Credentials = { username: string; password: string }

export type Tokens = { access_token: string; refresh_token: string; token_type: string }

export type Profile = { user_id: string; username: string; is_staff: boolean }

export type User = Profile & { is_active: boolean }

export type Resume = {
  id: string
  user_id: string
  file_url: string
  embedding: number[] | null
  created_at: string
}

export type Vacancy = { id: string; user_id: string; text: string }
