import type { Role } from "@/client"
import { Badge } from "@/components/ui/badge"
import { ROLE_LABELS } from "@/lib/roles"

const ROLE_VARIANTS: Record<Role, "default" | "secondary" | "outline"> = {
  admin: "default",
  manager: "outline",
  member: "secondary",
}

const RoleBadge = ({ role }: { role: Role }) => (
  <Badge variant={ROLE_VARIANTS[role]}>{ROLE_LABELS[role]}</Badge>
)

export default RoleBadge
