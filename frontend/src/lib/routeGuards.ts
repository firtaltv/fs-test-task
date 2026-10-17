import type { QueryClient } from "@tanstack/react-query"

import type { Permission } from "@/client"
import { currentUserQueryOptions } from "@/hooks/useAuth"
import { can } from "@/hooks/usePermission"

export interface RouterContext {
  queryClient: QueryClient
}

export class PermissionDeniedError extends Error {
  constructor(readonly permission: Permission) {
    super(`Missing permission: ${permission}`)
    this.name = "PermissionDeniedError"
  }
}

/**
 * Route guard for beforeLoad. Reads the current user from the shared cache
 * (fetching it on a hard refresh) and throws PermissionDeniedError, which
 * the route's errorComponent renders as AccessDenied.
 */
export const requirePermission =
  (permission: Permission) =>
  async ({ context }: { context: RouterContext }) => {
    const user = await context.queryClient.ensureQueryData(
      currentUserQueryOptions,
    )
    if (!can(user, permission)) {
      throw new PermissionDeniedError(permission)
    }
  }
