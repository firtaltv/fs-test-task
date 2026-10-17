import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { CircleAlert } from "lucide-react"

import { MetricsService } from "@/client"
import AccessDeniedOrError from "@/components/Common/AccessDeniedOrError"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { ROLE_LABELS, ROLES } from "@/lib/roles"
import { requirePermission } from "@/lib/routeGuards"

function getMetricsQueryOptions() {
  return {
    queryFn: async () => (await MetricsService.readMetrics()).data,
    queryKey: ["metrics"],
  }
}

export const Route = createFileRoute("/_layout/metrics")({
  component: Metrics,
  beforeLoad: requirePermission("metrics:read"),
  errorComponent: AccessDeniedOrError,
  head: () => ({
    meta: [
      {
        title: "Metrics - FastAPI Template",
      },
    ],
  }),
})

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <Card data-testid="stat-card">
      <CardHeader>
        <CardDescription>{label}</CardDescription>
        <CardTitle className="text-3xl tabular-nums">{value}</CardTitle>
      </CardHeader>
    </Card>
  )
}

const STAT_COUNT = ROLES.length + 2

function MetricsContent() {
  const { data, isPending, isError, refetch, isRefetching } = useQuery(
    getMetricsQueryOptions(),
  )

  if (isPending) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: STAT_COUNT }, (_, i) => (
          <Skeleton key={i} className="h-28 rounded-xl" />
        ))}
      </div>
    )
  }

  if (isError) {
    return (
      <Alert variant="destructive">
        <CircleAlert />
        <AlertTitle>Couldn't load metrics</AlertTitle>
        <AlertDescription>
          <p>Something went wrong while fetching the numbers.</p>
          <Button
            variant="outline"
            size="sm"
            className="mt-2"
            onClick={() => refetch()}
            disabled={isRefetching}
          >
            Try again
          </Button>
        </AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <StatCard label="Total users" value={data.users_total} />
      {ROLES.map((role) => (
        <StatCard
          key={role}
          label={`${ROLE_LABELS[role]}s`}
          value={data.users_by_role[role] ?? 0}
        />
      ))}
      <StatCard label="Items" value={data.items_total} />
    </div>
  )
}

function Metrics() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Metrics</h1>
        <p className="text-muted-foreground">
          Users by role and item totals across the system
        </p>
      </div>
      <MetricsContent />
    </div>
  )
}
