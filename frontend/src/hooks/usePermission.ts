import type { Permission, UserMe } from "@/client"
import useAuth from "./useAuth"

/**
 * Whether the user's role grants the permission. The backend computes the
 * permission list on /users/me, so the frontend never re-implements the
 * role -> permission map. UI gating only; the backend enforces every check.
 */
export const can = (
  user: UserMe | null | undefined,
  permission: Permission,
): boolean => user?.permissions.includes(permission) ?? false

const usePermission = (permission: Permission): boolean => {
  const { user } = useAuth()
  return can(user, permission)
}

export default usePermission
