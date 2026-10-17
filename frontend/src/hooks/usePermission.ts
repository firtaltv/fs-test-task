import type { Permission } from "@/client"
import { can } from "@/lib/permissions"
import useAuth from "./useAuth"

/** React wrapper around can() for the signed-in user. */
const usePermission = (permission: Permission): boolean => {
  const { user } = useAuth()
  return can(user, permission)
}

export default usePermission
