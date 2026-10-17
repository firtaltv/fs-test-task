import type { ComponentProps } from "react"

import type { Role } from "@/client"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { ROLE_LABELS, ROLES } from "@/lib/roles"

// Trigger props (id, aria-*) arrive from FormControl
type RoleSelectProps = Omit<
  ComponentProps<typeof SelectTrigger>,
  "onChange"
> & {
  value: Role
  onChange: (role: Role) => void
}

const RoleSelect = ({ value, onChange, ...triggerProps }: RoleSelectProps) => (
  <Select value={value} onValueChange={(role) => onChange(role as Role)}>
    <SelectTrigger className="w-full" {...triggerProps}>
      <SelectValue />
    </SelectTrigger>
    <SelectContent>
      {ROLES.map((role) => (
        <SelectItem key={role} value={role}>
          {ROLE_LABELS[role]}
        </SelectItem>
      ))}
    </SelectContent>
  </Select>
)

export default RoleSelect
