import { LoginService, type Role, UsersService } from "../../src/client"
import { client } from "../../src/client/client.gen"
import { firstSuperuser, firstSuperuserPassword } from "../config.ts"

client.setConfig({
  baseURL: `${process.env.VITE_API_URL}`,
})

// Users with a role other than member can only be created by an admin, so
// this goes through the real API as the first superuser (the seeded admin)
export const createUserWithRole = async ({
  email,
  password,
  role,
}: {
  email: string
  password: string
  role: Role
}) => {
  const { data: token } = await LoginService.loginAccessToken({
    body: { username: firstSuperuser, password: firstSuperuserPassword },
  })
  const { data: user } = await UsersService.createUser({
    body: { email, password, role, full_name: "Test User", is_active: true },
    headers: { Authorization: `Bearer ${token.access_token}` },
  })
  return user
}
