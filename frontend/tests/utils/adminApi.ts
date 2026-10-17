import { LoginService, type Role, UsersService } from "../../src/client"
import { client } from "../../src/client/client.gen"
import { firstSuperuser, firstSuperuserPassword } from "../config.ts"

client.setConfig({
  baseURL: `${process.env.VITE_API_URL}`,
})

// Role changes and deactivation need an admin, so these helpers go through
// the real API as the first superuser (the seeded admin)
const adminHeaders = async () => {
  const { data: token } = await LoginService.loginAccessToken({
    body: { username: firstSuperuser, password: firstSuperuserPassword },
  })
  return { Authorization: `Bearer ${token.access_token}` }
}

export const createUserWithRole = async ({
  email,
  password,
  role,
}: {
  email: string
  password: string
  role: Role
}) => {
  const { data: user } = await UsersService.createUser({
    body: { email, password, role, full_name: "Test User", is_active: true },
    headers: await adminHeaders(),
  })
  return user
}

export const deactivateUser = async (userId: string) => {
  await UsersService.updateUser({
    path: { user_id: userId },
    body: { is_active: false },
    headers: await adminHeaders(),
  })
}
