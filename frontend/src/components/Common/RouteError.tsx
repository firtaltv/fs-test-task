import type { ErrorComponentProps } from "@tanstack/react-router"

import { PermissionDeniedError } from "@/lib/routeGuards"
import AccessDenied from "./AccessDenied"
import ErrorComponent from "./ErrorComponent"

/** errorComponent for permission-guarded routes. */
const RouteError = ({ error }: ErrorComponentProps) =>
  error instanceof PermissionDeniedError ? <AccessDenied /> : <ErrorComponent />

export default RouteError
