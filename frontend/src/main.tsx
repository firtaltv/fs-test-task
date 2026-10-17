import {
  hashKey,
  MutationCache,
  QueryCache,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query"
import { createRouter, RouterProvider } from "@tanstack/react-router"
import { AxiosError } from "axios"
import { StrictMode } from "react"
import ReactDOM from "react-dom/client"
import { toast } from "sonner"
import { client } from "./client/client.gen"
import { ThemeProvider } from "./components/theme-provider"
import { Toaster } from "./components/ui/sonner"
import { currentUserQueryOptions } from "./hooks/useAuth"
import "./index.css"
import { routeTree } from "./routeTree.gen"

client.setConfig({
  baseURL: import.meta.env.VITE_API_URL ?? "",
  auth: () => localStorage.getItem("access_token") || "",
})

const signOut = (loginUrl = "/login") => {
  localStorage.removeItem("access_token")
  window.location.href = loginUrl
}

const handleApiError = (error: Error, isCurrentUserQuery = false) => {
  if (!(error instanceof AxiosError)) return
  const status = error.response?.status
  if (status === 401) {
    // Not authenticated (missing, invalid or expired token): sign out
    signOut()
  } else if (status === 403 && isCurrentUserQuery) {
    // /users/me needs no permission, so a 403 there can only mean the
    // account is inactive: sign out instead of toasting on every request
    signOut("/login?reason=deactivated")
  } else if (status === 403) {
    // Authenticated but not allowed: stay signed in. The fixed id keeps
    // parallel failing requests from stacking identical toasts.
    toast.error("You don't have permission to do that", {
      id: "forbidden",
      description: error.response?.data?.detail,
    })
  }
}
const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: (error, query) =>
      handleApiError(
        error,
        query.queryHash === hashKey(currentUserQueryOptions.queryKey),
      ),
  }),
  mutationCache: new MutationCache({
    onError: (error) => handleApiError(error),
  }),
})

const router = createRouter({ routeTree, context: { queryClient } })
declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router
  }
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
        <Toaster richColors closeButton />
      </QueryClientProvider>
    </ThemeProvider>
  </StrictMode>,
)
