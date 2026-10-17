import type { QueryClient } from "@tanstack/react-query"

import type { Permission, UserMe } from "@/client"

/**
 * Whether the user's role grants the permission. The backend computes the
 * permission list on /users/me, so the frontend never re-implements the
 * role -> permission map. UI gating only; the backend enforces every check.
 */
export const can = (
  user: UserMe | null | undefined,
  permission: Permission,
): boolean => user?.permissions.includes(permission) ?? false

/** Router context: route guards read the current user through it. */
export interface RouterContext {
  queryClient: QueryClient
}
