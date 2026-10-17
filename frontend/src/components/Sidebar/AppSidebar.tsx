import { Briefcase, ChartColumn, Home, Users } from "lucide-react"

import type { Permission } from "@/client"

import { SidebarAppearance } from "@/components/Common/Appearance"
import { Logo } from "@/components/Common/Logo"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
} from "@/components/ui/sidebar"
import useAuth from "@/hooks/useAuth"
import { can } from "@/lib/permissions"
import { type Item, Main } from "./Main"
import { User } from "./User"

// Items with a permission are only shown to users whose role grants it
const navItems: (Item & { permission?: Permission })[] = [
  { icon: Home, title: "Dashboard", path: "/" },
  { icon: Briefcase, title: "Items", path: "/items" },
  {
    icon: ChartColumn,
    title: "Metrics",
    path: "/metrics",
    permission: "metrics:read",
  },
  { icon: Users, title: "Admin", path: "/admin", permission: "users:read" },
]

export function AppSidebar() {
  const { user: currentUser } = useAuth()

  const items = navItems.filter(
    (item) => !item.permission || can(currentUser, item.permission),
  )

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="px-4 py-6 group-data-[collapsible=icon]:px-0 group-data-[collapsible=icon]:items-center">
        <Logo variant="responsive" />
      </SidebarHeader>
      <SidebarContent>
        <Main items={items} />
      </SidebarContent>
      <SidebarFooter>
        <SidebarAppearance />
        <User user={currentUser} />
      </SidebarFooter>
    </Sidebar>
  )
}

export default AppSidebar
