import { http } from './http'

export async function login(payload) {
  const { data } = await http.post('/auth/login', payload)
  return data
}

export async function register(payload) {
  const { data } = await http.post('/auth/register', payload)
  return data
}

export async function getCurrentUser() {
  const { data } = await http.get('/auth/me')
  return data
}
