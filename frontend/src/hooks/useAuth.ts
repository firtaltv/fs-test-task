import {
  queryOptions,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query"
import { useNavigate } from "@tanstack/react-router"
import { AxiosError } from "axios"

import {
  type Body_login_login_access_token as AccessToken,
  LoginService,
  type UserMe,
  type UserRegister,
  UsersService,
} from "@/client"
import { handleError } from "@/utils"
import useCustomToast from "./useCustomToast"

const isLoggedIn = () => {
  return localStorage.getItem("access_token") !== null
}

// Shared by useAuth and the route guards so both read the same cache entry
export const currentUserQueryOptions = queryOptions<UserMe>({
  queryKey: ["currentUser"],
  queryFn: async () => (await UsersService.readUserMe()).data,
  // A 4xx (401 signed out, 403 deactivated) won't change on retry; failing
  // fast lets the global handler sign the user out straight away
  retry: (failureCount, error) =>
    !(error instanceof AxiosError && (error.response?.status ?? 500) < 500) &&
    failureCount < 3,
})

const useAuth = () => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { showErrorToast } = useCustomToast()

  const { data: user } = useQuery({
    ...currentUserQueryOptions,
    enabled: isLoggedIn(),
  })

  const signUpMutation = useMutation({
    mutationFn: (data: UserRegister) =>
      UsersService.registerUser({ body: data }),
    onSuccess: () => {
      navigate({ to: "/login" })
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] })
    },
  })

  const login = async (data: AccessToken) => {
    const response = await LoginService.loginAccessToken({
      body: data,
    })
    localStorage.setItem("access_token", response.data.access_token)
    // Never show the previous session's permissions to the new user
    queryClient.removeQueries({ queryKey: currentUserQueryOptions.queryKey })
  }

  const loginMutation = useMutation({
    mutationFn: login,
    onSuccess: () => {
      navigate({ to: "/" })
    },
    onError: handleError.bind(showErrorToast),
  })

  const logout = () => {
    localStorage.removeItem("access_token")
    queryClient.clear()
    navigate({ to: "/login" })
  }

  return {
    signUpMutation,
    loginMutation,
    logout,
    user,
  }
}

export { isLoggedIn }
export default useAuth
