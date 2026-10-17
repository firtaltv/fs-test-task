import { Link } from "@tanstack/react-router"
import { ShieldX } from "lucide-react"

import { Button } from "@/components/ui/button"

const AccessDenied = () => {
  return (
    <div
      className="flex flex-col items-center justify-center text-center py-12"
      data-testid="access-denied"
    >
      <div className="rounded-full bg-muted p-4 mb-4">
        <ShieldX className="h-8 w-8 text-muted-foreground" />
      </div>
      <h1 className="text-2xl font-bold tracking-tight">Access denied</h1>
      <p className="text-muted-foreground mt-2">
        You don't have permission to view this page. Ask an administrator if you
        think you should.
      </p>
      <Link to="/">
        <Button className="mt-6">Back to dashboard</Button>
      </Link>
    </div>
  )
}

export default AccessDenied
