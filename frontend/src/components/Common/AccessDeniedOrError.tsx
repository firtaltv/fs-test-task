import type { ErrorComponentProps } from "@tanstack/react-router"

import { PermissionDeniedError } from "@/lib/routeGuards"
import AccessDenied from "./AccessDenied"
import ErrorComponent from "./ErrorComponent"

/**
 * errorComponent for permission-guarded routes: the AccessDenied page for a
 * failed requirePermission guard, the generic error page for anything else.
 */
const AccessDeniedOrError = ({ error }: ErrorComponentProps) =>
  error instanceof PermissionDeniedError ? <AccessDenied /> : <ErrorComponent />

export default AccessDeniedOrError
