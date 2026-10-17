import type { Role } from "@/client"

// Display labels for each role. Typed as Record<Role, ...> so a role added
// on the backend fails to compile here until it gets a label. Roles are for
// display only; gate UI on permissions (usePermission), never on roles.
export const ROLE_LABELS: Record<Role, string> = {
  admin: "Admin",
  manager: "Manager",
  member: "Member",
}

export const ROLES = Object.keys(ROLE_LABELS) as Role[]
